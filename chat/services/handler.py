import re
import uuid

from .faq import match_faq
from .intents import parse_intent
from .llm import llm_assist, llm_classify_intent
from .session import get_session
from .site_map import SITE_MAP, get_courses_map


def _fallback_reply(primary: str | None, detected_course: dict | None) -> str:
    if detected_course:
        course_title = detected_course.get("title") or detected_course.get("name") or "this course"
        return f"You can explore details for {course_title} on our Courses page."

    replies = {
        "courses": "You can explore all programs on our Courses page.",
        "placements": "You can view placement outcomes and hiring partners on our Placements page.",
        "instructors": "You can meet our trainers and mentors on the Instructors page.",
        "gallery": "You can check campus life and events on our Gallery page.",
        "about": "You can learn more about Boffins Academy on the About page.",
        "contact": "Please contact our counselling team via the Contact page for exact details.",
        "home": "You can start from the Home page and navigate to any section you need.",
    }
    return replies.get(primary or "", "Please visit the Contact page and our team will guide you.")


def _is_llm_unavailable(reply: str) -> bool:
    text = (reply or "").lower()
    return "temporarily unavailable" in text or "offline" in text


def _finalize_reply(reply: str, primary: str | None, detected_course: dict | None) -> str:
    if not isinstance(reply, str) or not reply.strip():
        return _fallback_reply(primary, detected_course)
    if _is_llm_unavailable(reply):
        return _fallback_reply(primary, detected_course)
    return reply.strip()


def handle_message(session_id: str | None, message: str):
    session_id = session_id or str(uuid.uuid4())
    session = get_session(session_id)

    actions = []
    text = message.lower()

    name_match = re.search(
        r"(?:my name is|i am|i'm)\s+([a-zA-Z][a-zA-Z'\- ]{0,40})",
        message,
        flags=re.IGNORECASE,
    )
    if name_match:
        raw_name = re.split(r"[.!?,\n]", name_match.group(1).strip())[0]
        name_parts = raw_name.split()
        if name_parts:
            session["user_name"] = " ".join(name_parts[:2])

    goal_match = re.search(
        r"(?:i want to|i would like to|i'm looking to|i am looking to|i want|i need)\s+(.+)",
        message,
        flags=re.IGNORECASE,
    )
    if goal_match:
        raw_goal = re.split(r"[.!?\n]", goal_match.group(1).strip())[0]
        if raw_goal:
            session["user_goal"] = raw_goal[:120]

    detected_course = None
    for course_name, course in get_courses_map().items():
        if any(keyword in text for keyword in course["keywords"]):
            detected_course = {"name": course_name, **course}
            session["active_course"] = detected_course
            break

    if not detected_course and session.get("active_course"):
        detected_course = session["active_course"]

    llm_intent = llm_classify_intent(message)
    if llm_intent.get("primary") in SITE_MAP:
        intent = llm_intent
        primary = llm_intent["primary"]
        secondary = llm_intent.get("secondary", [])
    else:
        intent = parse_intent(message)
        primary = intent.get("primary")
        secondary = intent.get("secondary", [])

    if detected_course and not primary:
        primary = "courses"

    if primary and primary != "courses":
        session["active_course"] = None
        detected_course = None

    if not primary:
        faq_answer = match_faq(message)
        if faq_answer:
            return {
                "session_id": session_id,
                "actions": [{"type": "message", "content": faq_answer}],
            }

        reply = llm_assist(
            message,
            context={
                "current_page": session.get("current_page"),
                "active_course": session.get("active_course"),
                "user_name": session.get("user_name"),
                "user_goal": session.get("user_goal"),
            },
        )
        reply = _finalize_reply(reply, primary=None, detected_course=detected_course)

        return {
            "session_id": session_id,
            "actions": [{"type": "message", "content": reply}],
        }

    page_info = SITE_MAP.get(primary, {})
    target_page = page_info.get("page")

    section_selector = None
    if isinstance(intent, dict):
        section = intent.get("section")
        sections = page_info.get("sections", {})
        if section in sections:
            section_selector = sections[section]
        elif section in sections.values():
            section_selector = section

    if primary == "courses" and detected_course and not section_selector:
        section_selector = detected_course.get("section")

    current_page = session.get("current_page")
    navigating_to_new_page = bool(target_page and current_page != target_page)

    if navigating_to_new_page:
        navigate_url = target_page
        if section_selector and section_selector.startswith("#"):
            navigate_url = f"{target_page}{section_selector}"
        actions.append({"type": "navigate", "page": navigate_url})
        session["current_page"] = target_page
        session.setdefault("visited_pages", []).append(target_page)
    elif section_selector:
        actions.append({"type": "scroll", "selector": section_selector})

    reply = llm_assist(
        message,
        context={
            "current_page": session.get("current_page"),
            "active_course": session.get("active_course"),
            "intent": primary,
            "secondary": secondary,
            "user_name": session.get("user_name"),
            "user_goal": session.get("user_goal"),
        },
    )

    actions.append(
        {"type": "message", "content": _finalize_reply(reply, primary, detected_course)}
    )

    for sec in secondary:
        if sec == "pricing" and not page_info.get("has_price", True):
            cta = page_info.get("cta")
            if cta:
                actions.append(
                    {
                        "type": "suggest",
                        "content": "Course pricing depends on counselling and your background.",
                        "button": {"label": cta["label"], "page": cta["page"]},
                    }
                )
        elif sec == "duration":
            actions.append(
                {
                    "type": "message",
                    "content": "Course duration varies by program. You will find the details on this page.",
                }
            )
        elif sec == "syllabus" and detected_course:
            actions.append({"type": "scroll", "selector": detected_course["section"]})
            actions.append(
                {
                    "type": "message",
                    "content": "Here is the syllabus section for this course.",
                }
            )
        elif sec == "placements":
            actions.append(
                {
                    "type": "message",
                    "content": "Our programs include strong placement support with real industry exposure.",
                }
            )
        elif sec == "certificate":
            actions.append(
                {
                    "type": "message",
                    "content": "You will receive a recognized certificate after successful completion.",
                }
            )
        elif sec == "batch":
            actions.append(
                {
                    "type": "message",
                    "content": "Batch start dates depend on the program. Next batch details are available on the page.",
                }
            )

    session["last_intent"] = intent

    return {"session_id": session_id, "actions": actions}
