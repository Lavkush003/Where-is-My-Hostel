"""Admin registrations for custom users and owner profiles."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import OwnerProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "full_name",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "full_name", "mobile_number")
    ordering = ("full_name", "username")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "mobile_number",
                    "role",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Profile",
            {
                "classes": ("wide",),
                "fields": (
                    "full_name",
                    "email",
                    "mobile_number",
                    "role",
                ),
            },
        ),
    )


@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "owner_name",
        "user",
        "city",
        "contact_number",
    )
    search_fields = (
        "business_name",
        "owner_name",
        "user__email",
        "user__username",
        "city",
    )
    list_filter = ("city",)
