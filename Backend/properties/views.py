"""Public listing browsing, favourites, room configurations, and owner property management."""

from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import owner_required, student_required
from accounts.models import OwnerProfile
from enquiries.forms import EnquiryForm
from enquiries.models import Enquiry

from .demo_data import FEATURED_PROPERTIES
from .forms import PropertyForm, PropertyImageForm, RoomForm
from .models import Favourite, Property, PropertyImage, PropertyReport, Room

STAY_TYPE_LABELS = {
    "pg": "PG Accommodation",
    "private_hostel": "Private Hostel",
    "student_hostel": "Student Hostel",
    "independent_room": "Independent Room",
    "shared_room": "Shared Rental Room",
    "coliving": "Co-living Space",
    # Backward compatibility
    "hostel": "Hostel",
    "room": "Private room",
}

GENDER_LABELS = {
    "boys": "Boys only",
    "girls": "Girls only",
    "unisex": "Unisex / All",
}


import json
from django.core.paginator import Paginator
from locations.services.distance import (
    format_distance,
    haversine_distance,
)
from locations.services.geocoding import geocode_location
from locations.services.overpass import get_nearby_places
from .models import AVAILABLE_FACILITIES, Favourite, Property, PropertyImage, Room


def _search_properties(request):
    query = request.GET.get("q", "").strip()
    city = request.GET.get("city", "").strip()
    destination = request.GET.get("destination", "").strip()
    lat_str = request.GET.get("lat", "").strip()
    lng_str = request.GET.get("lng", "").strip()
    radius_str = request.GET.get("radius", "5.0").strip()
    sort_by = request.GET.get("sort", "").strip()

    stay_type = request.GET.get("type", "").strip()
    gender = request.GET.get("gender", "").strip()
    min_rent_str = request.GET.get("min_rent", "").strip()
    max_rent_str = request.GET.get("max_rent", "").strip()
    sharing = request.GET.get("sharing", "").strip()
    ac = request.GET.get("ac", "").strip()
    food = request.GET.get("food", "").strip()
    wifi = request.GET.get("wifi", "").strip()
    bathroom = request.GET.get("bathroom", "").strip()
    furnished = request.GET.get("furnished", "").strip()
    move_in = request.GET.get("move_in", "").strip()
    available_only = request.GET.get("available_only") in ["1", "true", "True", "yes"]
    view_mode = request.GET.get("view", "split").strip()

    # Parse facility list (comma-separated or getlist)
    raw_facilities = request.GET.getlist("facilities")
    if not raw_facilities:
        facilities_param = request.GET.get("facilities", "")
        raw_facilities = [f.strip() for f in facilities_param.split(",") if f.strip()]
    selected_facilities = list(dict.fromkeys(raw_facilities))

    # Determine radius (constrained between 0.5 and 15 km)
    try:
        radius_km = float(radius_str) if radius_str else 5.0
    except ValueError:
        radius_km = 5.0
    radius_km = max(0.5, min(15.0, radius_km))

    # Resolve destination coordinates
    target_lat = None
    target_lng = None
    searched_location = None

    if lat_str and lng_str:
        try:
            target_lat = float(lat_str)
            target_lng = float(lng_str)
            searched_location = {
                "name": destination or query or city or f"{target_lat:.4f}, {target_lng:.4f}",
                "display_name": destination or query or city or f"Coordinates ({target_lat:.4f}, {target_lng:.4f})",
                "latitude": target_lat,
                "longitude": target_lng,
            }
        except ValueError:
            target_lat, target_lng = None, None

    if (target_lat is None or target_lng is None) and (destination or query or city):
        geo_target = destination or query or city
        geocoded = geocode_location(geo_target)
        if geocoded:
            target_lat = float(geocoded["latitude"])
            target_lng = float(geocoded["longitude"])
            searched_location = {
                "name": geocoded.get("name") or geo_target,
                "display_name": geocoded.get("display_name", geo_target),
                "latitude": target_lat,
                "longitude": target_lng,
                "city": geocoded.get("city", city),
            }

    # Default sort
    if not sort_by or sort_by not in ["nearest", "rent_asc", "rent_desc", "recent", "popular"]:
        sort_by = "nearest" if target_lat is not None else "recent"

    # Base query for public, verified properties
    qs = (
        Property.objects.filter(is_active=True, is_approved=True)
        .annotate(
            popularity_score=Count("favourited_by", distinct=True) + Count("enquiries", distinct=True)
        )
        .select_related("owner")
        .prefetch_related("rooms", "images")
    )

    # 1. Text Search (if no geocoded destination or searching within results)
    if query and target_lat is None:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(city__icontains=query)
            | Q(locality__icontains=query)
            | Q(address__icontains=query)
            | Q(landmark__icontains=query)
            | Q(description__icontains=query)
            | Q(facilities__icontains=query)
        )

    # 2. City filter (if specified and not geocoded to a specific institute/landmark)
    if city and (target_lat is None or not query):
        qs = qs.filter(city__icontains=city)

    # 3. Category / Stay Type
    if stay_type in STAY_TYPE_LABELS:
        if stay_type == "hostel":
            qs = qs.filter(
                Q(property_type="hostel")
                | Q(property_type="student_hostel")
                | Q(property_type="private_hostel")
            )
        elif stay_type == "room":
            qs = qs.filter(
                Q(property_type="room")
                | Q(property_type="independent_room")
                | Q(property_type="shared_room")
            )
        else:
            qs = qs.filter(property_type=stay_type)
    else:
        stay_type = ""

    # 4. Gender
    if gender in GENDER_LABELS:
        qs = qs.filter(gender_preference=gender)
    else:
        gender = ""

    # 5. Budget Filters
    min_rent = None
    max_rent = None
    if min_rent_str and min_rent_str.isdigit():
        min_rent = int(min_rent_str)
        qs = qs.filter(
            Q(monthly_rent__gte=min_rent)
            | Q(rooms__monthly_rent__gte=min_rent, rooms__is_available=True)
        ).distinct()

    if max_rent_str and max_rent_str.isdigit():
        max_rent = int(max_rent_str)
        qs = qs.filter(
            Q(monthly_rent__lte=max_rent)
            | Q(rooms__monthly_rent__lte=max_rent, rooms__is_available=True)
        ).distinct()

    # 6. Room Occupancy / Sharing
    if sharing in ["single", "double", "triple", "four"]:
        qs = qs.filter(rooms__occupancy=sharing, rooms__is_available=True).distinct()
    else:
        sharing = ""

    # 7. Air Conditioning
    if ac in ["ac", "non_ac"]:
        qs = qs.filter(rooms__air_conditioning=ac, rooms__is_available=True).distinct()
    else:
        ac = ""

    # 8. Available rooms only
    if available_only:
        qs = qs.filter(rooms__available_beds__gt=0, rooms__is_available=True).distinct()

    # 9. Food Availability
    if food in ["1", "true", "True", "yes"] or "Food/Mess" in selected_facilities:
        qs = qs.filter(
            Q(facilities__icontains="Food")
            | Q(facilities__icontains="Mess")
            | Q(facilities__icontains="Meals")
        )

    # 10. Wi-Fi
    if wifi in ["1", "true", "True", "yes"] or "Wi-Fi" in selected_facilities:
        qs = qs.filter(facilities__icontains="Wi-Fi")

    # 11. Attached Bathroom
    if bathroom in ["attached", "1", "true", "True"] or "Attached Bathroom" in selected_facilities:
        qs = qs.filter(
            Q(rooms__bathroom_type="attached", rooms__is_available=True)
            | Q(facilities__icontains="Attached Bathroom")
        ).distinct()

    # 12. Furnished / Unfurnished
    if furnished:
        if furnished.lower() in ["furnished", "full", "fully"]:
            qs = qs.filter(
                Q(facilities__icontains="Furnished")
                | (Q(facilities__icontains="Study Table") & Q(facilities__icontains="Wardrobe"))
            ).distinct()
        elif furnished.lower() == "unfurnished":
            qs = qs.exclude(facilities__icontains="Furnished").exclude(
                Q(facilities__icontains="Study Table") & Q(facilities__icontains="Wardrobe")
            )

    # 13. Facilities (must match all selected)
    for facility in selected_facilities:
        qs = qs.filter(facilities__icontains=facility)

    # 14. Move-in date
    if move_in:
        try:
            move_in_date = date.fromisoformat(move_in)
            qs = qs.filter(
                Q(available_from__lte=move_in_date) | Q(available_from__isnull=True)
            )
        except ValueError:
            move_in = ""

    # Evaluate properties and calculate Haversine distances
    results = []
    for prop in qs:
        dist_km = None
        if target_lat is not None and target_lng is not None and prop.latitude and prop.longitude:
            dist_km = haversine_distance(
                target_lat,
                target_lng,
                float(prop.latitude),
                float(prop.longitude),
            )
            # Filter by radius
            if dist_km > radius_km:
                continue

            prop.distance_km = dist_km
            prop.distance_text = format_distance(dist_km)
        else:
            prop.distance_km = 9999.0
            prop.distance_text = prop.landmark or prop.locality or prop.city

        results.append(prop)

    # Sorting
    if sort_by == "rent_asc":
        results.sort(key=lambda p: (p.min_monthly_rent, p.distance_km))
    elif sort_by == "rent_desc":
        results.sort(key=lambda p: (-p.min_monthly_rent, p.distance_km))
    elif sort_by == "recent":
        results.sort(key=lambda p: -p.created_at.timestamp())
    elif sort_by == "popular":
        results.sort(key=lambda p: (-getattr(p, "popularity_score", 0), p.distance_km, -p.created_at.timestamp()))
    else:  # 'nearest'
        results.sort(key=lambda p: (p.distance_km, p.min_monthly_rent))

    # Retrieve nearby POIs around the searched destination
    nearby_pois = []
    if target_lat is not None and target_lng is not None:
        poi_data = get_nearby_places(
            target_lat,
            target_lng,
            radius_meters=int(radius_km * 1000),
        )
        nearby_pois = poi_data.get("all", [])

    # Map markers serialized data
    map_markers = []
    for p in results:
        if p.latitude and p.longitude:
            map_markers.append({
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "latitude": float(p.latitude),
                "longitude": float(p.longitude),
                "monthly_rent": p.min_monthly_rent,
                "distance_text": getattr(p, "distance_text", ""),
                "property_type_display": p.get_property_type_display(),
                "gender_preference": p.gender_preference,
                "image_url": p.primary_image_url or "/static/images/rooms/room_single_cozy.jpg",
                "url": p.get_absolute_url(),
            })

    active_filters_count = sum([
        bool(city),
        bool(stay_type),
        bool(gender),
        bool(min_rent_str),
        bool(max_rent_str),
        bool(sharing),
        bool(ac),
        bool(food),
        bool(wifi),
        bool(bathroom),
        bool(furnished),
        bool(available_only),
        len(selected_facilities) > 0,
    ])

    search_context = {
        "query": query,
        "destination": destination,
        "searched_location": searched_location,
        "target_lat": target_lat,
        "target_lng": target_lng,
        "city": city,
        "radius_km": radius_km,
        "sort_by": sort_by,
        "stay_type": stay_type,
        "stay_type_label": STAY_TYPE_LABELS.get(stay_type, ""),
        "gender": gender,
        "gender_label": GENDER_LABELS.get(gender, ""),
        "min_rent": min_rent_str,
        "max_rent": max_rent_str,
        "sharing": sharing,
        "ac": ac,
        "food": food,
        "wifi": wifi,
        "bathroom": bathroom,
        "furnished": furnished,
        "move_in": move_in,
        "available_only": available_only,
        "selected_facilities": selected_facilities,
        "available_facilities": [f for f, _ in AVAILABLE_FACILITIES],
        "view_mode": view_mode,
        "active_filters_count": active_filters_count,
        "nearby_pois": nearby_pois,
        "map_markers_json": json.dumps(map_markers),
        "searched_location_json": json.dumps(searched_location) if searched_location else "null",
        "nearby_pois_json": json.dumps(nearby_pois[:20]),
    }

    return results, search_context


