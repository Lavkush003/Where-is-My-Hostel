"""Nominatim OpenStreetMap geocoding service with caching, throttling, and landmark fallbacks."""

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from django.core.cache import cache
from django.db.models import Q

logger = logging.getLogger(__name__)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "WhereIsMyHostel/1.0 (+https://whereismyhostel.com; student-housing-search@whereismyhostel.com)"
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
_LAST_REQUEST_TIME = 0.0

# Pre-curated student landmarks for instant zero-latency lookup and offline resilience
CURATED_LANDMARKS: List[Dict[str, Any]] = [
    {
        "name": "Allen Career Institute, Kota",
        "city": "Kota",
        "state": "Rajasthan",
        "category": "coaching",
        "latitude": 25.1388,
        "longitude": 75.8454,
        "address": "Sankalp, CP-6, Indra Vihar, Kota, Rajasthan 324005",
        "aliases": ["allen kota", "allen sangyan", "allen career institute", "allen indra vihar"],
    },
    {
        "name": "Resonance, Kota",
        "city": "Kota",
        "state": "Rajasthan",
        "category": "coaching",
        "latitude": 25.1485,
        "longitude": 75.8480,
        "address": "CG Tower, A-46 & 52, IPIA, Near City Mall, Jhalawar Road, Kota",
        "aliases": ["resonance kota", "resonance", "resonance ipia"],
    },
    {
        "name": "Motion Education, Kota",
        "city": "Kota",
        "state": "Rajasthan",
        "category": "coaching",
        "latitude": 25.1395,
        "longitude": 75.8440,
        "address": "394, Rajeev Gandhi Nagar, Kota, Rajasthan",
        "aliases": ["motion kota", "motion rajeev gandhi nagar"],
    },
    {
        "name": "Kota Junction Railway Station",
        "city": "Kota",
        "state": "Rajasthan",
        "category": "railway_station",
        "latitude": 25.2212,
        "longitude": 75.8648,
        "address": "Bhimganj Mandi, Kota, Rajasthan",
        "aliases": ["kota junction", "kota station", "kota railway station"],
    },
    {
        "name": "Prayagraj Junction Railway Station",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "category": "railway_station",
        "latitude": 25.4484,
        "longitude": 81.8267,
        "address": "Civil Lines, Prayagraj, Uttar Pradesh 211001",
        "aliases": ["prayagraj junction", "allahabad junction", "prayagraj station"],
    },
    {
        "name": "Allahabad University",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "category": "university",
        "latitude": 25.4593,
        "longitude": 81.8601,
        "address": "Senate House Campus, University Road, Old Katra, Prayagraj",
        "aliases": ["au", "allahabad university", "university of allahabad", "katra prayagraj"],
    },
    {
        "name": "Civil Lines, Prayagraj",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "category": "locality",
        "latitude": 25.4526,
        "longitude": 81.8349,
        "address": "Civil Lines, Prayagraj, Uttar Pradesh",
        "aliases": ["civil lines", "civil lines prayagraj", "tagore town"],
    },
    {
        "name": "Motilal Nehru National Institute of Technology (MNNIT)",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "category": "college",
        "latitude": 25.4925,
        "longitude": 81.8639,
        "address": "Teliarganj, Prayagraj, Uttar Pradesh 211004",
        "aliases": ["mnnit", "mnnit prayagraj", "mnnit allahabad", "teliarganj"],
    },
    {
        "name": "Mukherjee Nagar, Delhi",
        "city": "Delhi",
        "state": "Delhi",
        "category": "locality",
        "latitude": 28.7107,
        "longitude": 77.2144,
        "address": "Mukherjee Nagar, North Delhi, Delhi 110009",
        "aliases": ["mukherjee nagar", "upsc hub delhi", "drishti ias delhi", "batra cinema"],
    },
    {
        "name": "Karol Bagh, Delhi",
        "city": "Delhi",
        "state": "Delhi",
        "category": "locality",
        "latitude": 28.6517,
        "longitude": 77.1906,
        "address": "Karol Bagh, Central Delhi, Delhi 110005",
        "aliases": ["karol bagh", "pusa road", "vajiram delhi"],
    },
    {
        "name": "Boring Road, Patna",
        "city": "Patna",
        "state": "Bihar",
        "category": "locality",
        "latitude": 25.6137,
        "longitude": 85.1189,
        "address": "Boring Road, Patna, Bihar 800001",
        "aliases": ["boring road", "boring road patna", "kankarbagh patna"],
    },
    {
        "name": "Patna Junction Railway Station",
        "city": "Patna",
        "state": "Bihar",
        "category": "railway_station",
        "latitude": 25.6022,
        "longitude": 85.1376,
        "address": "Station Road, Fraser Road Area, Patna, Bihar 800001",
        "aliases": ["patna junction", "patna station"],
    },
    {
        "name": "Gopalpura Bypass, Jaipur",
        "city": "Jaipur",
        "state": "Rajasthan",
        "category": "locality",
        "latitude": 26.8524,
        "longitude": 75.7766,
        "address": "Gopalpura Bypass Road, Jaipur, Rajasthan",
        "aliases": ["gopalpura", "gopalpura bypass", "allen jaipur"],
    },
    {
        "name": "Ameerpet, Hyderabad",
        "city": "Hyderabad",
        "state": "Telangana",
        "category": "locality",
        "latitude": 17.4375,
        "longitude": 78.4482,
        "address": "Ameerpet, Hyderabad, Telangana 500016",
        "aliases": ["ameerpet", "koti hyderabad", "osmania"],
    },
    {
        "name": "Civil Lines Bus Station, Prayagraj",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "category": "bus_station",
        "latitude": 25.4510,
        "longitude": 81.8315,
        "address": "Civil Lines Bus Station, MG Marg, Prayagraj, UP",
        "aliases": ["civil lines bus stand", "prayagraj bus stand", "zero road bus station", "bus stand"],
    },
    {
        "name": "Kota Inter State Bus Stand (Nayapura)",
        "city": "Kota",
        "state": "Rajasthan",
        "category": "bus_station",
        "latitude": 25.1884,
        "longitude": 75.8398,
        "address": "Nayapura Bus Stand, Kota, Rajasthan",
        "aliases": ["kota bus stand", "nayapura bus stand", "bus stand kota"],
    },
    {
        "name": "Kashmere Gate ISBT, Delhi",
        "city": "Delhi",
        "state": "Delhi",
        "category": "bus_station",
        "latitude": 28.6675,
        "longitude": 77.2285,
        "address": "Maharana Pratap Inter-State Bus Terminus, Kashmere Gate, Delhi",
        "aliases": ["isbt kashmere gate", "delhi bus stand", "anand vihar bus stand", "isbt delhi"],
    },
    {
        "name": "Sindhi Camp Central Bus Stand, Jaipur",
        "city": "Jaipur",
        "state": "Rajasthan",
        "category": "bus_station",
        "latitude": 26.9238,
        "longitude": 75.8012,
        "address": "Station Road, Sindhi Camp, Jaipur, Rajasthan",
        "aliases": ["sindhi camp", "jaipur bus stand", "sindhi camp bus stand"],
    },
]


