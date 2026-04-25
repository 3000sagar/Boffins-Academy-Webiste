from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("gallery/", views.gallery, name="gallery"),
    path("contact/", views.contact, name="contact"),
    path("about/", views.about, name="about"),
    path("placements/",views.placements, name="placements"),
    path("courses/", views.courses, name="courses"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("instructors/", views.instructors, name="instructors"),
    path("feedback/", views.feedback_submit, name="feedback_submit"),
    path("api/courses/", views.api_courses, name="api_courses"),
]
