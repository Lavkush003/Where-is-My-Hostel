"""Tests for enquiry models, student enquiry submissions, and owner management."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from enquiries.models import Enquiry
from properties.models import Property


class EnquiryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="hostel_mgr",
            email="hostel.mgr@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.other_owner = get_user_model().objects.create_user(
            username="other_mgr",
            email="other.mgr@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="student_enquirer",
            email="student.enquirer@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        cls.property = Property.objects.create(
            owner=cls.owner,
            name="City Centre PG",
            property_type=Property.PropertyType.PG,
            description="Central location.",
            city="Kota",
            address="Station Road",
            monthly_rent=7500,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )

    def test_student_submit_enquiry(self):
        self.client.force_login(self.student)
        url = reverse("enquiries:create", args=[self.property.slug])
        response = self.client.post(
            url,
            {
                "message": "When can I schedule a visit to view the room?",
                "contact_number": "9123456789",
            },
        )
        self.assertRedirects(response, f"{self.property.get_absolute_url()}#enquiry")
        enquiry = Enquiry.objects.get(student=self.student, property=self.property)
        self.assertEqual(enquiry.status, Enquiry.Status.PENDING)
        self.assertEqual(enquiry.contact_number, "9123456789")
        self.assertIn("City Centre PG", str(enquiry))

    def test_unauthenticated_user_cannot_enquire(self):
        url = reverse("enquiries:create", args=[self.property.slug])
        response = self.client.post(
            url,
            {
                "message": "Is Wi-Fi available?",
                "contact_number": "9123456789",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_owner_cannot_submit_enquiry(self):
        self.client.force_login(self.owner)
        url = reverse("enquiries:create", args=[self.property.slug])
        response = self.client.post(
            url,
            {
                "message": "Owner trying to enquire",
                "contact_number": "9876543210",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_updates_enquiry_status(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Need 2-sharing room.",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        self.client.force_login(self.owner)
        url = reverse("enquiries:update_status", args=[enquiry.pk])

        # Valid update
        response = self.client.post(url, {"status": Enquiry.Status.CONTACTED})
        self.assertRedirects(response, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.CONTACTED)

        # Invalid status choice rejected
        bad_response = self.client.post(url, {"status": "invalid_choice"})
        self.assertRedirects(bad_response, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.CONTACTED)

    def test_other_owner_cannot_update_enquiry(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Question for owner",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        self.client.force_login(self.other_owner)
        url = reverse("enquiries:update_status", args=[enquiry.pk])
        response = self.client.post(url, {"status": Enquiry.Status.CLOSED})
        self.assertEqual(response.status_code, 403)