def _throttle_request() -> None:
    """Enforce at least 1.0 second between consecutive calls to Nominatim API."""
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _LAST_REQUEST_TIME = time.time()


def _search_curated_landmarks(query: str) -> Optional[Dict[str, Any]]:
    """Match query against built-in curated landmark registry."""
    q_norm = query.lower().strip()
    for item in CURATED_LANDMARKS:
        if q_norm == item["name"].lower() or q_norm == item["city"].lower():
            return item
        if any(q_norm in alias or alias in q_norm for alias in item.get("aliases", [])):
            return item
        if item["name"].lower() in q_norm or q_norm in item["name"].lower():
            return item
    return None


def _search_database_landmarks(query: str) -> Optional[Dict[str, Any]]:
    """Query Landmark model in database."""
    try:
        from locations.models import Landmark

        q_norm = query.strip()
        landmark = (
            Landmark.objects.filter(
                Q(name__icontains=q_norm)
                | Q(aliases__icontains=q_norm)
                | Q(city__iexact=q_norm)
            )
            .order_by("-is_verified", "name")
            .first()
        )
        if landmark:
            return {
                "name": landmark.name,
                "city": landmark.city,
                "state": landmark.state,
                "category": landmark.category,
                "latitude": float(landmark.latitude),
                "longitude": float(landmark.longitude),
                "address": landmark.address or f"{landmark.name}, {landmark.city}",
            }
    except Exception as e:
        logger.debug("Database landmark lookup error: %s", e)
    return None


