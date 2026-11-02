"""Custom administration, listing moderation, user management, and location management views."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.decorators import admin_required
from accounts.models import OwnerProfile
from enquiries.models import Enquiry
from locations.models import City, Landmark, Locality, State
from properties.models import Property, PropertyImage, PropertyReport, Room

User = get_user_model()


# =====================================================================
# 1. ADMIN DASHBOARD & PLATFORM OVERVIEW
# =====================================================================

@admin_required
def admin_dashboard(request):
    """Main administrative dashboard displaying key metrics, city distribution, and moderation queues."""
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_owners = User.objects.filter(role=User.Role.OWNER).count()
    total_properties = Property.objects.count()
    pending_properties = Property.objects.filter(approval_status=Property.ApprovalStatus.PENDING).count()
    approved_properties = Property.objects.filter(approval_status=Property.ApprovalStatus.APPROVED).count()
    rejected_properties = Property.objects.filter(approval_status=Property.ApprovalStatus.REJECTED).count()
    suspended_properties = Property.objects.filter(approval_status=Property.ApprovalStatus.SUSPENDED).count()
    total_enquiries = Enquiry.objects.count()
    pending_reports_count = PropertyReport.objects.filter(status=PropertyReport.Status.PENDING).count()

    # City-wise property distribution
    city_stats_qs = Property.objects.values("city").annotate(
        total=Count("id"),
        approved=Count("id", filter=Q(approval_status=Property.ApprovalStatus.APPROVED)),
        pending=Count("id", filter=Q(approval_status=Property.ApprovalStatus.PENDING)),
        rejected=Count("id", filter=Q(approval_status=Property.ApprovalStatus.REJECTED)),
        suspended=Count("id", filter=Q(approval_status=Property.ApprovalStatus.SUSPENDED)),
    ).order_by("-total")

    city_stats = []
    for item in city_stats_qs:
        percentage = round((item["total"] / total_properties * 100), 1) if total_properties > 0 else 0
        city_stats.append({
            "city": item["city"],
            "total": item["total"],
            "approved": item["approved"],
            "pending": item["pending"],
            "rejected": item["rejected"],
            "suspended": item["suspended"],
            "percentage": percentage,
        })

    # Recent queues
    pending_submissions = Property.objects.filter(
        approval_status=Property.ApprovalStatus.PENDING
    ).select_related("owner").order_by("-created_at")[:5]

    recent_reports = PropertyReport.objects.filter(
        status=PropertyReport.Status.PENDING
    ).select_related("property", "reported_by").order_by("-created_at")[:5]

    recent_users = User.objects.exclude(role=User.Role.ADMIN).order_by("-date_joined")[:6]

    context = {
        "total_students": total_students,
        "total_owners": total_owners,
        "total_properties": total_properties,
        "pending_properties": pending_properties,
        "approved_properties": approved_properties,
        "rejected_properties": rejected_properties,
        "suspended_properties": suspended_properties,
        "total_enquiries": total_enquiries,
        "pending_reports_count": pending_reports_count,
        "city_stats": city_stats,
        "pending_submissions": pending_submissions,
        "recent_reports": recent_reports,
        "recent_users": recent_users,
        "active_tab": "dashboard",
    }
    return render(request, "accounts/dashboard_admin.html", context)


# =====================================================================
# 2. PROPERTY MODERATION & REVIEW
# =====================================================================

@admin_required
def admin_property_list(request):
    """List properties with approval status filtering, search and moderation action links."""
    status_filter = request.GET.get("status", "all").strip().lower()
    search_query = request.GET.get("q", "").strip()

    queryset = Property.objects.select_related("owner").prefetch_related("rooms", "images", "reports").order_by("-created_at")

    if status_filter in {"pending", "approved", "rejected", "suspended"}:
        queryset = queryset.filter(approval_status=status_filter)

    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(city__icontains=search_query)
            | Q(locality__icontains=search_query)
            | Q(owner__full_name__icontains=search_query)
            | Q(owner__email__icontains=search_query)
        )

    # Status counts for filter chips
    status_counts = {
        "all": Property.objects.count(),
        "pending": Property.objects.filter(approval_status=Property.ApprovalStatus.PENDING).count(),
        "approved": Property.objects.filter(approval_status=Property.ApprovalStatus.APPROVED).count(),
        "rejected": Property.objects.filter(approval_status=Property.ApprovalStatus.REJECTED).count(),
        "suspended": Property.objects.filter(approval_status=Property.ApprovalStatus.SUSPENDED).count(),
    }

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "properties": page_obj,
        "status_filter": status_filter,
        "search_query": search_query,
        "status_counts": status_counts,
        "active_tab": "properties",
    }
    return render(request, "accounts/admin/property_moderation_list.html", context)


@admin_required
def admin_property_moderate(request, pk):
    """Detailed inspection screen for a single property listing: inspect images, owner info, rooms, and take moderation action."""
    property_obj = get_object_or_404(
        Property.objects.select_related("owner").prefetch_related("rooms", "images", "reports"),
        pk=pk,
    )
    owner = property_obj.owner
    owner_profile = getattr(owner, "owner_profile", None)
    owner_other_properties = Property.objects.filter(owner=owner).exclude(pk=property_obj.pk)

    gallery_images = property_obj.images.all()
    rooms = property_obj.rooms.all()
    reports = property_obj.reports.all().order_by("-created_at")

    context = {
        "property": property_obj,
        "owner": owner,
        "owner_profile": owner_profile,
        "owner_other_properties": owner_other_properties,
        "gallery_images": gallery_images,
        "rooms": rooms,
        "reports": reports,
        "active_tab": "properties",
    }
    return render(request, "accounts/admin/property_moderate_detail.html", context)


@admin_required
@require_POST
def admin_property_approve(request, pk):
    """Approve a property listing, clearing any previous rejection reason."""
    property_obj = get_object_or_404(Property, pk=pk)
    property_obj.approval_status = Property.ApprovalStatus.APPROVED
    property_obj.is_approved = True
    property_obj.is_suspended = False
    property_obj.rejection_reason = ""
    property_obj.save()

    messages.success(request, f"Property '{property_obj.name}' has been approved and is now publicly visible.")
    return redirect("accounts:admin_property_moderate", pk=pk)


@admin_required
@require_POST
def admin_property_reject(request, pk):
    """Reject a property listing with an explanation reason."""
    property_obj = get_object_or_404(Property, pk=pk)
    reason = request.POST.get("rejection_reason", "").strip()

    if not reason:
        reason = "Listing does not meet platform quality or verification guidelines."

    property_obj.approval_status = Property.ApprovalStatus.REJECTED
    property_obj.is_approved = False
    property_obj.rejection_reason = reason
    property_obj.save()

    messages.warning(request, f"Property '{property_obj.name}' was rejected. Reason recorded: {reason}")
    return redirect("accounts:admin_property_moderate", pk=pk)


@admin_required
@require_POST
def admin_property_suspend(request, pk):
    """Suspend a suspicious property listing immediately."""
    property_obj = get_object_or_404(Property, pk=pk)
    notes = request.POST.get("moderation_notes", "").strip() or "Suspended by administrator due to suspicious activity."

    property_obj.approval_status = Property.ApprovalStatus.SUSPENDED
    property_obj.is_approved = False
    property_obj.is_suspended = True
    property_obj.is_active = False
    property_obj.moderation_notes = notes
    property_obj.save()

    messages.error(request, f"Property '{property_obj.name}' has been suspended from public discovery.")
    return redirect("accounts:admin_property_moderate", pk=pk)


@admin_required
@require_POST
def admin_property_delete(request, pk):
    """Permanently remove a misleading or fraudulent listing."""
    property_obj = get_object_or_404(Property, pk=pk)
    property_name = property_obj.name
    property_obj.delete()

    messages.info(request, f"Property '{property_name}' was removed from the database.")
    return redirect("accounts:admin_property_list")


# =====================================================================
# 3. USER MANAGEMENT & ACTIVITY
# =====================================================================

@admin_required
def admin_user_list(request):
    """List registered students, property owners, and admins with search and activation controls."""
    role_filter = request.GET.get("role", "all").strip().lower()
    status_filter = request.GET.get("status", "all").strip().lower()
    search_query = request.GET.get("q", "").strip()

    queryset = User.objects.annotate(
        properties_count=Count("properties", distinct=True),
        enquiries_count=Count("enquiries", distinct=True),
    ).order_by("-date_joined")

    if role_filter in {"student", "owner", "admin"}:
        queryset = queryset.filter(role=role_filter)

    if status_filter == "active":
        queryset = queryset.filter(is_active=True)
    elif status_filter == "inactive":
        queryset = queryset.filter(is_active=False)

    if search_query:
        queryset = queryset.filter(
            Q(full_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(mobile_number__icontains=search_query)
        )

    # Role counts
    role_counts = {
        "all": User.objects.count(),
        "student": User.objects.filter(role=User.Role.STUDENT).count(),
        "owner": User.objects.filter(role=User.Role.OWNER).count(),
        "admin": User.objects.filter(role=User.Role.ADMIN).count(),
    }

    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "users": page_obj,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "search_query": search_query,
        "role_counts": role_counts,
        "active_tab": "users",
    }
    return render(request, "accounts/admin/user_management.html", context)


@admin_required
@require_POST
def admin_user_toggle_status(request, pk):
    """Activate or deactivate a user account with protection against self-deactivation."""
    target_user = get_object_or_404(User, pk=pk)

    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own administrator account.")
        return redirect("accounts:admin_user_list")

    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "activated" if target_user.is_active else "deactivated"
    messages.success(request, f"User '{target_user.get_full_name() or target_user.username}' has been {status_str}.")
    return redirect(request.META.get("HTTP_REFERER") or "accounts:admin_user_list")


@admin_required
def admin_user_activity(request, pk):
    """Inspect complete activity history for a specific student or property owner."""
    target_user = get_object_or_404(User, pk=pk)
    owner_profile = getattr(target_user, "owner_profile", None)

    properties = Property.objects.filter(owner=target_user).prefetch_related("rooms") if target_user.is_owner else []
    enquiries_submitted = Enquiry.objects.filter(student=target_user).select_related("property") if target_user.is_student else []
    enquiries_received = Enquiry.objects.filter(property__owner=target_user).select_related("property", "student") if target_user.is_owner else []
    favourites = target_user.favourites.select_related("property") if target_user.is_student else []
    reports_filed = PropertyReport.objects.filter(reported_by=target_user).select_related("property")

    context = {
        "target_user": target_user,
        "owner_profile": owner_profile,
        "properties": properties,
        "enquiries_submitted": enquiries_submitted,
        "enquiries_received": enquiries_received,
        "favourites": favourites,
        "reports_filed": reports_filed,
        "active_tab": "users",
    }
    return render(request, "accounts/admin/user_activity.html", context)


# =====================================================================
# 4. REPORTED LISTINGS MANAGEMENT
# =====================================================================

@admin_required
def admin_reports_list(request):
    """List and manage user reports filed against suspicious or misleading properties."""
    status_filter = request.GET.get("status", "all").strip().lower()
    reports_qs = PropertyReport.objects.select_related("property", "reported_by", "reviewed_by").order_by("-created_at")

    if status_filter in {"pending", "reviewed", "resolved", "dismissed"}:
        reports_qs = reports_qs.filter(status=status_filter)

    report_counts = {
        "all": PropertyReport.objects.count(),
        "pending": PropertyReport.objects.filter(status=PropertyReport.Status.PENDING).count(),
        "reviewed": PropertyReport.objects.filter(status=PropertyReport.Status.REVIEWED).count(),
        "resolved": PropertyReport.objects.filter(status=PropertyReport.Status.RESOLVED).count(),
        "dismissed": PropertyReport.objects.filter(status=PropertyReport.Status.DISMISSED).count(),
    }

    paginator = Paginator(reports_qs, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "reports": page_obj,
        "status_filter": status_filter,
        "report_counts": report_counts,
        "active_tab": "reports",
    }
    return render(request, "accounts/admin/reports_list.html", context)


@admin_required
@require_POST
def admin_report_action(request, pk):
    """Update report status, record action taken, or optionally suspend the reported property."""
    report = get_object_or_404(PropertyReport, pk=pk)
    action = request.POST.get("action", "").strip().lower()
    notes = request.POST.get("action_taken", "").strip()

    report.action_taken = notes
    report.reviewed_by = request.user

    if action == "resolve":
        report.status = PropertyReport.Status.RESOLVED
        messages.success(request, f"Report #{report.pk} marked as resolved.")
    elif action == "dismiss":
        report.status = PropertyReport.Status.DISMISSED
        messages.info(request, f"Report #{report.pk} dismissed.")
    elif action == "suspend_property":
        report.status = PropertyReport.Status.RESOLVED
        property_obj = report.property
        property_obj.approval_status = Property.ApprovalStatus.SUSPENDED
        property_obj.is_approved = False
        property_obj.is_suspended = True
        property_obj.is_active = False
        property_obj.moderation_notes = f"Suspended following Report #{report.pk}: {report.get_reason_display()}"
        property_obj.save()
        messages.error(request, f"Property '{property_obj.name}' suspended and report marked resolved.")
    else:
        report.status = PropertyReport.Status.REVIEWED
        messages.info(request, f"Report #{report.pk} marked under review.")

    report.save()
    return redirect("accounts:admin_reports_list")


# =====================================================================
# 5. CITY, STATE, LOCALITY & LANDMARK MANAGEMENT
# =====================================================================

@admin_required
def admin_locations_manage(request):
    """Unified management interface for States, Cities, Localities, Coaching Centres, and Landmarks."""
    section = request.GET.get("section", "cities").strip().lower()

    states = State.objects.all().order_by("name")
    cities = City.objects.select_related("state").all().order_by("name")
    localities = Locality.objects.select_related("city").all().order_by("city_name", "name")
    coaching_centres = Landmark.objects.filter(category=Landmark.Category.COACHING).order_by("city", "name")
    landmarks = Landmark.objects.exclude(category=Landmark.Category.COACHING).order_by("city", "name")

    counts = {
        "cities": cities.count(),
        "states": states.count(),
        "localities": localities.count(),
        "coaching": coaching_centres.count(),
        "landmarks": landmarks.count(),
    }

    context = {
        "section": section,
        "states": states,
        "cities": cities,
        "localities": localities,
        "coaching_centres": coaching_centres,
        "landmarks": landmarks,
        "counts": counts,
        "active_tab": "locations",
    }
    return render(request, "accounts/admin/locations_manage.html", context)


@admin_required
@require_POST
def admin_city_create(request):
    """Add a new city."""
    name = request.POST.get("name", "").strip()
    state_id = request.POST.get("state")
    tag = request.POST.get("tag", "").strip()
    area_summary = request.POST.get("area_summary", "").strip()
    latitude = request.POST.get("latitude", "").strip() or None
    longitude = request.POST.get("longitude", "").strip() or None
    is_popular = bool(request.POST.get("is_popular"))

    if not name:
        messages.error(request, "City name is required.")
        return redirect("accounts:admin_locations_manage")

    state = State.objects.filter(pk=state_id).first() if state_id else None
    state_name = state.name if state else request.POST.get("state_name", "Uttar Pradesh").strip()

    city, created = City.objects.get_or_create(
        name=name,
        defaults={
            "state": state,
            "state_name": state_name,
            "tag": tag,
            "area_summary": area_summary,
            "latitude": latitude,
            "longitude": longitude,
            "is_popular": is_popular,
        },
    )
    if created:
        messages.success(request, f"City '{city.name}' added successfully.")
    else:
        messages.warning(request, f"City '{city.name}' already exists.")

    return redirect("/accounts/admin/locations/?section=cities")


@admin_required
@require_POST
def admin_city_delete(request, pk):
    """Delete a city."""
    city = get_object_or_404(City, pk=pk)
    name = city.name
    city.delete()
    messages.info(request, f"City '{name}' deleted.")
    return redirect("/accounts/admin/locations/?section=cities")


@admin_required
@require_POST
def admin_state_create(request):
    """Add a new state."""
    name = request.POST.get("name", "").strip()
    code = request.POST.get("code", "").strip().upper()

    if not name:
        messages.error(request, "State name is required.")
        return redirect("/accounts/admin/locations/?section=states")

    state, created = State.objects.get_or_create(name=name, defaults={"code": code})
    if created:
        messages.success(request, f"State '{state.name}' added.")
    else:
        messages.warning(request, f"State '{state.name}' already exists.")

    return redirect("/accounts/admin/locations/?section=states")


@admin_required
@require_POST
def admin_state_delete(request, pk):
    """Delete a state."""
    state = get_object_or_404(State, pk=pk)
    name = state.name
    state.delete()
    messages.info(request, f"State '{name}' deleted.")
    return redirect("/accounts/admin/locations/?section=states")


@admin_required
@require_POST
def admin_locality_create(request):
    """Add a new locality."""
    name = request.POST.get("name", "").strip()
    city_id = request.POST.get("city")
    pincode = request.POST.get("pincode", "").strip()
    latitude = request.POST.get("latitude", "").strip() or None
    longitude = request.POST.get("longitude", "").strip() or None

    if not name:
        messages.error(request, "Locality name is required.")
        return redirect("/accounts/admin/locations/?section=localities")

    city = City.objects.filter(pk=city_id).first() if city_id else None
    city_name = city.name if city else request.POST.get("city_name", "").strip()

    locality = Locality.objects.create(
        name=name,
        city=city,
        city_name=city_name,
        pincode=pincode,
        latitude=latitude,
        longitude=longitude,
    )
    messages.success(request, f"Locality '{locality.name}' added.")
    return redirect("/accounts/admin/locations/?section=localities")


@admin_required
@require_POST
def admin_locality_delete(request, pk):
    """Delete a locality."""
    locality = get_object_or_404(Locality, pk=pk)
    name = locality.name
    locality.delete()
    messages.info(request, f"Locality '{name}' deleted.")
    return redirect("/accounts/admin/locations/?section=localities")


@admin_required
@require_POST
def admin_landmark_create(request):
    """Add a coaching centre or landmark."""
    name = request.POST.get("name", "").strip()
    category = request.POST.get("category", Landmark.Category.COACHING)
    city = request.POST.get("city", "").strip()
    state = request.POST.get("state", "Uttar Pradesh").strip()
    address = request.POST.get("address", "").strip()
    latitude = request.POST.get("latitude", "").strip()
    longitude = request.POST.get("longitude", "").strip()
    aliases = request.POST.get("aliases", "").strip()
    is_verified = bool(request.POST.get("is_verified", True))

    if not name or not city or not latitude or not longitude:
        messages.error(request, "Name, City, Latitude, and Longitude are required.")
        section = "coaching" if category == Landmark.Category.COACHING else "landmarks"
        return redirect(f"/accounts/admin/locations/?section={section}")

    landmark = Landmark.objects.create(
        name=name,
        category=category,
        city=city,
        state=state,
        address=address,
        latitude=latitude,
        longitude=longitude,
        aliases=aliases,
        is_verified=is_verified,
    )
    messages.success(request, f"Landmark '{landmark.name}' added.")
    section = "coaching" if category == Landmark.Category.COACHING else "landmarks"
    return redirect(f"/accounts/admin/locations/?section={section}")


@admin_required
@require_POST
def admin_landmark_delete(request, pk):
    """Delete a landmark."""
    landmark = get_object_or_404(Landmark, pk=pk)
    name = landmark.name
    is_coaching = landmark.category == Landmark.Category.COACHING
    landmark.delete()
    messages.info(request, f"Landmark '{name}' deleted.")
    section = "coaching" if is_coaching else "landmarks"
    return redirect(f"/accounts/admin/locations/?section={section}")

