"""Admin registrations for student enquiries."""

from django.contrib import admin

from .models import Enquiry


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "property",
        "status",
        "contact_number",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "student__email",
        "student__full_name",
        "property__name",
        "message",
    )
    readonly_fields = ("created_at", "updated_at")
