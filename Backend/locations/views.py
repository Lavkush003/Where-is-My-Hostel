"""API and discovery views for smart location search and nearby places."""

from typing import Any, Dict
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services.distance import find_nearby_properties, format_distance, haversine_distance
from .services.geocoding import geocode_location, get_landmark_suggestions, reverse_geocode
from .services.overpass import get_nearby_places


@require_GET
def api_geocode(request):
    """
    Geocode an address, institute, railway station or landmark using
    local verified registry and Nominatim OpenStreetMap API.
    """
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"status": "error", "message": "Query parameter 'q' is required."}, status=400)

    result = geocode_location(query)
    if result:
        return JsonResponse({"status": "ok", "result": result})

    return JsonResponse({
        "status": "not_found",
        "message": f"Could not determine coordinates for '{query}'. Please specify city or landmark.",
    }, status=404)


@require_GET
def api_reverse_geocode(request):
    """Reverse geocode latitude and longitude into address fields."""
    lat_str = request.GET.get("lat")
    lng_str = request.GET.get("lng")
    if not lat_str or not lng_str:
        return JsonResponse({"status": "error", "message": "Parameters 'lat' and 'lng' are required."}, status=400)

    try:
        lat = float(lat_str)
        lng = float(lng_str)
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid coordinates format."}, status=400)

    result = reverse_geocode(lat, lng)
    if result:
        return JsonResponse({"status": "ok", "result": result})
    return JsonResponse({"status": "not_found", "message": "Location details not found."}, status=404)


@require_GET
def api_suggest(request):
    """Autocomplete search suggestions for coaching institutes, colleges and cities."""
    query = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 8))
    suggestions = get_landmark_suggestions(query, limit=limit)
    return JsonResponse({"status": "ok", "suggestions": suggestions})


@require_GET
def api_nearby_places(request):
    """
    Query Overpass API for categorized points of interest around coordinates
    (coaching institutes, colleges, railway stations, hospitals, markets).
    """
    lat_str = request.GET.get("lat")
    lng_str = request.GET.get("lng")
    radius_meters = int(request.GET.get("radius", 2500))

    if not lat_str or not lng_str:
        return JsonResponse({"status": "error", "message": "Parameters 'lat' and 'lng' are required."}, status=400)

    try:
        lat = float(lat_str)
        lng = float(lng_str)
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid coordinates."}, status=400)

    # Constrain radius between 500m and 10000m
    radius_meters = max(500, min(10000, radius_meters))

    data = get_nearby_places(lat, lng, radius_meters=radius_meters)
    return JsonResponse({"status": "ok", "data": data})


@require_GET
def api_nearby_properties(request):
    """
    Search and filter verified properties by Haversine distance, budget,
    room type, gender and amenities, returning GeoJSON/JSON for the Leaflet map.
    """
    lat_str = request.GET.get("lat")
    lng_str = request.GET.get("lng")
    destination = request.GET.get("destination", "").strip()

    # If coordinates are missing but a destination string was provided, geocode it
    if (not lat_str or not lng_str) and destination:
        geocoded = geocode_location(destination)
        if geocoded:
            lat_str = str(geocoded["latitude"])
            lng_str = str(geocoded["longitude"])

    if not lat_str or not lng_str:
        return JsonResponse({
            "status": "error",
            "message": "Parameters 'lat' and 'lng' (or 'destination') are required.",
        }, status=400)

    try:
        target_lat = float(lat_str)
        target_lng = float(lng_str)
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid latitude/longitude."}, status=400)

    radius_km = float(request.GET.get("radius", 5.0))
    radius_km = max(0.5, min(15.0, radius_km))

    # Extract filter arguments
    filters = {
        "city": request.GET.get("city", "").strip(),
        "type": request.GET.get("type", "").strip(),
        "gender": request.GET.get("gender", "").strip(),
        "min_rent": request.GET.get("min_rent", "").strip(),
        "max_rent": request.GET.get("max_rent", "").strip(),
        "sharing": request.GET.get("sharing", "").strip(),
        "ac": request.GET.get("ac", "").strip(),
        "available_only": request.GET.get("available_only") in ["1", "true", "True"],
        "facilities": request.GET.get("facilities", "").strip(),
    }
    sort_by = request.GET.get("sort", "nearest")

    # Discover nearby properties
    matched_properties = find_nearby_properties(
        target_lat=target_lat,
        target_lng=target_lng,
        max_radius_km=radius_km,
        filters=filters,
        sort_by=sort_by,
    )

    # Format property items
    prop_data = []
    for p in matched_properties:
        prop_data.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "url": p.get_absolute_url(),
            "property_type": p.property_type,
            "property_type_display": p.get_property_type_display(),
            "gender_preference": p.gender_preference,
            "gender_display": p.get_gender_preference_display(),
            "address": p.address,
            "locality": p.locality,
            "city": p.city,
            "latitude": float(p.latitude),
            "longitude": float(p.longitude),
            "distance_km": p.distance_km,
            "distance_text": p.distance_text,
            "monthly_rent": p.min_monthly_rent,
            "deposit": p.deposit,
            "primary_image_url": p.primary_image_url or "/static/images/rooms/room_single_cozy.jpg",
            "facilities": p.facilities_list[:5],
            "total_available_beds": p.total_available_beds,
            "occupancies": p.room_occupancy_labels,
        })

    # Pagination
    page_num = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 12))
    paginator = Paginator(prop_data, page_size)
    page_obj = paginator.get_page(page_num)

    return JsonResponse({
        "status": "ok",
        "destination": {
            "name": destination or f"{target_lat:.4f}, {target_lng:.4f}",
            "latitude": target_lat,
            "longitude": target_lng,
        },
        "radius_km": radius_km,
        "total_count": len(prop_data),
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "properties": list(page_obj.object_list),
        "all_map_markers": [
            {
                "id": p["id"],
                "name": p["name"],
                "slug": p["slug"],
                "latitude": p["latitude"],
                "longitude": p["longitude"],
                "monthly_rent": p["monthly_rent"],
                "distance_text": p["distance_text"],
                "property_type_display": p["property_type_display"],
                "image_url": p["primary_image_url"],
                "url": p["url"],
            }
            for p in prop_data
        ],
    })
