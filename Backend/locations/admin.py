"""Admin configuration for locations and landmark models."""

from django.contrib import admin
from .models import Landmark, PlaceCache


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
