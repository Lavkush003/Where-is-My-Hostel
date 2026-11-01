"""Admin registrations for property listings, rooms, gallery images and student favourites."""

from django.contrib import admin

from .models import Favourite, Property, PropertyImage, Room


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
        "is_active",
        "is_approved",
        "created_at",
    )
    list_filter = (
        "property_type",
        "gender_preference",
        "city",
        "is_active",
        "is_approved",
    )
    search_fields = (
        "name",
        "city",
        "locality",
        "address",
        "landmark",
        "owner__email",
        "owner__full_name",
    )
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [RoomInline, PropertyImageInline]
    actions = ["approve_properties", "disapprove_properties"]

    @admin.action(description="Approve selected listings for public display")
    def approve_properties(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} propert{'y' if updated == 1 else 'ies'} approved.")

    @admin.action(description="Revoke public approval for selected listings")
    def disapprove_properties(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} propert{'y' if updated == 1 else 'ies'} unapproved.")


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
