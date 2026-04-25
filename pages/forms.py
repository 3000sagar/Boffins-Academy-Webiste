from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import ContactMessage, Course, Courses, FeedbackSubmission


class ContactForm(forms.ModelForm):
    course_interest = forms.ModelChoiceField(
        queryset=Course.objects.filter(is_active=True),
        required=False,
        empty_label="Select a course"
    )

    class Meta:
        model = ContactMessage
        fields = [
            "full_name",
            "email",
            "phone",
            "course_interest",
            "message",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Full Name",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Email Id",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Phone No.",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm"
            }),
            "course_interest": forms.Select(attrs={
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "message": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Tell us about your goals and how we can help you.",
                "class": "w-full rounded-lg border border-[#E6E2F0] px-4 py-3 text-sm resize-none"
            }),
        }


class FeedbackForm(forms.ModelForm):
    overall_rating = forms.IntegerField(
        required=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        widget=forms.HiddenInput(attrs={"id": "id_overall_rating"}),
    )
    instructor_rating = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        widget=forms.HiddenInput(attrs={"id": "id_instructor_rating"}),
    )

    class Meta:
        model = FeedbackSubmission
        fields = [
            "full_name",
            "email",
            "phone",
            "submitter_type",
            "course",
            "overall_rating",
            "instructor_rating",
            "message",
            "testimonial_consent",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Full Name",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "Email Address",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "Phone Number (optional)",
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm"
            }),
            "submitter_type": forms.RadioSelect(attrs={"class": "flex gap-4"}),
            "course": forms.Select(attrs={
                "class": "h-10 w-full rounded-lg border border-[#E6E2F0] px-4 text-sm focus:border-[#6B4EFF] focus:ring-2 focus:ring-[#6B4EFF]/20 outline-none"
            }),
            "message": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "What did you enjoy? What could we improve?",
                "class": "w-full rounded-lg border border-[#E6E2F0] px-4 py-3 text-sm resize-none"
            }),
            "testimonial_consent": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded border-[#E6E2F0] text-[#6B4EFF] focus:ring-[#6B4EFF]/20"
            }),
        }

    def clean_overall_rating(self):
        rating = self.cleaned_data.get("overall_rating")
        if rating is None or rating < 1 or rating > 5:
            raise forms.ValidationError("Please select a rating between 1 and 5 stars.")
        return rating

    def clean_instructor_rating(self):
        rating = self.cleaned_data.get("instructor_rating")
        if rating is not None and (rating < 1 or rating > 5):
            raise forms.ValidationError("Instructor rating must be between 1 and 5 stars.")
        return rating

    def clean(self):
        cleaned_data = super().clean()
        submitter_type = cleaned_data.get("submitter_type")
        course = cleaned_data.get("course")
        instructor_rating = cleaned_data.get("instructor_rating")

        if submitter_type == "student" and not course:
            self.add_error("course", "Please select the course you are enrolled in.")

        if submitter_type == "visitor" and instructor_rating:
            cleaned_data["instructor_rating"] = None

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Courses.objects.filter(is_active=True).order_by("title")
        self.fields["course"].empty_label = "Select a course"
