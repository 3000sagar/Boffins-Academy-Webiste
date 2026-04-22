import json
from openai import OpenAI, RateLimitError, OpenAIError
from django.conf import settings
from .site_map import SITE_MAP, get_courses_map

client = OpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFY_PROMPT = """
You are Boffins Academy Assistant.

Rules (STRICT):
- You ONLY talk about Boffins Academy.
- You NEVER invent pages.
- You ONLY choose from these pages:
  home, courses, instructors, placements, gallery, about, contact
- If unsure, return null intent.
- Be concise.

Output JSON only.
"""

ASSIST_PROMPT = """
You are Boffins Academy Assistant.

Rules (STRICT):
- You ONLY talk about Boffins Academy.
- You NEVER invent pages, sections, courses, prices, dates, or policies.
- Use the provided admin data when answering.
- If the user asks for information that is not in the provided context, say you don't have it and guide them to the most relevant page or the contact page.
- Write 1 to 2 short lines (not bullet points), like ChatGPT: understand first, then give the most helpful, optimal response.
- Be concise, helpful, and friendly.

When appropriate, you should:
- Use the current page and active course context.
- Suggest the relevant page if the user’s request maps to a different page.
- If pricing or admissions specifics are requested and not present in context, suggest contacting counselling via the contact page.
"""


def _trim_text(value: str | None, limit: int) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _build_admin_context(base_context: dict) -> dict:
    """
    Pulls admin-managed data from the database and returns a compact, LLM-safe
    context payload. This lets the assistant answer based on what you add in admin.
    """
    active_course = (base_context or {}).get("active_course") or {}
    active_slug = (active_course.get("slug") or "").strip().lower()
    active_title = (active_course.get("title") or active_course.get("name") or "").strip().lower()

    data = {
        "courses": [],
        "placements": [],
        "companies": [],
        "gallery": {
            "count": 0,
            "examples": [],
        },
    }

    try:
        from pages.models import (
            Courses,
            CourseCurriculum,
            CourseTechnology,
            CourseCareerRole,
            Placement,
            Company,
            GalleryImage,
        )

        courses = Courses.objects.filter(is_active=True).order_by("order", "title")
        for course in courses:
            is_active = False
            if active_slug and course.slug and course.slug.lower() == active_slug:
                is_active = True
            if active_title and course.title and course.title.lower() == active_title:
                is_active = True

            item = {
                "title": course.title,
                "slug": course.slug,
                "tagline": _trim_text(course.tagline, 140),
                "description": _trim_text(course.description, 240 if not is_active else 500),
                "salary_range_lpa": f"{course.salary_min}-{course.salary_max}",
                "next_batch": str(course.next_batch),
                "certificate": _trim_text(course.certificate, 140),
            }

            if is_active:
                curriculum = CourseCurriculum.objects.filter(course=course).order_by("order")
                technologies = CourseTechnology.objects.filter(course=course).order_by("name")
                projects = CourseProject.objects.filter(course=course).order_by("title")
                career_roles = CourseCareerRole.objects.filter(course=course).order_by("title")

                item["curriculum"] = [
                    {
                        "title": c.title,
                        "duration": c.duration,
                    }
                    for c in curriculum
                ]
                item["technologies"] = [t.name for t in technologies]
                item["projects"] = [p.title for p in projects]
                item["career_roles"] = [r.title for r in career_roles]

            data["courses"].append(item)

        placements = Placement.objects.filter(is_active=True).order_by("order", "name")
        placement_items = []
        for placement in placements:
            placement_items.append(
                {
                    "name": placement.name,
                    "course": placement.course,
                    "company": placement.company,
                    "package_lpa": placement.package_lpa,
                    "tag": placement.tag,
                    "testimonial": _trim_text(placement.testimonial, 200),
                }
            )

        if active_title:
            active_placements = [
                p for p in placement_items if active_title in (p.get("course") or "").lower()
            ]
            data["placements"] = active_placements[:10] if active_placements else placement_items[:8]
        else:
            data["placements"] = placement_items[:8]

        companies = Company.objects.filter(is_active=True).order_by("order", "name")
        data["companies"] = [c.name for c in companies[:12]]

        gallery = GalleryImage.objects.filter(is_active=True).order_by("order", "id")
        data["gallery"]["count"] = gallery.count()
        data["gallery"]["examples"] = [
            _trim_text(img.alt_text, 80) for img in gallery[:8] if img.alt_text
        ]

    except Exception:
        return data

    return data

def llm_classify_intent(message: str):
    """
    Returns:
    {
      "primary": "courses" | null,
      "secondary": ["pricing", "duration"],
      "section": "#data-science" | null
    }
    """

    pages = list(SITE_MAP.keys())
    sections_map = {
        page: meta.get("sections", {}).copy()
        for page, meta in SITE_MAP.items()
        if meta.get("sections") is not None
    }

    # Inject dynamic course sections so we don't hardcode IDs
    course_sections = {}
    for course in get_courses_map().values():
        title = (course.get("title") or "").strip().lower()
        slug = (course.get("slug") or "").strip().lower()
        section = course.get("section")
        if not section:
            continue
        if title:
            course_sections[title] = section
        if slug:
            course_sections[slug.replace("-", " ")] = section

    if course_sections:
        sections_map["courses"] = course_sections

    if not settings.OPENAI_API_KEY:
        return {"primary": None, "secondary": []}

    try:
        response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=120,
        messages=[
            {"role": "system", "content": CLASSIFY_PROMPT},
            {
                "role": "user",
                "content": f"""
User message:
"{message}"

Available pages:
{pages}

Section anchors by page (if any):
{sections_map}

Respond ONLY in JSON:
{{ "primary": <page or null>, "secondary": [], "section": <selector or null> }}
"""
            }
        ],
    )
    except RateLimitError:
        return {"primary": None, "secondary": []}
    except OpenAIError:
        return {"primary": None, "secondary": []}

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        return {"primary": None, "secondary": []}


def llm_assist(message: str, context: dict):
    if not settings.OPENAI_API_KEY:
        return "Chat assistant is offline. Please set a valid OpenAI API key."

    admin_data = _build_admin_context(context or {})

    pages = list(SITE_MAP.keys())
    sections_map = {
        page: meta.get("sections", {}).copy()
        for page, meta in SITE_MAP.items()
        if meta.get("sections") is not None
    }
    course_titles = []
    for course in get_courses_map().values():
        title = (course.get("title") or "").strip()
        if title and title not in course_titles:
            course_titles.append(title)

    try:
        response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=120,
        messages=[
            {"role": "system", "content": ASSIST_PROMPT},
            {
                "role": "user",
                "content": f"""
Context:
{context}

Admin data (authoritative):
{admin_data}

Available pages:
{pages}

Known sections by page (if any):
{sections_map}

Known course titles (if any):
{course_titles}

User:
{message}
"""
            }
        ],
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return "The assistant is temporarily unavailable due to API quota limits. Please try again later."
    except OpenAIError:
        return "The assistant is temporarily unavailable. Please try again later."
