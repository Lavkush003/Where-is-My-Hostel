"""OpenStreetMap Overpass API service for discovering verified nearby facilities and landmarks."""

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from django.core.cache import cache

from .distance import format_distance, haversine_distance

logger = logging.getLogger(__name__)

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "WhereIsMyHostel/1.0 (+https://whereismyhostel.com; contact@whereismyhostel.com)"
OVERPASS_CACHE_TTL = 7 * 24 * 3600  # 7 days

# Mapping of OSM tags to clean student-centric category labels & icons
CATEGORY_MAPPINGS = {
    # Education
    ("amenity", "college"): ("College & University", "education", "🎓"),
    ("amenity", "university"): ("College & University", "education", "🏛️"),
    ("amenity", "prep_school"): ("Coaching & Institute", "coaching", "📚"),
    ("amenity", "school"): ("School & Academy", "education", "🏫"),
    ("amenity", "library"): ("Study Library", "coaching", "📖"),
    # Transit
    ("railway", "station"): ("Railway Station", "transit", "🚆"),
    ("railway", "subway_entrance"): ("Metro Station", "transit", "🚇"),
    ("amenity", "bus_station"): ("Bus Station", "transit", "🚌"),
    ("highway", "bus_stop"): ("Bus Stop", "transit", "🚏"),
    # Essentials
    ("amenity", "hospital"): ("Hospital", "healthcare", "🏥"),
    ("amenity", "clinic"): ("Clinic & Medical", "healthcare", "🩺"),
    ("amenity", "pharmacy"): ("Pharmacy & Chemist", "healthcare", "💊"),
    ("amenity", "police"): ("Police Station", "safety", "👮"),
    # Food & Shopping
    ("shop", "mall"): ("Shopping Mall", "market", "🛍️"),
    ("shop", "supermarket"): ("Supermarket & Grocery", "market", "🛒"),
    ("shop", "convenience"): ("Local Grocery Store", "market", "🏪"),
    ("amenity", "restaurant"): ("Restaurant & Mess", "food", "🍽️"),
    ("amenity", "fast_food"): ("Fast Food & Eatery", "food", "🍕"),
    ("amenity", "cafe"): ("Student Cafe", "food", "☕"),
}


def _classify_osm_element(tags: Dict[str, str]) -> Tuple[str, str, str]:
    """Determine display category, category code, and icon for an OSM tag set."""
    for (key, val), (cat_name, cat_code, icon) in CATEGORY_MAPPINGS.items():
        if tags.get(key) == val:
            return cat_name, cat_code, icon

    # Secondary checks
    if "college" in tags.get("name", "").lower() or "university" in tags.get("name", "").lower():
        return "College & University", "education", "🎓"
    if "coaching" in tags.get("name", "").lower() or "academy" in tags.get("name", "").lower() or "classes" in tags.get("name", "").lower():
        return "Coaching & Institute", "coaching", "📚"
    if "station" in tags.get("name", "").lower() or "junction" in tags.get("name", "").lower():
        return "Railway Station", "transit", "🚆"
    if "hospital" in tags.get("name", "").lower() or "medical" in tags.get("name", "").lower():
        return "Hospital", "healthcare", "🏥"
    if "mall" in tags.get("name", "").lower() or "market" in tags.get("name", "").lower():
        return "Market & Shopping", "market", "🛍️"

    return "Point of Interest", "other", "📍"


def _fallback_places_from_db(lat: float, lng: float, radius_meters: int) -> List[Dict[str, Any]]:
    """
    Fallback to Landmark database and nearby properties when external Overpass API
    is unreachable or during isolated automated test execution.
    """
    from locations.models import Landmark

    radius_km = radius_meters / 1000.0
    results = []
    seen_names = set()

    try:
        landmarks = Landmark.objects.all()
        for lm in landmarks:
            dist_km = haversine_distance(lat, lng, float(lm.latitude), float(lm.longitude))
            if dist_km <= radius_km and lm.name not in seen_names:
                seen_names.add(lm.name)
                cat_display = lm.get_category_display()
                icon = "📍"
                cat_code = lm.category
                if lm.category in ["coaching", "college", "university"]:
                    icon = "🎓"
                    cat_code = "education"
                elif lm.category in ["railway_station", "bus_station", "metro_station"]:
                    icon = "🚆"
                    cat_code = "transit"
                elif lm.category == "hospital":
                    icon = "🏥"
                    cat_code = "healthcare"
                elif lm.category == "market":
                    icon = "🛍️"
                    cat_code = "market"

                results.append({
                    "name": lm.name,
                    "category": cat_display,
                    "category_code": cat_code,
                    "icon": icon,
                    "latitude": float(lm.latitude),
                    "longitude": float(lm.longitude),
                    "distance_km": dist_km,
                    "distance_text": format_distance(dist_km),
                })
    except Exception as exc:
        logger.debug("Database fallback places error: %s", exc)

    results.sort(key=lambda x: x["distance_km"])
    return results


