"""Forms for property listings, room configurations, and gallery image uploads."""

from django import forms
from django.core.exceptions import ValidationError

from .models import AVAILABLE_FACILITIES, Property, PropertyImage, Room

FORM_INPUT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white "
    "px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition "
    "placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
)

FORM_SELECT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white "
    "px-4 py-3 text-sm text-slate-900 shadow-sm outline-none transition "
    "focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
)

FILE_INPUT_CLASS = (
    "block w-full rounded-lg border border-slate-300 bg-white "
    "px-4 py-3 text-sm text-slate-600 file:mr-3 file:rounded-md "
    "file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 "
    "file:text-sm file:font-semibold file:text-brand-700"
)


class PropertyForm(forms.ModelForm):
    gender_preference = forms.ChoiceField(
        choices=Property.GenderPreference.choices,
        initial=Property.GenderPreference.UNISEX,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    facility_choices = forms.MultipleChoiceField(
        choices=AVAILABLE_FACILITIES,
        widget=forms.CheckboxSelectMultiple(
            attrs={"class": "rounded border-slate-300 text-brand-600 focus:ring-brand-500"}
        ),
        required=False,
        label="Facilities & Amenities",
        help_text="Select all amenities offered at this property.",
    )

    class Meta:
        model = Property
        fields = (
            "name",
            "property_type",
            "gender_preference",
            "description",
            "address",
            "locality",
            "city",
            "state",
            "pincode",
            "landmark",
            "latitude",
            "longitude",
            "monthly_rent",
            "deposit",
            "available_from",
            "contact_number",
            "facilities",
            "image",
            "is_active",
        )
        widgets = {
            "name": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Royal Student Residency"}
            ),
            "property_type": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "gender_preference": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "description": forms.Textarea(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "rows": 5,
                    "placeholder": "Describe your PG or hostel, environment, mess timings, rules, etc.",
                }
            ),
            "address": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "Complete street address"}
            ),
            "locality": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Civil Lines, Talwandi, Mukherjee Nagar"}
            ),
            "city": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Prayagraj, Kota, Delhi"}),
            "state": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Uttar Pradesh, Rajasthan"}),
            "pincode": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. 211001"}),
            "landmark": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Near Allen Samyak, 500m from Metro"}
            ),
            "latitude": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "step": "0.000001", "placeholder": "e.g. 25.435801"}
            ),
            "longitude": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "step": "0.000001", "placeholder": "e.g. 81.846311"}
            ),
            "monthly_rent": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "min": 0, "placeholder": "e.g. 6500"}
            ),
            "deposit": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. One month rent (refundable)"}
            ),
            "available_from": forms.DateInput(
                attrs={"class": FORM_INPUT_CLASS, "type": "date"}
            ),
            "contact_number": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "inputmode": "tel",
                    "autocomplete": "tel",
                    "placeholder": "10-digit mobile number",
                }
            ),
            "facilities": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "placeholder": "Additional custom facilities (comma separated)",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": FILE_INPUT_CLASS, "accept": "image/*"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-5 w-5 rounded border-slate-300 text-brand-700 focus:ring-brand-500"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.facilities:
            current_facilities = [f.strip() for f in self.instance.facilities.split(",") if f.strip()]
            self.fields["facility_choices"].initial = [
                f for f, _ in AVAILABLE_FACILITIES if f in current_facilities
            ]

    def clean_gender_preference(self):
        val = self.cleaned_data.get("gender_preference")
        return val or Property.GenderPreference.UNISEX

    def clean_monthly_rent(self):
        monthly_rent = self.cleaned_data.get("monthly_rent")
        if monthly_rent is not None and monthly_rent < 0:
            raise forms.ValidationError("Monthly rent cannot be negative.")
        return monthly_rent

    def clean_contact_number(self):
        contact_number = self.cleaned_data["contact_number"].strip()
        normalized = contact_number.replace(" ", "").replace("-", "")
        if not normalized.isdigit() or not 10 <= len(normalized) <= 15:
            raise forms.ValidationError(
                "Enter a valid contact number with 10 to 15 digits."
            )
        return normalized

    def clean_latitude(self):
        lat = self.cleaned_data.get("latitude")
        if lat is not None:
            if lat < -90 or lat > 90:
                raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
            from decimal import Decimal
            return round(Decimal(str(lat)), 6)
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data.get("longitude")
        if lng is not None:
            if lng < -180 or lng > 180:
                raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
            from decimal import Decimal
            return round(Decimal(str(lng)), 6)
        return lng

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get("latitude")
        lng = cleaned_data.get("longitude")

        # Automatically geocode if latitude or longitude is missing
        if (not lat or not lng) and cleaned_data.get("city"):
            from decimal import Decimal
            from locations.services.geocoding import geocode_location
            address = cleaned_data.get("address", "")
            landmark = cleaned_data.get("landmark", "")
            locality = cleaned_data.get("locality", "")
            city = cleaned_data.get("city", "")

            query_candidates = [
                f"{address}, {city}".strip(", "),
                f"{landmark}, {city}".strip(", ") if landmark else None,
                f"{locality}, {city}".strip(", ") if locality else None,
                city,
            ]
            for query in query_candidates:
                if query:
                    geo = geocode_location(query)
                    if geo:
                        cleaned_data["latitude"] = round(Decimal(str(geo["latitude"])), 6)
                        cleaned_data["longitude"] = round(Decimal(str(geo["longitude"])), 6)
                        break
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected = list(self.cleaned_data.get("facility_choices") or [])
        custom = self.cleaned_data.get("facilities") or ""
        custom_items = [item.strip() for item in custom.split(",") if item.strip()]

        # Merge selected standard facilities and custom facilities
        combined = []
        for f in selected + custom_items:
            if f and f not in combined:
                combined.append(f)
        instance.facilities = ", ".join(combined)

        if commit:
            instance.save()
        return instance


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = (
            "room_type",
            "occupancy",
            "monthly_rent",
            "security_deposit",
            "total_beds",
            "available_beds",
            "bathroom_type",
            "air_conditioning",
            "is_available",
        )
        widgets = {
            "room_type": forms.TextInput(
                attrs={
                    "class": FORM_INPUT_CLASS,
                    "placeholder": "e.g. Deluxe Single AC or Standard Double",
                }
            ),
            "occupancy": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "monthly_rent": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "min": 1, "placeholder": "Rent in ₹ per month"}
            ),
            "security_deposit": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "min": 0, "placeholder": "Deposit in ₹"}
            ),
            "total_beds": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "min": 1, "value": 1}
            ),
            "available_beds": forms.NumberInput(
                attrs={"class": FORM_INPUT_CLASS, "min": 0, "value": 1}
            ),
            "bathroom_type": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "air_conditioning": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "is_available": forms.CheckboxInput(
                attrs={"class": "h-5 w-5 rounded border-slate-300 text-brand-700 focus:ring-brand-500"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        total_beds = cleaned_data.get("total_beds")
        available_beds = cleaned_data.get("available_beds")

        if total_beds is not None and available_beds is not None:
            if available_beds > total_beds:
                self.add_error(
                    "available_beds",
                    "Available beds cannot exceed total beds in this room configuration.",
                )
        return cleaned_data


class PropertyImageForm(forms.ModelForm):
    class Meta:
        model = PropertyImage
        fields = ("image", "category", "caption", "is_primary")
        widgets = {
            "image": forms.ClearableFileInput(
                attrs={"class": FILE_INPUT_CLASS, "accept": "image/*"}
            ),
            "category": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "caption": forms.TextInput(
                attrs={"class": FORM_INPUT_CLASS, "placeholder": "e.g. Spacious study area with natural light"}
            ),
            "is_primary": forms.CheckboxInput(
                attrs={"class": "h-5 w-5 rounded border-slate-300 text-brand-700 focus:ring-brand-500"}
            ),
        }

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if img:
            # 5MB limit
            if img.size > 5 * 1024 * 1024:
                raise ValidationError("Image file size cannot exceed 5MB.")
        return img
