import json
import logging
from openai import OpenAI, RateLimitError, OpenAIError
from django.conf import settings
from .site_map import SITE_MAP, get_courses_map

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFY_PROMPT = """
You are Boffins Academy Assistant — intent classifier only.

Rules (STRICT):
- Output ONLY valid JSON. No prose, no markdown, no code fences.
- "primary" must be exactly one of: home, courses, instructors, placements, gallery, about, contact — or null.
- "secondary" must be an array of strings (can be empty []).
- "section" must be a CSS selector string or null.

Output format (exactly, nothing else):
{"primary": <string|null>, "secondary": [<string>, ...], "section": <string|null>}
"""

ASSIST_PROMPT = """
You are Boffins Assistant — the friendly AI for Boffins Academy, a professional
offline tech training institute in Nagpur, India.

Rules (STRICT):
- Answer ONLY about Boffins Academy. Never discuss competitors or other institutes.
- Use the admin data provided to answer confidently and accurately.
- NEVER say "I don't have information" or "I'm not sure" about courses — the admin
  data contains all course info, use it.
- If a specific detail like exact fee is missing, say:
  "Contact our counselling team via the Contact page for details."
- NEVER use markdown: no **bold**, no *italic*, no [links](url), no bullet points,
  no hyphens as bullets. Plain sentences only.
- Keep answers to 1-3 short sentences maximum.
- Be warm, positive, and encouraging.
- For enrollment: say "Visit the Courses page or Contact page."
- For pricing: say "Contact our counselling team via the Contact page."
"""


def _trim_text(value: str | None, limit: int) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _build_admin_context(base_context: dict) -> dict:
    active_course = (base_context or {}).get("active_course") or {}
    active_slug = (active_course.get("slug") or "").strip().lower()
    active_title = (
        active_course.get("title") or active_course.get("name") or ""
    ).strip().lower()

    data = {
        "courses": [],
        "placements": [],
        "companies": [],
        "gallery": {"count": 0, "examples": []},
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

        # CourseProject is optional — import safely so a missing model
        # never silently kills the entire context build.
        try:
            from pages.models import CourseProject
            has_course_project = True
        except ImportError:
            has_course_project = False
            logger.debug("CourseProject model not found — skipping projects data.")

        courses = Courses.objects.filter(is_active=True).order_by("order", "title")
        for course in courses:
            is_active = False
            if active_slug and course.slug and course.slug.lower() == active_slug:
                is_active = True
            if active_title and course.title and course.title.lower() == active_title:
                is_active = True

            # ── Related model: CourseSalary (OneToOne → salary.min_lpa / salary.max_lpa)
            salary_str = ""
            try:
                s = course.salary
                salary_str = f"₹{s.min_lpa}-{s.max_lpa} LPA"
            except Exception:
                pass  # No salary linked — leave blank

            # ── Related model: CourseBatch (OneToOne → batch.start_date / batch.note)
            batch_str = ""
            try:
                b = course.batch
                batch_str = str(b.start_date or "")
                if b.note:
                    batch_str += f" ({b.note})"
            except Exception:
                pass  # No batch linked — leave blank

            # ── Related model: CourseCertificate (OneToOne — may not exist)
            certificate_str = ""
            try:
                c = course.certificate
                certificate_str = _trim_text(str(c), 140)
            except Exception:
                pass  # No certificate linked — leave blank

            item = {
                "title": course.title,
                "slug": course.slug,
                "tagline": _trim_text(course.tagline, 140),
                "description": _trim_text(
                    course.description, 240 if not is_active else 500
                ),
                "salary": salary_str,
                "next_batch": batch_str,
                "certificate": certificate_str,
            }

            if is_active:
                curriculum = CourseCurriculum.objects.filter(
                    course=course
                ).order_by("order")
                technologies = CourseTechnology.objects.filter(
                    course=course
                ).order_by("name")
                career_roles = CourseCareerRole.objects.filter(
                    course=course
                ).order_by("title")

                item["curriculum"] = [
                    {"title": c.title, "duration": c.duration} for c in curriculum
                ]
                item["technologies"] = [t.name for t in technologies]
                item["career_roles"] = [r.title for r in career_roles]

                if has_course_project:
                    projects = CourseProject.objects.filter(
                        course=course
                    ).order_by("title")
                    item["projects"] = [p.title for p in projects]

            data["courses"].append(item)

        placements = Placement.objects.filter(is_active=True).order_by(
            "order", "name"
        )
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
                p
                for p in placement_items
                if active_title in (p.get("course") or "").lower()
            ]
            data["placements"] = (
                active_placements[:10] if active_placements else placement_items[:8]
            )
        else:
            data["placements"] = placement_items[:8]

        companies = Company.objects.filter(is_active=True).order_by("order", "name")
        data["companies"] = [c.name for c in companies[:12]]

        gallery = GalleryImage.objects.filter(is_active=True).order_by("order", "id")
        data["gallery"]["count"] = gallery.count()
        data["gallery"]["examples"] = [
            _trim_text(img.alt_text, 80) for img in gallery[:8] if img.alt_text
        ]

    except Exception as e:
        # Log the real error — never swallow silently again
        logger.error("_build_admin_context failed: %s", e, exc_info=True)
        return data

    return data


def llm_classify_intent(message: str):
    pages = list(SITE_MAP.keys())
    sections_map = {
        page: meta.get("sections", {}).copy()
        for page, meta in SITE_MAP.items()
        if meta.get("sections") is not None
    }

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
                    "content": (
                        f'User message: "{message}"\n\n'
                        f"Available pages: {pages}\n\n"
                        f"Section anchors by page: {sections_map}\n\n"
                        "Respond ONLY in JSON — no markdown, no code fences:\n"
                        '{"primary": <page or null>, "secondary": [], "section": <selector or null>}'
                    ),
                },
            ],
        )
    except RateLimitError:
        return {"primary": None, "secondary": []}
    except OpenAIError:
        return {"primary": None, "secondary": []}

    content = response.choices[0].message.content.strip()

    # Strip accidental markdown code fences GPT sometimes adds
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        logger.warning("llm_classify_intent: failed to parse JSON: %s", content)
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
            max_tokens=150,
            messages=[
                {"role": "system", "content": ASSIST_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Context: {context}\n\n"
                        f"Admin data (authoritative — use this to answer): {admin_data}\n\n"
                        f"Available pages: {pages}\n\n"
                        f"Known sections: {sections_map}\n\n"
                        f"Known course titles: {course_titles}\n\n"
                        f"User: {message}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return "The assistant is temporarily unavailable due to high demand. Please try again shortly."
    except OpenAIError:
        return "The assistant is temporarily unavailable. Please try again later."