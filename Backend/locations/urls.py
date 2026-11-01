"""URL routing for locations and geographic API services."""

from django.urls import path
from . import views

app_name = "locations"

urlpatterns = [
    path("api/geocode/", views.api_geocode, name="api_geocode"),
    path("api/reverse-geocode/", views.api_reverse_geocode, name="api_reverse_geocode"),
    path("api/suggest/", views.api_suggest, name="api_suggest"),
    path("api/nearby-places/", views.api_nearby_places, name="api_nearby_places"),
    path("api/properties/nearby/", views.api_nearby_properties, name="api_nearby_properties"),
]
