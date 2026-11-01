"""Views for student enquiries and owner enquiry management."""

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
    property_obj = get_object_or_404(
        Property,
        slug=slug,
        is_active=True,
        is_approved=True,
    )
    form = EnquiryForm(request.POST)
    if form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.property = property_obj
        enquiry.student = request.user
        enquiry.save()
        messages.success(
            request,
            "Your enquiry has been sent. You can track its status from your dashboard.",
        )
    else:
        messages.error(request, "Please correct the enquiry form and try again.")
    return redirect(f"{property_obj.get_absolute_url()}#enquiry")


@student_required
def student_enquiry_list(request):
    enquiries = Enquiry.objects.filter(student=request.user).select_related(
        "property", "property__owner"
    )
    return render(
        request,
        "enquiries/student_list.html",
        {"enquiries": enquiries},
    )


@owner_required
def owner_enquiry_list(request):
    enquiries = Enquiry.objects.filter(
        property__owner=request.user
    ).select_related("property", "student")
    return render(
        request,
        "enquiries/owner_list.html",
        {
            "enquiries": enquiries,
            "status_choices": Enquiry.Status.choices,
        },
    )


@owner_required
@require_POST
def update_enquiry_status(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if enquiry.property.owner_id != request.user.id and not request.user.is_platform_admin:
        raise PermissionDenied("You can only update enquiries for your own properties.")

    status = request.POST.get("status", "")
    if status not in Enquiry.Status.values:
        messages.error(request, "Choose a valid enquiry status.")
    else:
        enquiry.status = status
        enquiry.save(update_fields=["status", "updated_at"])
        messages.success(request, "Enquiry status updated.")
    return redirect("enquiries:owner_list")
