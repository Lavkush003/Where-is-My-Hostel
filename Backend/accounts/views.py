"""Authentication, dashboard and profile views."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from enquiries.models import Enquiry
from properties.models import Favourite, Property

from .decorators import owner_required, student_required
from .forms import (
    OwnerProfileForm,
    RegistrationForm,
    StudentProfileForm,
    StyledAuthenticationForm,
)
from .models import OwnerProfile


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class AccountLogoutView(LogoutView):
    next_page = "core:home"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(
            request,
            f"Welcome, {user.get_full_name()}. Your account has been created.",
        )
        return redirect("accounts:dashboard")

    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    user = request.user
    context = {"user": user}

    if user.is_platform_admin:
        context.update(
            {
                "user_count": user.__class__.objects.count(),
                "owner_count": user.__class__.objects.filter(role=user.Role.OWNER).count(),
                "property_count": Property.objects.count(),
                "enquiry_count": Enquiry.objects.count(),
                "recent_properties": Property.objects.select_related("owner")[:5],
            }
        )
        template_name = "accounts/dashboard_admin.html"
    elif user.is_owner:
        profile, _ = OwnerProfile.objects.get_or_create(
            user=user,
            defaults={
                "owner_name": user.full_name,
                "contact_number": user.mobile_number,
            },
        )
        properties = Property.objects.filter(owner=user)
        enquiries_qs = Enquiry.objects.filter(property__owner=user).select_related(
            "property", "student"
        )
        pending_enquiry_count = enquiries_qs.filter(status=Enquiry.Status.PENDING).count()
        context.update(
            {
                "profile": profile,
                "properties": properties[:5],
                "property_count": properties.count(),
                "active_property_count": properties.filter(is_active=True).count(),
                "enquiries": enquiries_qs,
                "enquiry_count": enquiries_qs.count(),
                "pending_enquiry_count": pending_enquiry_count,
            }
        )
        context["profile_is_complete"] = bool(
            profile.owner_name
            and profile.contact_number
            and profile.business_name
            and profile.city
        )
        template_name = "accounts/dashboard_owner.html"
    else:
        favourites = Favourite.objects.filter(student=user).select_related("property")
        enquiries_qs = Enquiry.objects.filter(student=user).select_related("property")
        pending_enquiry_count = enquiries_qs.filter(status=Enquiry.Status.PENDING).count()
        accepted_enquiry_count = enquiries_qs.filter(status=Enquiry.Status.ACCEPTED).count()
        context.update(
            {
                "favourites": favourites[:4],
                "favourite_count": favourites.count(),
                "enquiries": enquiries_qs[:5],
                "enquiry_count": enquiries_qs.count(),
                "pending_enquiry_count": pending_enquiry_count,
                "accepted_enquiry_count": accepted_enquiry_count,
            }
        )
        template_name = "accounts/dashboard_student.html"

    return render(request, template_name, context)


@student_required
def student_profile(request):
    form = StudentProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your student profile has been updated.")
        return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile_form.html",
        {
            "form": form,
            "page_title": "Student profile",
            "page_copy": "Keep your contact details up to date for property owners.",
            "email": request.user.email,
            "back_url": "accounts:dashboard",
            "favourite_count": Favourite.objects.filter(student=request.user).count(),
            "enquiry_count": Enquiry.objects.filter(student=request.user).count(),
        },
    )


@student_required
def favourite_list(request):
    favourites = Favourite.objects.filter(student=request.user).select_related(
        "property", "property__owner"
    )
    return render(request, "accounts/favourites.html", {"favourites": favourites})


@owner_required
def owner_profile(request):
    profile, _ = OwnerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "owner_name": request.user.full_name,
            "contact_number": request.user.mobile_number,
        },
    )

    if request.method == "POST":
        form = OwnerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            saved_profile = form.save()
            updated_fields = []
            if saved_profile.owner_name and saved_profile.owner_name != request.user.full_name:
                request.user.full_name = saved_profile.owner_name
                updated_fields.append("full_name")
            if saved_profile.contact_number and saved_profile.contact_number != request.user.mobile_number:
                request.user.mobile_number = saved_profile.contact_number
                updated_fields.append("mobile_number")
            if updated_fields:
                request.user.save(update_fields=updated_fields)
            messages.success(request, "Your property owner profile has been updated.")
            return redirect("accounts:owner_profile")
    else:
        if not profile.owner_name:
            profile.owner_name = request.user.full_name
        if not profile.contact_number:
            profile.contact_number = request.user.mobile_number
        form = OwnerProfileForm(instance=profile)

    return render(
        request,
        "accounts/owner_profile.html",
        {
            "form": form,
            "profile": profile,
            "back_url": "accounts:dashboard",
            "property_count": Property.objects.filter(owner=request.user).count(),
            "enquiry_count": Enquiry.objects.filter(property__owner=request.user).count(),
        },
    )
