"""Tests for enquiry models, student enquiry submissions, occupancy, move-in dates, cancellations, and owner management."""

from datetime import date, timedelta
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
        cls.other_student = get_user_model().objects.create_user(
            username="other_student",
            email="other.student@example.com",
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
                "occupancy": "single",
                "move_in_date": (date.today() + timedelta(days=5)).isoformat(),
            },
        )
        self.assertRedirects(response, f"{self.property.get_absolute_url()}#enquiry")
        enquiry = Enquiry.objects.get(student=self.student, property=self.property)
        self.assertEqual(enquiry.status, Enquiry.Status.PENDING)
        self.assertEqual(enquiry.contact_number, "9123456789")
        self.assertEqual(enquiry.occupancy, "single")
        self.assertEqual(enquiry.move_in_date, date.today() + timedelta(days=5))
        self.assertIn("City Centre PG", str(enquiry))

    def test_student_cannot_submit_past_move_in_date(self):
        self.client.force_login(self.student)
        url = reverse("enquiries:create", args=[self.property.slug])
        past_date = date.today() - timedelta(days=10)
        response = self.client.post(
            url,
            {
                "message": "Need room starting in the past.",
                "contact_number": "9123456789",
                "move_in_date": past_date.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Enquiry.objects.filter(student=self.student, property=self.property).exists())

    def test_prevent_duplicate_active_enquiries(self):
        self.client.force_login(self.student)
        url = reverse("enquiries:create", args=[self.property.slug])

        # First enquiry succeeds
        resp1 = self.client.post(
            url,
            {
                "message": "First enquiry.",
                "contact_number": "9123456789",
            },
        )
        self.assertRedirects(resp1, f"{self.property.get_absolute_url()}#enquiry")
        self.assertEqual(Enquiry.objects.filter(student=self.student, property=self.property).count(), 1)

        # Duplicate active enquiry is rejected
        resp2 = self.client.post(
            url,
            {
                "message": "Duplicate enquiry attempt.",
                "contact_number": "9123456789",
            },
        )
        self.assertRedirects(resp2, f"{self.property.get_absolute_url()}#enquiry")
        self.assertEqual(Enquiry.objects.filter(student=self.student, property=self.property).count(), 1)

    def test_student_can_re_enquire_after_cancellation(self):
        self.client.force_login(self.student)
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Initial enquiry.",
            contact_number="9123456789",
            status=Enquiry.Status.CANCELLED,
        )

        url = reverse("enquiries:create", args=[self.property.slug])
        resp = self.client.post(
            url,
            {
                "message": "Fresh enquiry after previous cancellation.",
                "contact_number": "9123456789",
            },
        )
        self.assertRedirects(resp, f"{self.property.get_absolute_url()}#enquiry")
        self.assertEqual(
            Enquiry.objects.filter(student=self.student, property=self.property, status=Enquiry.Status.PENDING).count(),
            1,
        )

    def test_student_cancel_enquiry_when_pending(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Cancel me please.",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        self.client.force_login(self.student)
        url = reverse("enquiries:cancel", args=[enquiry.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("enquiries:student_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.CANCELLED)

    def test_student_cannot_cancel_accepted_enquiry(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Already accepted enquiry.",
            contact_number="9123456789",
            status=Enquiry.Status.ACCEPTED,
        )
        self.client.force_login(self.student)
        url = reverse("enquiries:cancel", args=[enquiry.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("enquiries:student_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.ACCEPTED)

    def test_other_student_cannot_cancel_enquiry(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Private enquiry.",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        self.client.force_login(self.other_student)
        url = reverse("enquiries:cancel", args=[enquiry.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.PENDING)

    def test_owner_accept_and_reject_shortcuts(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Can I book?",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        self.client.force_login(self.owner)

        # Accept shortcut
        accept_url = reverse("enquiries:accept", args=[enquiry.pk])
        resp_acc = self.client.post(accept_url)
        self.assertRedirects(resp_acc, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.ACCEPTED)

        # Reject shortcut
        reject_url = reverse("enquiries:reject", args=[enquiry.pk])
        resp_rej = self.client.post(reject_url)
        self.assertRedirects(resp_rej, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.REJECTED)

    def test_owner_cannot_modify_cancelled_enquiry(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="I changed my mind.",
            contact_number="9123456789",
            status=Enquiry.Status.CANCELLED,
        )
        self.client.force_login(self.owner)
        url = reverse("enquiries:update_status", args=[enquiry.pk])
        resp = self.client.post(url, {"status": Enquiry.Status.ACCEPTED})
        self.assertRedirects(resp, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.CANCELLED)

    def test_whatsapp_urls_generated_correctly(self):
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Looking for single room.",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )
        # Owner contact is 9876543210
        self.assertIn("https://wa.me/919876543210", enquiry.owner_whatsapp_url)
        # Student contact is 9123456789
        self.assertIn("https://wa.me/919123456789", enquiry.student_whatsapp_url)

    def test_dashboard_enquiry_notifications(self):
        # Create 1 pending enquiry
        Enquiry.objects.create(
            property=self.property,
            student=self.student,
            message="Pending question.",
            contact_number="9123456789",
            status=Enquiry.Status.PENDING,
        )

        # Owner dashboard contains pending notification
        self.client.force_login(self.owner)
        resp_owner = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(resp_owner.status_code, 200)
        self.assertContains(resp_owner, "pending student enquir")

        # Student dashboard contains recent enquiry
        self.client.force_login(self.student)
        resp_student = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(resp_student.status_code, 200)
        self.assertContains(resp_student, "City Centre PG")

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
