# chat/services/site_map.py

SITE_MAP = {
    "home": {
        "page": "/",
        "keywords": ["home", "homepage", "main", "start"],
    },
    "courses": {
        "page": "/courses/",
        "keywords": ["course", "courses", "program", "programs", "training"],
        "has_price": False,
        "cta": {"label": "Get Course Pricing", "page": "/contact/"},
        "sections": {},
    },
    "instructors": {
        "page": "/instructors/",
        "keywords": [
            "instructor",
            "instructors",
            "trainer",
            "trainers",
            "mentor",
            "mentors",
            "faculty",
            "teachers",
        ],
        "sections": {
            "top": "#instructors-hero",
            "instructors": "#instructors-grid",
            "cta": "#instructors-cta",
        },
    },
    "placements": {
        "page": "/placements/",
        "keywords": [
            "placement",
            "placements",
            "job",
            "jobs",
            "salary",
            "lpa",
            "career",
            "success stories",
            "success story",
            "testimonials",
            "reviews",
            "alumni",
        ],
        "sections": {
            "top": "#placements-hero",
            "placements": "#placements-hero",
            "process": "#placement-process",
            "hiring partners": "#hiring-partners",
            "cta": "#placements-cta",
        },
    },
    "gallery": {
        "page": "/gallery/",
        "keywords": ["gallery", "photos", "images", "campus", "events"],
        "sections": {
            "top": "#gallery-hero",
            "gallery": "#gallery-grid",
            "community": "#gallery-cta",
        },
    },
    "about": {
        "page": "/about/",
        "keywords": ["about", "about us", "company", "academy"],
        "sections": {
            "top": "#about-hero",
            "mission": "#mission-vision",
            "vision": "#mission-vision",
            "drives": "#drives",
            "success story": "#about-cta",
        },
    },
    "contact": {
        "page": "/contact/",
        "keywords": [
            "contact",
            "contact us",
            "fees",
            "fee",
            "price",
            "pricing",
            "cost",
            "counselling",
            "counselor",
        ],
        "sections": {
            "top": "#contact-hero",
            "form": "#contact-form",
            "contact": "#contact-form",
        },
    },
}

COURSES = {
    "data science": {
        "id": "data_science",
        "keywords": [
            "data science",
            "data scientist",
            "ds",
            "machine learning",
            "ml",
            "ai course",
            "python",
        ],
        "section": "#course-data-science",
    },
    "full stack": {
        "id": "full_stack",
        "keywords": [
            "full stack",
            "fullstack",
            "web development",
            "frontend backend",
            "mern",
        ],
        "section": "#course-full-stack-development",
    },
    "cloud devops": {
        "id": "cloud_devops",
        "keywords": ["cloud", "devops", "aws", "azure", "docker", "kubernetes"],
        "section": "#course-cloud-devops",
    },
}


def _split_keywords(value: str) -> list[str]:
    if not value:
        return []
    tokens = []
    for part in value.replace("-", " ").replace("_", " ").split():
        part = part.strip().lower()
        if part and part not in tokens:
            tokens.append(part)
    return tokens


def get_courses_map():
    try:
        from pages.models import Courses

        courses = Courses.objects.filter(is_active=True).order_by("order", "title")
        if not courses.exists():
            return COURSES

        course_map = {}
        for course in courses:
            title = (course.title or "").strip()
            slug = (course.slug or "").strip()
            key = (title or slug or "").lower()
            if not key:
                continue

            keywords = []
            if title:
                keywords.append(title.lower())
                keywords.extend(_split_keywords(title))
            if slug:
                keywords.append(slug.replace("-", " ").lower())
                keywords.extend(_split_keywords(slug))

            seen = set()
            clean_keywords = []
            for keyword in keywords:
                keyword = keyword.strip().lower()
                if keyword and keyword not in seen:
                    seen.add(keyword)
                    clean_keywords.append(keyword)

            course_map[key] = {
                "id": slug or key.replace(" ", "_"),
                "keywords": clean_keywords,
                "section": f"#course-{slug}" if slug else None,
                "title": title,
                "slug": slug,
            }

        return course_map or COURSES
    except Exception:
        return COURSES
