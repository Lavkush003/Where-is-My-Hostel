"""Admin registrations for property listings, rooms, gallery images and student favourites."""

from django.contrib import admin

from .models import Favourite, Property, PropertyImage, PropertyReport, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
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


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ("image", "category", "caption", "is_primary")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "property_type",
        "gender_preference",
        "city",
        "locality",
        "owner",
        "monthly_rent",
        "approval_status",
        "is_active",
        "is_approved",
        "is_suspended",
        "created_at",
    )
    list_filter = (
        "approval_status",
        "is_approved",
        "is_active",
        "is_suspended",
        "property_type",
        "gender_preference",
        "city",
    )
    search_fields = (
        "name",
        "city",
        "locality",
        "address",
        "landmark",
        "owner__email",
        "owner__full_name",
        "rejection_reason",
    )
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [RoomInline, PropertyImageInline]
    actions = ["approve_properties", "reject_properties", "suspend_properties"]

    @admin.action(description="Approve selected listings for public display")
    def approve_properties(self, request, queryset):
        updated = queryset.update(
            approval_status=Property.ApprovalStatus.APPROVED,
            is_approved=True,
            is_suspended=False,
            rejection_reason="",
        )
        self.message_user(request, f"{updated} propert{'y' if updated == 1 else 'ies'} approved.")

    @admin.action(description="Reject selected listings")
    def reject_properties(self, request, queryset):
        updated = queryset.update(
            approval_status=Property.ApprovalStatus.REJECTED,
            is_approved=False,
        )
        self.message_user(request, f"{updated} propert{'y' if updated == 1 else 'ies'} rejected.")

    @admin.action(description="Suspend selected suspicious listings")
    def suspend_properties(self, request, queryset):
        updated = queryset.update(
            approval_status=Property.ApprovalStatus.SUSPENDED,
            is_approved=False,
            is_suspended=True,
            is_active=False,
        )
        self.message_user(request, f"{updated} propert{'y' if updated == 1 else 'ies'} suspended.")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "room_type",
        "occupancy",
        "monthly_rent",
        "available_beds",
        "total_beds",
        "bathroom_type",
        "air_conditioning",
        "is_available",
    )
    list_filter = (
        "occupancy",
        "bathroom_type",
        "air_conditioning",
        "is_available",
    )
    search_fields = ("property__name", "room_type")


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "category", "caption", "is_primary", "created_at")
    list_filter = ("category", "is_primary")
    search_fields = ("property__name", "caption")


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("student", "property", "created_at")
    search_fields = (
        "student__email",
        "student__full_name",
        "property__name",
    )
    readonly_fields = ("created_at",)


@admin.register(PropertyReport)
class PropertyReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "reason",
        "status",
        "reported_by",
        "reporter_name",
        "reporter_email",
        "created_at",
    )
    list_filter = ("status", "reason", "created_at")
    search_fields = (
        "property__name",
        "details",
        "reporter_name",
        "reporter_email",
        "action_taken",
    )
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_resolved", "mark_dismissed", "suspend_reported_properties"]

    @admin.action(description="Mark selected reports as Resolved")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(status=PropertyReport.Status.RESOLVED, reviewed_by=request.user)
        self.message_user(request, f"{updated} report(s) marked as resolved.")

    @admin.action(description="Mark selected reports as Dismissed")
    def mark_dismissed(self, request, queryset):
        updated = queryset.update(status=PropertyReport.Status.DISMISSED, reviewed_by=request.user)
        self.message_user(request, f"{updated} report(s) dismissed.")

    @admin.action(description="Suspend properties for selected reports and resolve")
    def suspend_reported_properties(self, request, queryset):
        for report in queryset:
            prop = report.property
            prop.approval_status = Property.ApprovalStatus.SUSPENDED
            prop.is_approved = False
            prop.is_suspended = True
            prop.is_active = False
            prop.moderation_notes = f"Suspended following Report #{report.pk}"
            prop.save()
            report.status = PropertyReport.Status.RESOLVED
            report.action_taken = "Suspended listing"
            report.reviewed_by = request.user
            report.save()
        self.message_user(request, f"{queryset.count()} reported propert(ies) suspended.")

