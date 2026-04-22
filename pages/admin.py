from django.contrib import admin

from .models import (
    ContactMessage,
    Course,
    Courses,
    GalleryImage,
    Placement,
    Company,

    # Course sub-models
    CourseSalary,
    CourseBatch,
    CourseCertificate,
    CourseCTA,
    CourseCurriculum,
    CourseTechnology,
    CourseCareerRole,
)


# =========================
# Contact Messages
# =========================
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "created_at")


# =========================
# Legacy / Simple Course (if still used)
# =========================
admin.site.register(Course)


# =========================
# Course Inlines
# =========================
class CourseSalaryInline(admin.StackedInline):
    model = CourseSalary
    extra = 0
    max_num = 1


class CourseBatchInline(admin.StackedInline):
    model = CourseBatch
    extra = 0
    max_num = 1


class CourseCertificateInline(admin.StackedInline):
    model = CourseCertificate
    extra = 0
    max_num = 1


class CourseCTAInline(admin.StackedInline):
    model = CourseCTA
    extra = 0
    max_num = 1


class CourseCurriculumInline(admin.TabularInline):
    model = CourseCurriculum
    extra = 1
    ordering = ("order",)


class CourseTechnologyInline(admin.TabularInline):
    model = CourseTechnology
    extra = 1
    ordering = ("order",)





class CourseCareerRoleInline(admin.TabularInline):
    model = CourseCareerRole
    extra = 1
    ordering = ("order",)


# =========================
# Courses (MAIN ADMIN)
# =========================
@admin.register(Courses)
class CoursesAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")
    ordering = ("order",)
    prepopulated_fields = {"slug": ("title",)}

    inlines = [
        CourseSalaryInline,
        CourseBatchInline,
        CourseCertificateInline,
        CourseCTAInline,
        CourseCurriculumInline,
        CourseTechnologyInline,
        
        CourseCareerRoleInline,
    ]


# =========================
# Gallery Images
# =========================
@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("id", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    ordering = ("order",)


# =========================
# Placements
# =========================
@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "course", "package_lpa", "is_active", "order")
    list_editable = ("is_active", "order")


# =========================
# Companies
# =========================
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name",)