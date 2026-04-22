from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class Course(models.Model):
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    course_interest = models.ForeignKey(
    Course,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.email}"

class Courses(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    tagline = models.CharField(max_length=150)
    description = models.TextField()

    icon_svg = models.TextField(
        help_text="Paste full SVG markup here"
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def active_offers(self):
        return self.offers.filter(is_active=True, deadline__gte=timezone.now()).order_by("order")

    @property
    def current_offer(self):
        return self.active_offers.first()


# =========================
# Salary Card
# =========================
class CourseSalary(models.Model):
    course = models.OneToOneField(
        Courses,
        on_delete=models.CASCADE,
        related_name="salary"
    )
    min_lpa = models.PositiveIntegerField()
    max_lpa = models.PositiveIntegerField()
    description = models.CharField(
        max_length=150,
        default="Average salary for freshers to 2 years exp."
    )

    def __str__(self):
        return f"₹ {self.min_lpa}-{self.max_lpa} LPA"

    @property
    def discount_label(self):
        if self.discount_percentage:
            return f"{self.discount_percentage}% off"
        if self.discount_amount:
            return f"₹{self.discount_amount} off"
        return "Special offer"

    @property
    def formatted_deadline(self):
        return self.deadline.strftime("%b %d, %Y")

    @property
    def is_expired(self):
        return timezone.now() > self.deadline

# =========================
# Batch Card
# =========================
class CourseBatch(models.Model):
    course = models.OneToOneField(
        Courses,
        on_delete=models.CASCADE,
        related_name="batch"
    )
    start_date = models.DateField()
    note = models.CharField(
        max_length=100,
        help_text="Example: Next batch in Feb 2026"
    )

    def __str__(self):
        return f"Batch starts {self.start_date}"


# =========================
# Certificate Card
# =========================
class CourseCertificate(models.Model):
    course = models.OneToOneField(
        Courses,
        on_delete=models.CASCADE,
        related_name="certificate"
    )
    title = models.CharField(
        max_length=150,
        default="Certificate Included"
    )
    description = models.CharField(
        max_length=200,
        default="Industry-Recognized Certificate"
    )

    def __str__(self):
        return self.title

# =========================
# CTA Button
# =========================
class CourseCTA(models.Model):
    course = models.OneToOneField(
        Courses,
        on_delete=models.CASCADE,
        related_name="cta"
    )
    button_text = models.CharField(
        max_length=50,
        default="Enroll Course Now"
    )
    url = models.URLField()

    def __str__(self):
        return self.button_text

# =========================
# Curriculum
# =========================
class CourseCurriculum(models.Model):
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="curriculum"
    )
    title = models.CharField(max_length=150)
    duration = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

# =========================
# Technologies
# =========================
class CourseTechnology(models.Model):
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="technologies"
    )
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name

# =========================
# Portfolio Projects
# =========================
# class CourseProject(models.Model):
#     course = models.ForeignKey(
#         Courses,
#         on_delete=models.CASCADE,
#         related_name="projects"
#     )
#     title = models.CharField(max_length=150)
#     order = models.PositiveIntegerField(default=0)

#     class Meta:
#         ordering = ["order"]

#     def __str__(self):
#         return self.title

# =========================
# Career Opportunities
# =========================
class CourseCareerRole(models.Model):
    course = models.ForeignKey(
        Courses,
        on_delete=models.CASCADE,
        related_name="career_roles"
    )
    title = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery/")
    alt_text = models.CharField(
        max_length=150,
        blank=True,
        help_text="Optional description for accessibility"
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Gallery Image {self.id}"
    

class Placement(models.Model):
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    company = models.CharField(max_length=100)

    package_lpa = models.CharField(max_length=20)

    testimonial = models.TextField(blank=True)

    avatar = models.ImageField(upload_to="placements/")

    tag = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
    

class Company(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(
        upload_to="companies/",
        blank=True,
        null=True,
        help_text="Optional logo (can be added later)"
    )

    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
