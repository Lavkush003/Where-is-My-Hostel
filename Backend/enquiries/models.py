"""Models for student enquiries, occupancy preferences, and owner responses."""

import builtins
import urllib.parse
from django.conf import settings
from django.db import models

from properties.models import Property


class Enquiry(models.Model):
    """A student enquiry about a property listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONTACTED = "contacted", "Contacted"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        # Backward compatibility alias
        CLOSED = "closed", "Closed"

    class OccupancyPreference(models.TextChoices):
        ANY = "any", "Any Occupancy"
        SINGLE = "single", "Single Sharing"
        DOUBLE = "double", "Double Sharing"
        TRIPLE = "triple", "Triple Sharing"
        FOUR = "four", "Four Sharing"

    # Field 'property' shadows built-in property decorator inside class scope
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="enquiries",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enquiries",
    )
    message = models.TextField()
    contact_number = models.CharField(max_length=16)
    move_in_date = models.DateField(
        "Preferred move-in date",
        null=True,
        blank=True,
        help_text="Student's preferred check-in / move-in date.",
    )
    occupancy = models.CharField(
        "Desired room occupancy",
        max_length=20,
        choices=OccupancyPreference.choices,
        default=OccupancyPreference.ANY,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "enquiries"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "property"],
                condition=models.Q(status__in=["pending", "contacted", "accepted"]),
                name="unique_active_student_property_enquiry",
            )
        ]

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.property.name} ({self.get_status_display()})"

    @builtins.property
    def is_active(self):
        """Active enquiries prevent duplicate active submissions."""
        return self.status in [
            self.Status.PENDING,
            self.Status.CONTACTED,
            self.Status.ACCEPTED,
        ]

    @builtins.property
    def can_be_cancelled_by_student(self):
        """Students can cancel pending or contacted enquiries before they are accepted."""
        return self.status in [self.Status.PENDING, self.Status.CONTACTED]

    @builtins.property
    def owner_whatsapp_url(self):
        """Validated WhatsApp link for student to contact property owner."""
        phone = getattr(self.property, "contact_number", None)
        if not phone:
            return None
        clean = "".join(filter(str.isdigit, str(phone)))
        if not clean:
            return None
        if len(clean) == 10:
            clean = "91" + clean
        msg = (
            f"Hello, I am {self.student.get_full_name()}! "
            f"I submitted an enquiry for {self.property.name} on Where Is My Hostel."
        )
        return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"

    @builtins.property
    def student_whatsapp_url(self):
        """Validated WhatsApp link for owner to message student."""
        phone = self.contact_number or getattr(self.student, "mobile_number", None)
        if not phone:
            return None
        clean = "".join(filter(str.isdigit, str(phone)))
        if not clean:
            return None
        if len(clean) == 10:
            clean = "91" + clean
        msg = (
            f"Hello {self.student.get_full_name()}! "
            f"Regarding your enquiry for {self.property.name} on Where Is My Hostel."
        )
        return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"