def property_list(request):
    """Browse live listings with smart location search, Leaflet map, and pagination."""
    matched_properties, search_context = _search_properties(request)

    student_favourite_ids = set()
    if request.user.is_authenticated and request.user.is_student:
        student_favourite_ids = set(
            Favourite.objects.filter(student=request.user).values_list(
                "property_id", flat=True
            )
        )

    from locations.demo_data import POPULAR_CITY_SHORTCUTS

    live_cities = list(
        Property.objects.filter(is_active=True, is_approved=True)
        .values_list("city", flat=True)
        .distinct()
    )
    all_cities = sorted(set(live_cities + POPULAR_CITY_SHORTCUTS))

    # Pagination: 9 properties per page
    paginator = Paginator(matched_properties, 9)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Clean query string for pagination links (excluding page parameter)
    get_params = request.GET.copy()
    if "page" in get_params:
        del get_params["page"]
    pagination_query = get_params.urlencode()

    has_live_properties = len(matched_properties) > 0 or Property.objects.filter(is_active=True, is_approved=True).exists()

    return render(
        request,
        "properties/property_list.html",
        {
            **search_context,
            "properties": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "total_properties_count": len(matched_properties),
            "pagination_query": pagination_query,
            "has_live_properties": has_live_properties,
            "student_favourite_ids": student_favourite_ids,
            "available_cities": all_cities,
            "sample_properties": FEATURED_PROPERTIES,
        },
    )


