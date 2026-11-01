"""Forms for submitting and managing student property enquiries."""

from datetime import date
from django import forms

from .models import Enquiry

FORM_INPUT_CLASS = (
    "block w-full rounded-xl border border-slate-300 bg-white "
    "px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-sm outline-none transition "
    "placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-200"
)


class EnquiryForm(forms.ModelForm):
    def __init__(self, *args, student=None, property_obj=None, **kwargs):
        self.student = student
        self.property_obj = property_obj
        super().__init__(*args, **kwargs)

    class Meta:
        model = Enquiry
        fields = ("move_in_date", "occupancy", "message", "contact_number")
        widgets = {
            "move_in_date": forms.DateInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "type": "date",
                }
            ),
            "occupancy": forms.Select(
                attrs={
                    "class": FORM_INPUT_CLASS,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "rows": 3,
                    "placeholder": (
                        "Describe your requirements, study schedule, or specific questions for the owner..."
                    ),
                }
            ),
            "contact_number": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "inputmode": "tel",
                    "autocomplete": "tel",
                    "placeholder": "Your active 10-digit mobile number",
                }
            ),
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data.get("contact_number", "").strip()
        normalized = contact_number.replace(" ", "").replace("-", "").replace("+", "")
        if not normalized.isdigit() or not (10 <= len(normalized) <= 15):
            raise forms.ValidationError(
                "Enter a valid mobile or contact number with 10 to 15 digits."
            )
        return normalized

    def clean_move_in_date(self):
        move_in = self.cleaned_data.get("move_in_date")
        if move_in and move_in < date.today():
            raise forms.ValidationError("Preferred move-in date cannot be in the past.")
        return move_in

    def clean(self):
        cleaned_data = super().clean()
        if self.student and self.property_obj:
            active_exists = Enquiry.objects.filter(
                student=self.student,
                property=self.property_obj,
                status__in=[
                    Enquiry.Status.PENDING,
                    Enquiry.Status.CONTACTED,
                    Enquiry.Status.ACCEPTED,
                ],
            ).exists()
            if active_exists:
                raise forms.ValidationError(
                    "You already have an active enquiry for this property. "
                    "You can track or cancel it from your student dashboard."
                )
        return cleaned_data
