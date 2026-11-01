"""Forms for submitting enquiries."""

from django import forms

from .models import Enquiry

FORM_INPUT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white "
    "px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition "
    "placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
)


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ("message", "contact_number")
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "rows": 4,
                    "placeholder": (
                        "Tell the owner about your move-in date, budget and any questions."
                    ),
                }
            ),
            "contact_number": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "inputmode": "tel",
                    "autocomplete": "tel",
                    "placeholder": "Your contact number",
                }
            ),
        }

    def clean_contact_number(self):
        contact_number = self.cleaned_data["contact_number"].strip()
        normalized = contact_number.replace(" ", "").replace("-", "")
        if not normalized.isdigit() or not 10 <= len(normalized) <= 15:
            raise forms.ValidationError(
                "Enter a valid contact number with 10 to 15 digits."
            )
        return normalized