def api_property_search(request):
    """
    JSON API endpoint for AJAX dynamic search and filter updates.
    Returns properties, pagination, map markers, and destination details.
    """
    matched_properties, search_context = _search_properties(request)

    student_favourite_ids = set()
    if request.user.is_authenticated and request.user.is_student:
        student_favourite_ids = set(
            Favourite.objects.filter(student=request.user).values_list(
                "property_id", flat=True
            )
        )

    try:
        page_num = int(request.GET.get("page", 1))
    except (ValueError, TypeError):
        page_num = 1

    try:
        page_size = int(request.GET.get("page_size", 9))
    except (ValueError, TypeError):
        page_size = 9

    page_size = max(1, min(50, page_size))
    paginator = Paginator(matched_properties, page_size)
    page_obj = paginator.get_page(page_num)

    serialized_properties = []
    for p in page_obj.object_list:
        serialized_properties.append({
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
            "landmark": p.landmark,
            "latitude": float(p.latitude) if p.latitude else None,
            "longitude": float(p.longitude) if p.longitude else None,
            "monthly_rent": p.min_monthly_rent,
            "deposit": p.deposit,
            "distance_km": getattr(p, "distance_km", None),
            "distance_text": getattr(p, "distance_text", ""),
            "primary_image_url": p.primary_image_url or "/static/images/rooms/room_single_cozy.jpg",
            "facilities": p.facilities_list[:6],
            "total_available_beds": p.total_available_beds,
            "occupancies": p.room_occupancy_labels,
            "is_favourite": p.id in student_favourite_ids,
        })

    return JsonResponse({
        "status": "ok",
        "total_count": len(matched_properties),
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
        "previous_page_number": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "properties": serialized_properties,
        "map_markers": json.loads(search_context["map_markers_json"]),
        "searched_location": json.loads(search_context["searched_location_json"]) if search_context["searched_location_json"] != "null" else None,
        "active_filters_count": search_context["active_filters_count"],
    })