def geocode_location(query: str) -> Optional[Dict[str, Any]]:
    """
    Geocode a student search query into latitude, longitude, and formatted name.
    Checks:
      1. Django Cache (key: geocode:<normalized_query>)
      2. Curated & Database Landmarks
      3. OpenStreetMap Nominatim API (with rate throttling & User-Agent)
    """
    if not query or not query.strip():
        return None

    query_str = query.strip()
    import hashlib
    norm_hash = hashlib.md5(query_str.lower().encode("utf-8")).hexdigest()
    cache_key = f"geocode_{norm_hash}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # 1. First check curated high-speed landmarks
    curated = _search_curated_landmarks(query_str)
    if curated:
        res = {
            "name": curated["name"],
            "display_name": f"{curated['name']}, {curated['city']}, {curated['state']}",
            "city": curated["city"],
            "state": curated["state"],
            "category": curated.get("category", "landmark"),
            "latitude": float(curated["latitude"]),
            "longitude": float(curated["longitude"]),
            "source": "verified_landmark",
        }
        cache.set(cache_key, res, CACHE_TTL_SECONDS)
        return res

    # 2. Check Database landmarks
    db_match = _search_database_landmarks(query_str)
    if db_match:
        res = {
            "name": db_match["name"],
            "display_name": db_match["address"],
            "city": db_match["city"],
            "state": db_match["state"],
            "category": db_match.get("category", "landmark"),
            "latitude": float(db_match["latitude"]),
            "longitude": float(db_match["longitude"]),
            "source": "database_landmark",
        }
        cache.set(cache_key, res, CACHE_TTL_SECONDS)
        return res

    # 3. Call OpenStreetMap Nominatim API
    try:
        _throttle_request()
        params = {
            "q": query_str,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "in",
        }
        url = f"{NOMINATIM_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )

        with urllib.request.urlopen(req, timeout=4.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if data and len(data) > 0:
                    first = data[0]
                    address = first.get("address", {})
                    city = (
                        address.get("city")
                        or address.get("town")
                        or address.get("village")
                        or address.get("state_district")
                        or query_str
                    )
                    state = address.get("state", "India")
                    res = {
                        "name": first.get("display_name", "").split(",")[0],
                        "display_name": first.get("display_name", ""),
                        "city": city,
                        "state": state,
                        "category": first.get("type", "landmark"),
                        "latitude": float(first["lat"]),
                        "longitude": float(first["lon"]),
                        "source": "nominatim_osm",
                    }
                    cache.set(cache_key, res, CACHE_TTL_SECONDS)
                    return res
    except Exception as exc:
        logger.warning("Nominatim geocoding failed for '%s': %s", query_str, exc)

    # 4. Fallback: fuzzy matching or default city coordinates
    city_fallbacks = {
        "prayagraj": (25.4358, 81.8463, "Prayagraj", "Uttar Pradesh"),
        "allahabad": (25.4358, 81.8463, "Prayagraj", "Uttar Pradesh"),
        "kota": (25.1800, 75.8300, "Kota", "Rajasthan"),
        "delhi": (28.6139, 77.2090, "Delhi", "Delhi"),
        "patna": (25.5941, 85.1376, "Patna", "Bihar"),
        "jaipur": (26.9124, 75.7873, "Jaipur", "Rajasthan"),
        "lucknow": (26.8467, 80.9462, "Lucknow", "Uttar Pradesh"),
        "hyderabad": (17.3850, 78.4867, "Hyderabad", "Telangana"),
        "bengaluru": (12.9716, 77.5946, "Bengaluru", "Karnataka"),
        "bangalore": (12.9716, 77.5946, "Bengaluru", "Karnataka"),
        "pune": (18.5204, 73.8567, "Pune", "Maharashtra"),
    }
    q_lower = query_str.lower()
    for key, (lat, lng, cname, sname) in city_fallbacks.items():
        if key in q_lower:
            fallback_res = {
                "name": f"{query_str} ({cname})",
                "display_name": f"{query_str}, {cname}, {sname}",
                "city": cname,
                "state": sname,
                "category": "city",
                "latitude": lat,
                "longitude": lng,
                "source": "city_fallback",
            }
            cache.set(cache_key, fallback_res, CACHE_TTL_SECONDS)
            return fallback_res

    return None


def reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Reverse geocode latitude and longitude into address components using Nominatim."""
    cache_key = f"reverse_geo_{round(lat, 4)}_{round(lng, 4)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        _throttle_request()
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "addressdetails": 1,
            "zoom": 18,
        }
        url = f"{NOMINATIM_REVERSE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=4.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                addr = data.get("address", {})
                res = {
                    "display_name": data.get("display_name", ""),
                    "address": addr.get("road") or addr.get("suburb", ""),
                    "locality": addr.get("suburb") or addr.get("neighbourhood", ""),
                    "city": addr.get("city") or addr.get("town") or addr.get("state_district", ""),
                    "state": addr.get("state", "Uttar Pradesh"),
                    "pincode": addr.get("postcode", ""),
                }
                cache.set(cache_key, res, CACHE_TTL_SECONDS)
                return res
    except Exception as exc:
        logger.warning("Reverse geocode failed: %s", exc)

    return None


def get_landmark_suggestions(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Return autocomplete suggestions for instant search UI."""
    if not query or len(query.strip()) < 2:
        return []

    q_lower = query.lower().strip()
    suggestions = []
    seen = set()

    # 1. From curated landmarks
    for item in CURATED_LANDMARKS:
        name = item["name"]
        city = item["city"]
        label = f"{name}, {city}"
        if label in seen:
            continue
        if q_lower in name.lower() or q_lower in city.lower() or any(q_lower in a for a in item.get("aliases", [])):
            seen.add(label)
            suggestions.append({
                "name": name,
                "city": city,
                "category": item["category"],
                "display_name": label,
                "latitude": item["latitude"],
                "longitude": item["longitude"],
            })
            if len(suggestions) >= limit:
                return suggestions

    # 2. From database Landmark model
    try:
        from locations.models import Landmark

        db_items = Landmark.objects.filter(
            Q(name__icontains=query) | Q(aliases__icontains=query) | Q(city__icontains=query)
        )[:limit]
        for item in db_items:
            label = f"{item.name}, {item.city}"
            if label not in seen:
                seen.add(label)
                suggestions.append({
                    "name": item.name,
                    "city": item.city,
                    "category": item.category,
                    "display_name": label,
                    "latitude": float(item.latitude),
                    "longitude": float(item.longitude),
                })
                if len(suggestions) >= limit:
                    break
    except Exception as exc:
        logger.debug("Database landmark suggestions error: %s", exc)

    return suggestions
