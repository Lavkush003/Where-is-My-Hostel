"""Forms for registration, authentication and profile management."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import OwnerProfile, User

FORM_INPUT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white "
    "px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition "
    "placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
)
FORM_SELECT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white px-4 py-3 "
    "text-sm text-slate-900 shadow-sm outline-none transition "
    "focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
)


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "autocomplete": "username",
                "placeholder": "you@example.com or username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "autocomplete": "current-password",
                "placeholder": "Password",
            }
        )
    )


class RegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "autocomplete": "name",
                "placeholder": "Your full name",
            }
        ),
    )
    email = forms.EmailField(
        label="Email address",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    mobile_number = forms.CharField(
        label="Mobile number",
        max_length=16,
        widget=forms.TextInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "autocomplete": "tel",
                "inputmode": "tel",
                "placeholder": "9876543210",
            }
        ),
    )
    account_type = forms.ChoiceField(
        label="Account type",
        choices=(
            (User.Role.STUDENT, "Student"),
            (User.Role.OWNER, "Property Owner"),
        ),
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("full_name", "email", "mobile_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", FORM_INPUT_CLASS)
        self.fields["account_type"].widget.attrs.update({"class": FORM_SELECT_CLASS})
        self.fields["password1"].label = "Password"
        self.fields["password1"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Create a password",
            }
        )
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].widget.attrs.update(
            {
                "autocomplete": "new-password",
                "placeholder": "Confirm your password",
            }
        )

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not full_name:
            raise forms.ValidationError("Enter your full name.")
        return full_name

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )
        return email

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data["mobile_number"].strip()
        normalized = mobile_number.replace(" ", "").replace("-", "")
        self.fields["mobile_number"].run_validators(normalized)
        return normalized

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"].strip().lower()
        user.full_name = self.cleaned_data["full_name"].strip()
        user.email = email
        user.mobile_number = self.cleaned_data["mobile_number"].strip()
        user.role = self.cleaned_data["account_type"]
        user.username = User.generate_unique_username(email)

        if commit:
            user.save()
            if user.role == User.Role.OWNER:
                OwnerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "owner_name": user.full_name,
                        "contact_number": user.mobile_number,
                    },
                )
        return user


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "mobile_number")
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "name",
                }
            ),
            "mobile_number": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),
        }

    def clean_full_name(self):
        full_name = self.cleaned_data["full_name"].strip()
        if not full_name:
            raise forms.ValidationError("Enter your full name.")
        return full_name

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data["mobile_number"].strip()
        normalized = mobile_number.replace(" ", "").replace("-", "")
        self.fields["mobile_number"].run_validators(normalized)
        return normalized


class OwnerProfileForm(forms.ModelForm):
    class Meta:
        model = OwnerProfile
        fields = (
            "owner_name",
            "contact_number",
            "business_name",
            "profile_photo",
            "address",
            "city",
        )
        widgets = {
            "owner_name": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "name",
                }
            ),
            "contact_number": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "tel",
                    "inputmode": "tel",
                }
            ),
            "business_name": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "placeholder": "Business or property management name",
                }
            ),
            "profile_photo": forms.ClearableFileInput(
                attrs={
                    "class": (
                        "block w-full rounded-lg border border-slate-300 bg-white "
                        "px-4 py-3 text-sm text-slate-600 file:mr-3 file:rounded-md "
                        "file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 "
                        "file:text-sm file:font-semibold file:text-brand-700"
                    ),
                    "accept": "image/*",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "street-address",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "autocomplete": "address-level2",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("owner_name", "contact_number", "business_name", "address", "city"):
            self.fields[field_name].required = field_name in {
                "owner_name",
                "contact_number",
                "business_name",
            }

    def clean_contact_number(self):
        contact_number = self.cleaned_data["contact_number"].strip()
        normalized = contact_number.replace(" ", "").replace("-", "")
        self.fields["contact_number"].run_validators(normalized)
        return normalized

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo:
            import os
            if hasattr(photo, "size") and photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Profile photo file size cannot exceed 5MB.")
            ext = os.path.splitext(getattr(photo, "name", ""))[1].lower()
            if ext and ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                raise forms.ValidationError("Only JPG, JPEG, PNG, or WEBP image formats are supported.")
        return photo
