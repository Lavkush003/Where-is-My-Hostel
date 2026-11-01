"""Accurate distance calculations using the Haversine formula and nearby property queries."""

import math
from typing import Any, Dict, List, Optional, Tuple

EARTH_RADIUS_KM = 6371.0088


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great circle distance between two points on the earth
    (specified in decimal degrees) using the Haversine formula.

    Returns distance in kilometers rounded to 3 decimal places.
    """
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (TypeError, ValueError):
        return 0.0

    # Convert decimal degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp value to prevent domain errors due to floating point inaccuracies
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = EARTH_RADIUS_KM * c
    return round(distance, 3)


def format_distance(distance_km: float) -> str:
    """
    Format a kilometer distance for display to students.
    E.g. 0.45 km -> "450 m", 1.82 km -> "1.8 km", 0.05 km -> "50 m".
    """
    if distance_km < 1.0:
        meters = int(round(distance_km * 1000))
        return f"{meters} m"
    return f"{distance_km:.1f} km"


def find_nearby_properties(
    target_lat: float,
    target_lng: float,
    max_radius_km: float = 5.0,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "nearest",
) -> List[Any]:
    """
    Discover all verified, active properties within max_radius_km from target coordinates.
    Computes real Haversine distance, filters, and sorts according to student preferences.
    """
    from django.db.models import Count
    from properties.models import Property

    filters = filters or {}

    qs = (
        Property.objects.filter(is_active=True, is_approved=True)
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .annotate(
            popularity_score=Count("favourited_by", distinct=True) + Count("enquiries", distinct=True)
        )
        .select_related("owner")
        .prefetch_related("rooms", "images")
    )

    # Optional City filter
    city = filters.get("city")
    if city:
        qs = qs.filter(city__icontains=city.strip())

    # Property Category / Type filter
    property_type = filters.get("property_type") or filters.get("type")
    if property_type:
        property_type = property_type.strip()
        if property_type == "hostel":
            qs = qs.filter(property_type__in=["hostel", "student_hostel", "private_hostel"])
        elif property_type == "room":
            qs = qs.filter(property_type__in=["room", "independent_room", "shared_room"])
        else:
            qs = qs.filter(property_type=property_type)

    # Gender filter
    gender = filters.get("gender")
    if gender and gender in ["boys", "girls", "unisex"]:
        qs = qs.filter(gender_preference=gender)

    nearby_results = []
    for prop in qs:
        dist_km = haversine_distance(
            target_lat,
            target_lng,
            float(prop.latitude),
            float(prop.longitude),
        )

        if dist_km <= max_radius_km:
            # Check room & price-level filters
            min_rent = filters.get("min_rent")
            max_rent = filters.get("max_rent")
            prop_rent = prop.min_monthly_rent

            if min_rent is not None and min_rent != "":
                try:
                    if prop_rent < int(min_rent):
                        continue
                except ValueError:
                    pass

            if max_rent is not None and max_rent != "":
                try:
                    if prop_rent > int(max_rent):
                        continue
                except ValueError:
                    pass

            # Room Occupancy / Sharing filter (e.g. single, double, triple, four)
            sharing = filters.get("sharing")
            if sharing:
                has_sharing = prop.rooms.filter(occupancy=sharing, is_available=True).exists()
                if not has_sharing:
                    continue

            # AC filter (ac, non_ac)
            ac = filters.get("ac")
            if ac in ["ac", "non_ac"]:
                has_ac_room = prop.rooms.filter(air_conditioning=ac, is_available=True).exists()
                if not has_ac_room:
                    continue

            # Available rooms/beds only
            available_only = filters.get("available_only")
            if available_only:
                if prop.total_available_beds <= 0:
                    continue

            # Food availability filter
            food = filters.get("food")
            if food in [True, "1", "true", "True", "yes"]:
                if not any(f.lower() in ["food/mess", "food", "mess", "meals"] for f in prop.facilities_list):
                    continue

            # Wi-Fi filter
            wifi = filters.get("wifi")
            if wifi in [True, "1", "true", "True", "yes"]:
                if not any("wi-fi" in f.lower() or "wifi" in f.lower() for f in prop.facilities_list):
                    continue

            # Attached bathroom filter
            bathroom = filters.get("bathroom")
            if bathroom in ["attached", "Attached", "1", "true", "True"]:
                has_attached = prop.rooms.filter(bathroom_type="attached", is_available=True).exists() or any("attached bathroom" in f.lower() for f in prop.facilities_list)
                if not has_attached:
                    continue

            # Furnished / Unfurnished filter
            furnished = filters.get("furnished")
            if furnished:
                is_furnished = any("furnished" in f.lower() for f in prop.facilities_list) or (
                    any("study table" in f.lower() for f in prop.facilities_list) and any("wardrobe" in f.lower() for f in prop.facilities_list)
                )
                if furnished.lower() == "furnished" and not is_furnished:
                    continue
                elif furnished.lower() == "unfurnished" and is_furnished:
                    continue

            # Facilities filter
            facilities = filters.get("facilities")
            if facilities:
                if isinstance(facilities, str):
                    facilities = [f.strip() for f in facilities.split(",") if f.strip()]
                prop_facilities = prop.facilities_list
                # Property must contain all requested facilities
                if not all(any(req.lower() in pf.lower() for pf in prop_facilities) for req in facilities):
                    continue

            # Attach calculated distance attributes
            prop.distance_km = dist_km
            prop.distance_text = format_distance(dist_km)
            nearby_results.append(prop)

    # Sorting
    if sort_by == "rent_asc":
        nearby_results.sort(key=lambda p: (p.min_monthly_rent, p.distance_km))
    elif sort_by == "rent_desc":
        nearby_results.sort(key=lambda p: (-p.min_monthly_rent, p.distance_km))
    elif sort_by == "recent":
        nearby_results.sort(key=lambda p: -p.created_at.timestamp())
    elif sort_by == "popular":
        nearby_results.sort(key=lambda p: (-getattr(p, "popularity_score", 0), p.distance_km, -p.created_at.timestamp()))
    else:  # 'nearest'
        nearby_results.sort(key=lambda p: (p.distance_km, p.min_monthly_rent))

    return nearby_results