def explore_pgs(request):
    """
    Dedicated Explore PGs discovery page pre-filtering for PG accommodation.
    Supports live AJAX dynamic search, Leaflet interactive map, and URL state sync.
    """
    get_params = request.GET.copy()
    if not get_params.get("type"):
        get_params["type"] = "pg"
    request.GET = get_params

    matched_properties, search_context = _search_properties(request)

    student_favourite_ids = set()
    if request.user.is_authenticated and request.user.is_student:
        student_favourite_ids = set(
            Favourite.objects.filter(student=request.user).values_list(
                "property_id", flat=True
            )
        )

    from locations.demo_data import POPULAR_CITY_SHORTCUTS

    live_cities = list(
        Property.objects.filter(is_active=True, is_approved=True)
        .values_list("city", flat=True)
        .distinct()
    )
    all_cities = sorted(set(live_cities + POPULAR_CITY_SHORTCUTS))

    paginator = Paginator(matched_properties, 9)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    get_params_clean = request.GET.copy()
    if "page" in get_params_clean:
        del get_params_clean["page"]
    pagination_query = get_params_clean.urlencode()

    has_live_properties = len(matched_properties) > 0 or Property.objects.filter(is_active=True, is_approved=True).exists()

    return render(
        request,
        "properties/explore_pgs.html",
        {
            **search_context,
            "properties": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "total_properties_count": len(matched_properties),
            "pagination_query": pagination_query,
            "has_live_properties": has_live_properties,
            "student_favourite_ids": student_favourite_ids,
            "available_cities": all_cities,
            "sample_properties": [p for p in FEATURED_PROPERTIES if "pg" in p.get("type", "").lower()],
        },
    )


