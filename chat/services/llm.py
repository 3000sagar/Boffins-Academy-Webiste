import json
import logging

from django.conf import settings
from openai import OpenAI, OpenAIError, RateLimitError

from .site_map import SITE_MAP, get_courses_map

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFY_PROMPT = """
You are the intent router for the Boffins Academy website chatbot.

Your task is only to classify the user's message into:
- the best page intent
- any useful secondary intents
- an optional section selector when the user clearly refers to a known course or section

Rules:
- Return only valid JSON.
- No markdown, no prose, no explanations, no code fences.
- "primary" must be exactly one of: home, courses, instructors, placements, gallery, about, contact, or null.
- "secondary" must be an array. Use only relevant short labels already implied by the user request.
- "section" must be a CSS selector string like "#course-data-science" or null.
- Prefer null rather than guessing.
- If the user asks about fees, pricing, cost, counselling, admission, contact details, or enrollment help, prefer "contact".
- If the user asks about jobs, salary, hiring partners, alumni results, success stories, or placements, prefer "placements".
- If the user asks about a specific course, syllabus, curriculum, technologies, duration, or what they will learn, prefer "courses".
- Use a section only when it is clearly supported by the provided section map.

Return exactly:
{"primary": <string|null>, "secondary": <string[]>, "section": <string|null>}
"""

ASSIST_PROMPT = """
You are Boffins Assistant, the website chatbot for Boffins Academy in Nagpur.

Your job is to sound like a helpful academy counselor inside a website chat panel.

Core behavior:
- Talk only about Boffins Academy.
- Use the provided admin data as the source of truth.
- Be accurate, practical, warm, and direct.
- Write plain text only. No markdown, bullets, numbering, emojis, or quotes.
- Keep replies concise: usually 1 to 3 short sentences.
- Answer the user's real question first, then guide them if needed.

Truthfulness:
- Never invent courses, fees, dates, trainers, placement figures, policies, pages, or promises.
- If a detail is missing or not explicit in the context, do not guess.
- For fees, exact pricing, admission process details, or anything not provided, say:
  Please contact our counselling team via the Contact page for exact details.

Response style:
- Avoid generic filler like "I am here to help" unless absolutely necessary.
- Avoid robotic phrases like "based on the provided context".
- If the user asks about a known course, mention that course naturally.
- If the user message is vague like "hi", "hello", or "help", reply with a short welcoming line and mention 2 or 3 useful things you can help with, such as courses, placements, or contact details.
- If the user asks for something unrelated to Boffins Academy, politely bring them back to academy-related help.
- If the user asks about a course, tool, skill, or technology that is not a standalone course but is covered inside a broader program, do not lead with a flat no. Lead with the closest positive match first.
- Example style: "Yes, Python is covered in our Data Science and AI program." If needed, follow with one short clarifying sentence that it is part of a broader course rather than a separate standalone program.
- Avoid starting replies with negative phrasing like "We do not offer..." when there is a relevant positive alternative available inside the academy.
- If the user asks about a course that is not clearly available at all, say so briefly and then suggest the closest relevant path using known academy data.

Navigation awareness:
- Use the current page and active course context when it helps.
- If the best next step is another page, mention it naturally in one short sentence.
- Do not mention internal field names, raw JSON, or system context.
"""


def _trim_text(value: str | None, limit: int) -> str:
    if not value:
        return ""
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "..."


def _safe_json_load(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        logger.warning("Failed to parse classifier JSON: %s", text)
    return {"primary": None, "secondary": [], "section": None}


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
            Company,
            CourseCareerRole,
            CourseCurriculum,
            CourseTechnology,
            Courses,
            GalleryImage,
            Placement,
        )

        courses = Courses.objects.filter(is_active=True).order_by("order", "title")
        for course in courses:
            is_active_course = False
            if active_slug and course.slug and course.slug.lower() == active_slug:
                is_active_course = True
            if active_title and course.title and course.title.lower() == active_title:
                is_active_course = True

            salary_str = ""
            try:
                salary = course.salary
                salary_str = f"{salary.min_lpa}-{salary.max_lpa} LPA"
            except Exception:
                salary_str = ""

            batch_str = ""
            try:
                batch = course.batch
                batch_str = str(batch.start_date or "")
                if batch.note:
                    batch_str = f"{batch_str} ({batch.note})"
            except Exception:
                batch_str = ""

            certificate_str = ""
            try:
                certificate = course.certificate
                certificate_str = _trim_text(str(certificate), 140)
            except Exception:
                certificate_str = ""

            technologies = CourseTechnology.objects.filter(course=course).order_by(
                "order", "name"
            )

            item = {
                "title": course.title,
                "slug": course.slug,
                "tagline": _trim_text(course.tagline, 140),
                "description": _trim_text(
                    course.description, 500 if is_active_course else 240
                ),
                "salary": salary_str,
                "next_batch": batch_str,
                "certificate": certificate_str,
                "technologies": [t.name for t in technologies[:8]],
            }

            if is_active_course:
                curriculum = CourseCurriculum.objects.filter(course=course).order_by(
                    "order"
                )
                career_roles = CourseCareerRole.objects.filter(course=course).order_by(
                    "order", "title"
                )

                item["curriculum"] = [
                    {"title": c.title, "duration": c.duration} for c in curriculum
                ]
                item["technologies"] = [t.name for t in technologies]
                item["career_roles"] = [r.title for r in career_roles]

            data["courses"].append(item)

        placements = Placement.objects.filter(is_active=True).order_by("order", "name")
        placement_items = [
            {
                "name": p.name,
                "course": p.course,
                "company": p.company,
                "package_lpa": p.package_lpa,
                "tag": p.tag,
                "testimonial": _trim_text(p.testimonial, 200),
            }
            for p in placements
        ]

        if active_title:
            active_placements = [
                p for p in placement_items if active_title in (p.get("course") or "").lower()
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
            _trim_text(g.alt_text, 80) for g in gallery[:8] if g.alt_text
        ]
    except Exception as exc:
        logger.error("_build_admin_context failed: %s", exc, exc_info=True)
        return data

    return data


def llm_classify_intent(message: str) -> dict:
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
        return {"primary": None, "secondary": [], "section": None}

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
                        f'User message:\n"{message}"\n\n'
                        f"Available pages:\n{pages}\n\n"
                        f"Section anchors by page:\n{sections_map}"
                    ),
                },
            ],
        )
    except RateLimitError:
        return {"primary": None, "secondary": [], "section": None}
    except OpenAIError:
        return {"primary": None, "secondary": [], "section": None}

    content = response.choices[0].message.content or ""
    parsed = _safe_json_load(content)

    primary = parsed.get("primary")
    if primary not in SITE_MAP:
        primary = None

    secondary = parsed.get("secondary")
    if not isinstance(secondary, list):
        secondary = []

    section = parsed.get("section")
    if section is not None and not isinstance(section, str):
        section = None

    return {"primary": primary, "secondary": secondary, "section": section}


def llm_assist(message: str, context: dict) -> str:
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
            temperature=0.3,
            max_tokens=150,
            messages=[
                {"role": "system", "content": ASSIST_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Context:\n{context}\n\n"
                        f"Admin data:\n{admin_data}\n\n"
                        f"Available pages:\n{pages}\n\n"
                        f"Known sections by page:\n{sections_map}\n\n"
                        f"Known course titles:\n{course_titles}\n\n"
                        f"User:\n{message}"
                    ),
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except RateLimitError:
        return "The assistant is temporarily unavailable due to high demand. Please try again shortly."
    except OpenAIError:
        return "The assistant is temporarily unavailable. Please try again later."
