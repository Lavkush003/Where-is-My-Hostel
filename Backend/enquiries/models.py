"""Models for student enquiries and owner responses."""

from django.conf import settings
from django.db import models

from properties.models import Property


class Enquiry(models.Model):
    """A student enquiry about a property listing."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONTACTED = "contacted", "Contacted"
        CLOSED = "closed", "Closed"

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

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.property.name}"