def property_detail(request, slug):
    """Show a live property when available, otherwise a sample preview, with nearby places."""
    property_obj = (
        Property.objects.select_related("owner")
        .prefetch_related("rooms", "images")
        .filter(slug=slug)
        .first()
    )

    if property_obj is not None:
        user = request.user
        is_owner = user.is_authenticated and property_obj.owner_id == user.id
        is_admin = user.is_authenticated and user.is_platform_admin
        if not property_obj.is_publicly_visible and not (is_owner or is_admin):
            raise Http404("Property not found.")

        owner_profile = None
        try:
            owner_profile = property_obj.owner.owner_profile
        except OwnerProfile.DoesNotExist:
            pass

        is_favourite = False
        enquiry_form = None
        active_enquiry = None
        if request.user.is_authenticated and request.user.is_student:
            is_favourite = Favourite.objects.filter(
                student=request.user,
                property=property_obj,
            ).exists()
            active_enquiry = Enquiry.objects.filter(
                student=request.user,
                property=property_obj,
                status__in=[
                    Enquiry.Status.PENDING,
                    Enquiry.Status.CONTACTED,
                    Enquiry.Status.ACCEPTED,
                ],
            ).first()
            enquiry_form = EnquiryForm(
                initial={"contact_number": request.user.mobile_number},
                student=request.user,
                property_obj=property_obj,
            )

        gallery_images = property_obj.images.all()
        rooms = property_obj.rooms.all()

        # Discover nearby points of interest via Overpass
        nearby_places_data = {"all": [], "by_category": {}, "count": 0}
        if property_obj.latitude and property_obj.longitude:
            nearby_places_data = get_nearby_places(
                float(property_obj.latitude),
                float(property_obj.longitude),
                radius_meters=3000,
            )

        return render(
            request,
            "properties/property_live_detail.html",
            {
                "property": property_obj,
                "owner_profile": owner_profile,
                "is_favourite": is_favourite,
                "active_enquiry": active_enquiry,
                "enquiry_form": enquiry_form,
                "gallery_images": gallery_images,
                "rooms": rooms,
                "nearby_places": nearby_places_data,
                "nearby_pois_json": json.dumps(nearby_places_data.get("all", [])[:20]),
            },
        )

    property_data = next(
        (item for item in FEATURED_PROPERTIES if item["slug"] == slug),
        None,
    )
    if property_data is None:
        raise Http404("Sample property not found.")

    related_properties = [
        item for item in FEATURED_PROPERTIES if item["slug"] != slug
    ][:3]

    # Sample property nearby places
    nearby_places_data = {"all": [], "by_category": {}, "count": 0}
    if property_data.get("latitude") and property_data.get("longitude"):
        nearby_places_data = get_nearby_places(
            property_data["latitude"],
            property_data["longitude"],
            radius_meters=3000,
        )

    return render(
        request,
        "properties/property_detail.html",
        {
            "property": property_data,
            "related_properties": related_properties,
            "nearby_places": nearby_places_data,
            "nearby_pois_json": json.dumps(nearby_places_data.get("all", [])[:20]),
        },
    )


# =====================================================================
# OWNER PROPERTY MANAGEMENT
# =====================================================================

@owner_required
def owner_property_list(request):
    """Overview of owner's listed properties with room and bed counts."""
    properties = (
        Property.objects.filter(owner=request.user)
        .select_related("owner")
        .prefetch_related("rooms", "images")
    )
    return render(
        request,
        "properties/owner_property_list.html",
        {"properties": properties},
    )


