"""Views for student enquiries, cancellations, and owner enquiry management."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import owner_required, student_required
from properties.models import Property

from .forms import EnquiryForm
from .models import Enquiry


@student_required
@require_POST
def submit_enquiry(request, slug):
    """Allow an authenticated student to submit an enquiry for a live property."""
    property_obj = get_object_or_404(
        Property,
        slug=slug,
        is_active=True,
        is_approved=True,
    )

    if property_obj.owner_id == request.user.id:
        raise PermissionDenied("Property owners cannot submit enquiries on their own properties.")

    form = EnquiryForm(
        request.POST,
        student=request.user,
        property_obj=property_obj,
    )
    if form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.property = property_obj
        enquiry.student = request.user
        enquiry.status = Enquiry.Status.PENDING
        enquiry.save()
        messages.success(
            request,
            f"Your enquiry for {property_obj.name} has been sent to the owner. "
            "You can track responses from your student dashboard.",
        )
    else:
        error_msgs = []
        for field, errors in form.errors.items():
            for error in errors:
                error_msgs.append(f"{error}")
        messages.error(request, " ".join(error_msgs) or "Please correct the form and try again.")

    return redirect(f"{property_obj.get_absolute_url()}#enquiry")


@student_required
def student_enquiry_list(request):
    """View enquiry history for the logged-in student."""
    status_filter = request.GET.get("status", "").strip().lower()

    qs = (
        Enquiry.objects.filter(student=request.user)
        .select_related("property", "property__owner")
        .order_by("-created_at")
    )

    if status_filter in Enquiry.Status.values:
        filtered_enquiries = qs.filter(status=status_filter)
    else:
        filtered_enquiries = qs
        status_filter = ""

    # Statistics for filter pills
    all_enquiries = list(qs)
    counts = {
        "all": len(all_enquiries),
        "pending": sum(1 for e in all_enquiries if e.status == Enquiry.Status.PENDING),
        "contacted": sum(1 for e in all_enquiries if e.status == Enquiry.Status.CONTACTED),
        "accepted": sum(1 for e in all_enquiries if e.status == Enquiry.Status.ACCEPTED),
        "rejected": sum(1 for e in all_enquiries if e.status == Enquiry.Status.REJECTED),
        "cancelled": sum(1 for e in all_enquiries if e.status == Enquiry.Status.CANCELLED),
    }

    return render(
        request,
        "enquiries/student_list.html",
        {
            "enquiries": filtered_enquiries,
            "status_filter": status_filter,
            "counts": counts,
            "status_choices": Enquiry.Status.choices,
        },
    )


@student_required
@require_POST
def cancel_enquiry(request, pk):
    """Allow student to cancel an enquiry if it has not yet been accepted."""
    enquiry = get_object_or_404(Enquiry, pk=pk)

    if enquiry.student_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only cancel your own enquiries.")

    if not enquiry.can_be_cancelled_by_student:
        messages.error(
            request,
            f"Cannot cancel enquiry with status '{enquiry.get_status_display()}'. "
            "Only pending or contacted enquiries can be cancelled.",
        )
        return redirect("enquiries:student_list")

    enquiry.status = Enquiry.Status.CANCELLED
    enquiry.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Your enquiry for {enquiry.property.name} has been cancelled.")
    return redirect("enquiries:student_list")


@owner_required
def owner_enquiry_list(request):
    """View and manage student enquiries for properties owned by this owner."""
    status_filter = request.GET.get("status", "").strip().lower()

    qs = (
        Enquiry.objects.filter(property__owner=request.user)
        .select_related("property", "student")
        .order_by("-created_at")
    )

    if status_filter in Enquiry.Status.values:
        filtered_enquiries = qs.filter(status=status_filter)
    else:
        filtered_enquiries = qs
        status_filter = ""

    all_enquiries = list(qs)
    counts = {
        "all": len(all_enquiries),
        "pending": sum(1 for e in all_enquiries if e.status == Enquiry.Status.PENDING),
        "contacted": sum(1 for e in all_enquiries if e.status == Enquiry.Status.CONTACTED),
        "accepted": sum(1 for e in all_enquiries if e.status == Enquiry.Status.ACCEPTED),
        "rejected": sum(1 for e in all_enquiries if e.status == Enquiry.Status.REJECTED),
        "cancelled": sum(1 for e in all_enquiries if e.status == Enquiry.Status.CANCELLED),
    }

    return render(
        request,
        "enquiries/owner_list.html",
        {
            "enquiries": filtered_enquiries,
            "status_filter": status_filter,
            "counts": counts,
            "status_choices": Enquiry.Status.choices,
        },
    )


@owner_required
@require_POST
def update_enquiry_status(request, pk):
    """Update enquiry status by the property owner (Accept, Reject, Contacted, etc.)."""
    enquiry = get_object_or_404(Enquiry, pk=pk)

    if enquiry.property.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only update enquiries for your own properties.")

    action = request.POST.get("action", "").strip().lower()
    new_status = request.POST.get("status", "").strip().lower()

    if action == "accept":
        new_status = Enquiry.Status.ACCEPTED
    elif action == "reject":
        new_status = Enquiry.Status.REJECTED
    elif action == "contacted":
        new_status = Enquiry.Status.CONTACTED

    if new_status not in Enquiry.Status.values:
        messages.error(request, "Choose a valid enquiry status.")
    elif enquiry.status == Enquiry.Status.CANCELLED and not request.user.is_platform_admin:
        messages.error(request, "Cannot update status of an enquiry cancelled by the student.")
    else:
        enquiry.status = new_status
        enquiry.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            f"Enquiry from {enquiry.student.get_full_name()} marked as {enquiry.get_status_display()}.",
        )

    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("enquiries:owner_list")


@owner_required
@require_POST
def owner_accept_enquiry(request, pk):
    """Quick action shortcut for owners to accept an enquiry."""
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if enquiry.property.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage enquiries for your own properties.")

    if enquiry.status == Enquiry.Status.CANCELLED:
        messages.error(request, "This enquiry was cancelled by the student.")
    else:
        enquiry.status = Enquiry.Status.ACCEPTED
        enquiry.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Enquiry from {enquiry.student.get_full_name()} accepted.")

    return redirect("enquiries:owner_list")


@owner_required
@require_POST
def owner_reject_enquiry(request, pk):
    """Quick action shortcut for owners to reject an enquiry."""
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if enquiry.property.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only manage enquiries for your own properties.")

    if enquiry.status == Enquiry.Status.CANCELLED:
        messages.error(request, "This enquiry was cancelled by the student.")
    else:
        enquiry.status = Enquiry.Status.REJECTED
        enquiry.save(update_fields=["status", "updated_at"])
        messages.info(request, f"Enquiry from {enquiry.student.get_full_name()} rejected.")

    return redirect("enquiries:owner_list")
