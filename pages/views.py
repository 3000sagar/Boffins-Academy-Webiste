from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .forms import ContactForm
from .models import Courses, GalleryImage, Placement, Company


# ---------- STATIC PAGES ----------

def home(request):
    placements = Placement.objects.filter(is_active=True)[:6]

    testimonials = []
    for p in placements:
        name = p.name or ""
        parts = [part for part in name.split() if part]
        initials = "".join(part[0].upper() for part in parts[:2]) or "BA"

        testimonials.append({
            "image": p.avatar.url if p.avatar else None,
            "initials": initials,
            "quote": p.testimonial or "Great learning experience at Boffins Academy.",
            "name": p.name,
            "role": p.company,
            "course": p.course,
            "salary": p.package_lpa,
        })

    return render(
        request,
        "pages/home.html",
        {
            "hero": {
                "trust_text": "Trusted by 15,000+ Students • 10 Years of Excellence",
                "headline_top": "Transform Your Career With",
                "headline_highlight": "Industry-Ready Tech Skills",
                "subtext": (
                    "Master Data Science, Full Stack Development, Cloud & DevOps, "
                    "or Digital Marketing through hands-on training, build a professional "
                    "portfolio, and land your dream job."
                ),
                "primary_cta": "Explore Courses",
                "secondary_cta": "Get Free Counselling",
            },
            "testimonials": testimonials,
        },
    )

def gallery(request):
    images = list(GalleryImage.objects.filter(is_active=True).order_by("order", "id"))
    return render(request, "pages/gallery.html", {
        "images": images,
        "last_img": images[-1] if images else None,
    })



def about(request):
    return render(request, "pages/about.html")



def courses(request):
    courses = (
        Courses.objects
        .filter(is_active=True)
        .select_related(
            "salary",
            "batch",
            "certificate",
            "cta",
        )
        .prefetch_related(
            "curriculum",
            "technologies",
            "career_roles",
        )
        .order_by("order")
    )

    return render(
        request,
        "pages/courses.html",
        {
            "courses": courses,
        }
    )


def course_detail(request, slug):
    course = get_object_or_404(
        Courses.objects.filter(is_active=True)
        .select_related("salary", "batch", "certificate", "cta")
        .prefetch_related("curriculum", "technologies","career_roles"),
        slug=slug,
    )

    tech_icons = {
        "power bi": {
            "icon": "PB",
            "description": "Learn how to transform raw data into interactive dashboards and reports using Power BI.",
            "points": [
                "Clean and prepare data for reporting",
                "Build interactive dashboards and charts",
                "Understand trends and patterns",
                "Share reports with others",
            ],
        },
        "python": {
            "icon": "Py",
            "description": "Start with Python basics and move into data analysis and machine learning to solve real problems.",
            "points": [
                "Write Python programs with confidence",
                "Analyze data using popular libraries",
                "Visualize data with charts and graphs",
                "Explore datasets and discover insights",
            ],
        },
        "excel": {
            "icon": "XL",
            "description": "Discover how Excel can power analysis, reporting, and automation for business-ready data workflows.",
            "points": [
                "Use powerful formulas and functions",
                "Analyze data with Pivot Tables",
                "Create interactive dashboards",
                "Work faster with automation tips",
            ],
        },
        "sql": {
            "icon": "SQL",
            "description": "Understand how data is stored and learn to extract the exact information you need using SQL.",
            "points": [
                "Fetch and filter data from databases",
                "Combine tables using joins",
                "Analyze data using SQL queries",
                "Prepare data for reporting and analysis",
            ],
        },
    }

    tool_overview = []
    for tech in course.technologies.all()[:4]:
        key = tech.name.strip().lower()
        detail = tech_icons.get(key)
        if detail is None:
            detail = {
                "icon": tech.name[:2].upper(),
                "description": f"Master {tech.name} as part of an industry-ready {course.title} curriculum.",
                "points": [
                    f"Gain practical experience with {tech.name}",
                    "Work on real-world industry scenarios",
                    "Build skills that companies value",
                ],
            }
        tool_overview.append({
            "title": tech.name,
            "icon": detail["icon"],
            "description": detail["description"],
            "points": detail["points"],
        })

    if not tool_overview:
        tool_overview = [
            {
                "title": course.title,
                "icon": course.title[:2].upper(),
                "description": course.description,
                "points": [
                    "Build practical skills through hands-on projects",
                    "Learn the core concepts that hiring managers look for",
                    "Get industry-ready with real-world use cases",
                ],
            }
        ]

    return render(
        request,
        "pages/course_detail.html",
        {
            "course": course,
            "tool_overview": tool_overview,
        },
    )


def instructors(request):
    return render(request, "pages/instructors.html")

def placements(request):
    placements = Placement.objects.filter(is_active=True)
    companies = Company.objects.filter(is_active=True)

    return render(
        request,
        "pages/placements.html",
        {
            "placements": placements,
            "companies": companies,
        }
    )


# ---------- CONTACT PAGE ----------

@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Message sent successfully. We’ll contact you soon."
            )

            # IMPORTANT: redirect WITHOUT query params
            return redirect("contact")
    else:
        form = ContactForm()

    context = {
        "form": form,

        # LEFT INFO CARDS
        "phone_lines": [
            "+91 1122334455",
            "+91 1122334455",
        ],
        "email_lines": [
            "info@boffinsacademy.com",
            "admissions@boffinsacademy.com",
        ],
        "location_lines": [
            "IT Park, Nagpur, Maharashtra",
            "Postal Code – 440022",
        ],
        "hours_lines": [
            "Mon–Fri: 9:00 AM – 7:00 PM",
            "Sat: 10:00 AM – 5:00 PM",
        ],
    }

    return render(request, "pages/contact.html", context)
