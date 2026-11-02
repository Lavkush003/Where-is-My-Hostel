"""Admin configuration for locations, cities, states, and landmark models."""

from django.contrib import admin
from .models import City, Landmark, Locality, PlaceCache, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state_name", "tag", "is_popular", "is_active", "latitude", "longitude")
    list_filter = ("is_popular", "is_active", "state_name")
    search_fields = ("name", "tag", "area_summary")
    ordering = ("name",)
    actions = ["mark_popular", "mark_active", "mark_inactive"]

    @admin.action(description="Mark selected cities as Popular")
    def mark_popular(self, request, queryset):
        queryset.update(is_popular=True)

    @admin.action(description="Activate selected cities")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected cities")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "city_name", "pincode", "is_popular", "is_active", "latitude", "longitude")
    list_filter = ("city_name", "is_popular", "is_active")
    search_fields = ("name", "city_name", "pincode")
    ordering = ("city_name", "name")


@admin.register(Landmark)
class LandmarkAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "state", "latitude", "longitude", "is_verified")
    list_filter = ("category", "city", "state", "is_verified")
    search_fields = ("name", "city", "address", "aliases")
    ordering = ("city", "name")


@admin.register(PlaceCache)
class PlaceCacheAdmin(admin.ModelAdmin):
    list_display = ("cache_key", "category", "updated_at")
    search_fields = ("cache_key",)
    readonly_fields = ("created_at", "updated_at")