@owner_required
def property_create(request):
    """Add a new property and redirect to room setup."""
    profile = OwnerProfile.objects.filter(user=request.user).first()
    initial = {
        "contact_number": (
            profile.contact_number
            if profile and profile.contact_number
            else request.user.mobile_number
        ),
        "city": profile.city if profile else "",
    }
    form = PropertyForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        property_obj = form.save(commit=False)
        property_obj.owner = request.user
        # Platform admins get instant approval; owner submissions can be configured
        property_obj.is_approved = True
        property_obj.save()
        messages.success(
            request,
            f"'{property_obj.name}' has been created! You can now manage room configurations and photos.",
        )
        return redirect("properties:owner_list")

    return render(
        request,
        "properties/property_form.html",
        {
            "form": form,
            "page_title": "Add a new property",
            "page_copy": "Fill in property details, location, facilities and cover photo.",
            "submit_label": "Continue to room configurations",
        },
    )


@owner_required
def property_edit(request, slug):
    """Edit an existing property's details."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage your own properties.")

    form = PropertyForm(request.POST or None, request.FILES or None, instance=property_obj)
    if request.method == "POST" and form.is_valid():
        property_obj = form.save()
        messages.success(request, f"'{property_obj.name}' details have been updated.")
        return redirect("properties:owner_list")

    return render(
        request,
        "properties/property_form.html",
        {
            "form": form,
            "property": property_obj,
            "page_title": "Edit property",
            "page_copy": "Update basic details, address, rent, facilities or cover image.",
            "submit_label": "Save property changes",
        },
    )


@owner_required
@require_POST
def property_delete(request, slug):
    """Delete an owned property listing."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only delete your own properties.")

    name = property_obj.name
    property_obj.delete()
    messages.success(request, f"'{name}' has been deleted.")
    return redirect("properties:owner_list")


@owner_required
@require_POST
def property_toggle_active(request, slug):
    """Quickly toggle a property between Active and Inactive."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage your own properties.")

    property_obj.is_active = not property_obj.is_active
    property_obj.save()
    status_str = "activated (live)" if property_obj.is_active else "deactivated (hidden)"
    messages.success(request, f"'{property_obj.name}' is now {status_str}.")
    return redirect("properties:owner_list")


# =====================================================================
# ROOM CONFIGURATION MANAGEMENT
# =====================================================================

@owner_required
def room_list(request, slug):
    """Manage multiple room configurations for a property."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage rooms for your own properties.")

    rooms = property_obj.rooms.all()
    form = RoomForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        room = form.save(commit=False)
        room.property = property_obj
        room.save()
        messages.success(request, f"Room configuration '{room.room_type}' added successfully.")
        return redirect("properties:room_list", slug=property_obj.slug)

    return render(
        request,
        "properties/room_list.html",
        {
            "property": property_obj,
            "rooms": rooms,
            "form": form,
        },
    )


@owner_required
def room_edit(request, slug, room_pk):
    """Edit a single room configuration."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage rooms for your own properties.")

    room = get_object_or_404(Room, pk=room_pk, property=property_obj)
    form = RoomForm(request.POST or None, instance=room)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Room '{room.room_type}' updated successfully.")
        return redirect("properties:room_list", slug=property_obj.slug)

    return render(
        request,
        "properties/room_form.html",
        {
            "property": property_obj,
            "room": room,
            "form": form,
        },
    )


@owner_required
@require_POST
def room_delete(request, slug, room_pk):
    """Delete a room configuration."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage rooms for your own properties.")

    room = get_object_or_404(Room, pk=room_pk, property=property_obj)
    room_name = room.room_type
    room.delete()
    messages.success(request, f"Room configuration '{room_name}' has been deleted.")
    return redirect("properties:room_list", slug=property_obj.slug)