def get_nearby_places(
    lat: float,
    lng: float,
    radius_meters: int = 2500,
) -> Dict[str, Any]:
    """
    Query OpenStreetMap Overpass API for real facilities, coaching centres,
    railway stations, hospitals, and markets around (lat, lng).
    Results are cached in Django cache and persistent database cache.
    """
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return {"all": [], "by_category": {}, "count": 0}

    # Normalize coordinate grid for caching (approx 100-meter bucket)
    grid_lat = round(lat, 3)
    grid_lng = round(lng, 3)
    cache_key = f"overpass_poi_{grid_lat}_{grid_lng}_{radius_meters}"

    cached = cache.get(cache_key)
    if cached:
        return cached

    # Check persistent PlaceCache model
    try:
        from locations.models import PlaceCache

        db_cache = PlaceCache.objects.filter(cache_key=cache_key).first()
        if db_cache and db_cache.data:
            cache.set(cache_key, db_cache.data, OVERPASS_CACHE_TTL)
            return db_cache.data
    except Exception as exc:
        logger.debug("PlaceCache query error: %s", exc)

    # Construct Overpass QL Query
    query_ql = f"""
    [out:json][timeout:5];
    (
      node["amenity"~"college|university|prep_school|school|library|hospital|clinic|pharmacy|police|restaurant|fast_food|bus_station"](around:{radius_meters},{lat},{lng});
      node["railway"~"station|subway_entrance"](around:{radius_meters},{lat},{lng});
      node["highway"="bus_stop"](around:{radius_meters},{lat},{lng});
      node["shop"~"supermarket|convenience|mall"](around:{radius_meters},{lat},{lng});
      way["amenity"~"college|university|hospital|police"](around:{radius_meters},{lat},{lng});
      way["shop"="mall"](around:{radius_meters},{lat},{lng});
    );
    out center tags 40;
    """

    places: List[Dict[str, Any]] = []
    seen_names = set()

    try:
        req = urllib.request.Request(
            OVERPASS_API_URL,
            data=urllib.parse.urlencode({"data": query_ql}).encode("utf-8"),
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                elements = body.get("elements", [])
                for el in elements:
                    tags = el.get("tags", {})
                    name = tags.get("name") or tags.get("name:en")
                    if not name or name in seen_names:
                        continue

                    # Extract coordinates (node has lat/lon, way has center)
                    item_lat = el.get("lat") or el.get("center", {}).get("lat")
                    item_lng = el.get("lon") or el.get("center", {}).get("lon")
                    if not item_lat or not item_lng:
                        continue

                    dist_km = haversine_distance(lat, lng, float(item_lat), float(item_lng))
                    cat_name, cat_code, icon = _classify_osm_element(tags)

                    seen_names.add(name)
                    places.append({
                        "name": name,
                        "category": cat_name,
                        "category_code": cat_code,
                        "icon": icon,
                        "latitude": round(float(item_lat), 6),
                        "longitude": round(float(item_lng), 6),
                        "distance_km": dist_km,
                        "distance_text": format_distance(dist_km),
                    })
    except Exception as exc:
        logger.info("Overpass API request failed or timed out: %s. Using local landmark fallback.", exc)

    # If Overpass returned no results or failed, use local curated database fallback
    if not places:
        places = _fallback_places_from_db(lat, lng, radius_meters)

    # Sort all places by distance
    places.sort(key=lambda x: x["distance_km"])

    # Group into categories for student view
    by_category: Dict[str, List[Dict[str, Any]]] = {
        "coaching": [],
        "education": [],
        "transit": [],
        "healthcare": [],
        "market": [],
        "food": [],
        "safety": [],
        "other": [],
    }
    for p in places:
        cat = p.get("category_code", "other")
        if cat in by_category:
            by_category[cat].append(p)
        else:
            by_category["other"].append(p)

    result = {
        "all": places[:30],
        "by_category": by_category,
        "count": len(places),
        "center": {"lat": lat, "lng": lng},
        "radius_meters": radius_meters,
    }

    # Cache in memory and DB
    cache.set(cache_key, result, OVERPASS_CACHE_TTL)
    try:
        from locations.models import PlaceCache

        PlaceCache.objects.update_or_create(
            cache_key=cache_key,
            defaults={"data": result, "category": "osm_pois"},
        )
    except Exception as exc:
        logger.debug("Error storing in PlaceCache: %s", exc)

    return result
