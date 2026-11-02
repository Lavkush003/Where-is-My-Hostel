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
    actions = ["activate_users", "deactivate_users"]

    @admin.action(description="Activate selected accounts")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    @admin.action(description="Deactivate selected accounts")
    def deactivate_users(self, request, queryset):
        # Exclude current admin
        safe_qs = queryset.exclude(pk=request.user.pk)
        updated = safe_qs.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")


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