@owner_required
@require_POST
def room_update_beds(request, slug, room_pk):
    """Quick update available beds and monthly rent from the room overview table."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage rooms for your own properties.")

    room = get_object_or_404(Room, pk=room_pk, property=property_obj)
    available_beds = request.POST.get("available_beds")
    monthly_rent = request.POST.get("monthly_rent")

    if available_beds and available_beds.isdigit():
        avail = int(available_beds)
        if avail <= room.total_beds:
            room.available_beds = avail
        else:
            messages.error(request, "Available beds cannot exceed total beds.")
            return redirect("properties:room_list", slug=property_obj.slug)

    if monthly_rent and monthly_rent.isdigit():
        room.monthly_rent = int(monthly_rent)

    room.save()
    messages.success(request, f"Availability & rent for '{room.room_type}' updated.")
    return redirect("properties:room_list", slug=property_obj.slug)


# =====================================================================
# PROPERTY IMAGE GALLERY MANAGEMENT
# =====================================================================

@owner_required
def gallery_manage(request, slug):
    """View and upload photos categorized by Exterior, Bedroom, Bathroom, Kitchen, etc."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage photos for your own properties.")

    images = property_obj.images.all()
    form = PropertyImageForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        img = form.save(commit=False)
        img.property = property_obj
        img.save()
        messages.success(request, f"Photo uploaded under '{img.get_category_display()}'.")
        return redirect("properties:gallery_manage", slug=property_obj.slug)

    return render(
        request,
        "properties/gallery_manage.html",
        {
            "property": property_obj,
            "images": images,
            "form": form,
        },
    )


@owner_required
@require_POST
def gallery_delete(request, slug, image_pk):
    """Delete an uploaded gallery photo."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage photos for your own properties.")

    image_obj = get_object_or_404(PropertyImage, pk=image_pk, property=property_obj)
    image_obj.delete()
    messages.success(request, "Photo removed from gallery.")
    return redirect("properties:gallery_manage", slug=property_obj.slug)


@owner_required
@require_POST
def gallery_set_primary(request, slug, image_pk):
    """Mark a photo as the primary cover image."""
    property_obj = get_object_or_404(Property, slug=slug)
    if property_obj.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage photos for your own properties.")

    image_obj = get_object_or_404(PropertyImage, pk=image_pk, property=property_obj)
    PropertyImage.objects.filter(property=property_obj).update(is_primary=False)
    image_obj.is_primary = True
    image_obj.save()
    messages.success(request, "Photo set as primary cover photo.")
    return redirect("properties:gallery_manage", slug=property_obj.slug)


# =====================================================================
# STUDENT FAVOURITES
# =====================================================================

@student_required
@require_POST
def toggle_favourite(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)
    favourite, created = Favourite.objects.get_or_create(
        student=request.user,
        property=property_obj,
    )
    if not created:
        favourite.delete()
        messages.info(request, f"Removed {property_obj.name} from your saved stays.")
    else:
        messages.success(request, f"Saved {property_obj.name} to your shortlist.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect(property_obj.get_absolute_url())


# =====================================================================
# REPORT MISLEADING OR FRAUDULENT LISTING
# =====================================================================

@require_POST
def property_report_submit(request, slug):
    """Allow students and users to report suspicious or misleading listings."""
    property_obj = get_object_or_404(Property, slug=slug)
    reason = request.POST.get("reason", PropertyReport.Reason.OTHER).strip()
    details = request.POST.get("details", "").strip()
    reporter_name = request.POST.get("reporter_name", "").strip()
    reporter_email = request.POST.get("reporter_email", "").strip()
    reporter_phone = request.POST.get("reporter_phone", "").strip()

    if not details:
        messages.error(
            request, "Please provide details explaining why you are reporting this listing."
        )
        return redirect(property_obj.get_absolute_url())

    reported_by = request.user if request.user.is_authenticated else None
    if reported_by:
        reporter_name = reporter_name or reported_by.get_full_name()
        reporter_email = reporter_email or reported_by.email
        reporter_phone = reporter_phone or getattr(reported_by, "mobile_number", "")

    PropertyReport.objects.create(
        property=property_obj,
        reported_by=reported_by,
        reporter_name=reporter_name,
        reporter_email=reporter_email,
        reporter_phone=reporter_phone,
        reason=reason,
        details=details,
        status=PropertyReport.Status.PENDING,
    )
    messages.success(
        request,
        "Thank you. Your report has been submitted to platform administrators for review.",
    )
    return redirect(property_obj.get_absolute_url())

