"""Tests for custom administration dashboard, listing moderation, user management, and location operations."""

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from enquiries.models import Enquiry
from locations.models import City, Landmark, Locality, State
from properties.models import Property, PropertyImage, PropertyReport, Room

User = get_user_model()


class AdminDashboardAndModerationTests(TestCase):
    """Test suite for PROMPT 8: Admin Dashboard, Property Moderation, User Management & City Management."""

    def setUp(self):
        self.client = Client()

        # Users
        self.admin_user = User.objects.create_superuser(
            username="test_admin",
            email="admin@test.example",
            password="AdminPassword123!",
            full_name="Platform Administrator",
        )

        self.owner = User.objects.create_user(
            username="test_owner",
            email="owner@test.example",
            password="OwnerPassword123!",
            role=User.Role.OWNER,
            full_name="Ramesh Owner",
            mobile_number="9876543210",
        )

        self.student = User.objects.create_user(
            username="test_student",
            email="student@test.example",
            password="StudentPassword123!",
            role=User.Role.STUDENT,
            full_name="Priya Student",
            mobile_number="9876543211",
        )

        # Properties
        self.property_approved = Property.objects.create(
            owner=self.owner,
            name="Sunrise Girls Hostel",
            property_type=Property.PropertyType.STUDENT_HOSTEL,
            gender_preference=Property.GenderPreference.GIRLS,
            description="Comfortable girls hostel near coaching centres.",
            address="10 Rajiv Gandhi Nagar",
            city="Kota",
            state="Rajasthan",
            monthly_rent=6000,
            contact_number="9876543210",
            is_approved=True,
            approval_status=Property.ApprovalStatus.APPROVED,
        )

        self.property_pending = Property.objects.create(
            owner=self.owner,
            name="New Ganga Boys PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.BOYS,
            description="Freshly submitted boys PG.",
            address="25 Civil Lines",
            city="Prayagraj",
            state="Uttar Pradesh",
            monthly_rent=4500,
            contact_number="9876543210",
            is_approved=False,
            approval_status=Property.ApprovalStatus.PENDING,
        )

        # Rooms
        Room.objects.create(
            property=self.property_approved,
            room_type="Single AC",
            occupancy=Room.Occupancy.SINGLE,
            monthly_rent=6000,
            total_beds=5,
            available_beds=2,
        )

        # Enquiries
        Enquiry.objects.create(
            student=self.student,
            property=self.property_approved,
            contact_number="9876543211",
            message="Looking for a single room.",
            move_in_date=date.today() + timedelta(days=7),
            occupancy=Enquiry.OccupancyPreference.SINGLE,
            status=Enquiry.Status.PENDING,
        )

    # -----------------------------------------------------------------
    # 1. Role-based Access Control
    # -----------------------------------------------------------------

    def test_admin_dashboard_accessible_by_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard_admin.html")

    def test_admin_dashboard_blocked_for_student(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_blocked_for_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_redirects_anonymous(self):
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 302)

    # -----------------------------------------------------------------
    # 2. Admin Dashboard Statistics & City Distribution
    # -----------------------------------------------------------------

    def test_admin_dashboard_metrics(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        ctx = response.context
        self.assertEqual(ctx["total_students"], 1)
        self.assertEqual(ctx["total_owners"], 1)
        self.assertEqual(ctx["total_properties"], 2)
        self.assertEqual(ctx["approved_properties"], 1)
        self.assertEqual(ctx["pending_properties"], 1)
        self.assertEqual(ctx["total_enquiries"], 1)

        # City distribution
        city_stats = ctx["city_stats"]
        cities = {s["city"]: s for s in city_stats}
        self.assertIn("Kota", cities)
        self.assertIn("Prayagraj", cities)
        self.assertEqual(cities["Kota"]["total"], 1)
        self.assertEqual(cities["Kota"]["approved"], 1)
        self.assertEqual(cities["Prayagraj"]["pending"], 1)

    # -----------------------------------------------------------------
    # 3. Property Moderation Workflow
    # -----------------------------------------------------------------

    def test_admin_property_list_filters(self):
        self.client.force_login(self.admin_user)

        # All
        resp = self.client.get(reverse("accounts:admin_property_list") + "?status=all")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["properties"]), 2)

        # Pending
        resp_pending = self.client.get(reverse("accounts:admin_property_list") + "?status=pending")
        self.assertEqual(resp_pending.status_code, 200)
        self.assertEqual(len(resp_pending.context["properties"]), 1)
        self.assertEqual(resp_pending.context["properties"][0].name, "New Ganga Boys PG")

        # Approved
        resp_approved = self.client.get(reverse("accounts:admin_property_list") + "?status=approved")
        self.assertEqual(resp_approved.status_code, 200)
        self.assertEqual(len(resp_approved.context["properties"]), 1)
        self.assertEqual(resp_approved.context["properties"][0].name, "Sunrise Girls Hostel")

    def test_admin_property_moderate_inspection_view(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_property_moderate", kwargs={"pk": self.property_pending.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Ganga Boys PG")
        self.assertContains(response, "Ramesh Owner")
        self.assertContains(response, "Prayagraj")

    def test_admin_approve_property(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_property_approve", kwargs={"pk": self.property_pending.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.property_pending.refresh_from_db()
        self.assertEqual(self.property_pending.approval_status, Property.ApprovalStatus.APPROVED)
        self.assertTrue(self.property_pending.is_approved)
        self.assertTrue(self.property_pending.is_publicly_visible)
        self.assertEqual(self.property_pending.rejection_reason, "")

    def test_admin_reject_property_with_reason(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_property_reject", kwargs={"pk": self.property_pending.pk})
        reason_text = "Missing clear photographs of the bathroom and room interior."
        response = self.client.post(url, {"rejection_reason": reason_text})
        self.assertEqual(response.status_code, 302)

        self.property_pending.refresh_from_db()
        self.assertEqual(self.property_pending.approval_status, Property.ApprovalStatus.REJECTED)
        self.assertFalse(self.property_pending.is_approved)
        self.assertFalse(self.property_pending.is_publicly_visible)
        self.assertEqual(self.property_pending.rejection_reason, reason_text)

    def test_admin_suspend_property(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_property_suspend", kwargs={"pk": self.property_approved.pk})
        response = self.client.post(url, {"moderation_notes": "Multiple scam complaints."})
        self.assertEqual(response.status_code, 302)

        self.property_approved.refresh_from_db()
        self.assertEqual(self.property_approved.approval_status, Property.ApprovalStatus.SUSPENDED)
        self.assertTrue(self.property_approved.is_suspended)
        self.assertFalse(self.property_approved.is_approved)
        self.assertFalse(self.property_approved.is_active)
        self.assertFalse(self.property_approved.is_publicly_visible)

    def test_admin_delete_misleading_property(self):
        self.client.force_login(self.admin_user)
        prop_id = self.property_pending.pk
        url = reverse("accounts:admin_property_delete", kwargs={"pk": prop_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Property.objects.filter(pk=prop_id).exists())

    # -----------------------------------------------------------------
    # 4. User Management & Activity
    # -----------------------------------------------------------------

    def test_admin_user_list_and_search(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_user_list")

        # View list
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ramesh Owner")
        self.assertContains(resp, "Priya Student")

        # Role filter
        resp_students = self.client.get(url + "?role=student")
        self.assertEqual(len(resp_students.context["users"]), 1)
        self.assertEqual(resp_students.context["users"][0].username, "test_student")

        # Search
        resp_search = self.client.get(url + "?q=Ramesh")
        self.assertEqual(len(resp_search.context["users"]), 1)
        self.assertEqual(resp_search.context["users"][0].username, "test_owner")

    def test_admin_user_toggle_status(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_user_toggle_status", kwargs={"pk": self.owner.pk})

        # Deactivate
        self.client.post(url)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_active)

        # Reactivate
        self.client.post(url)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)

    def test_admin_cannot_deactivate_self(self):
        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_user_toggle_status", kwargs={"pk": self.admin_user.pk})
        self.client.post(url)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_admin_user_activity_view(self):
        self.client.force_login(self.admin_user)

        # Owner activity
        url_owner = reverse("accounts:admin_user_activity", kwargs={"pk": self.owner.pk})
        resp_owner = self.client.get(url_owner)
        self.assertEqual(resp_owner.status_code, 200)
        self.assertContains(resp_owner, "Sunrise Girls Hostel")
        self.assertContains(resp_owner, "New Ganga Boys PG")

        # Student activity
        url_student = reverse("accounts:admin_user_activity", kwargs={"pk": self.student.pk})
        resp_student = self.client.get(url_student)
        self.assertEqual(resp_student.status_code, 200)
        self.assertContains(resp_student, "Looking for a single room.")

    # -----------------------------------------------------------------
    # 5. Reported Listings Management
    # -----------------------------------------------------------------

    def test_student_report_submission(self):
        self.client.force_login(self.student)
        url = reverse("properties:report", kwargs={"slug": self.property_approved.slug})
        response = self.client.post(
            url,
            {
                "reason": PropertyReport.Reason.INCORRECT_PRICING,
                "details": "Listed rent is 6000 but owner demands 9000 over phone.",
            },
        )
        self.assertEqual(response.status_code, 302)

        report = PropertyReport.objects.filter(property=self.property_approved).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reported_by, self.student)
        self.assertEqual(report.reason, PropertyReport.Reason.INCORRECT_PRICING)
        self.assertEqual(report.status, PropertyReport.Status.PENDING)

    def test_admin_handle_report_resolve(self):
        report = PropertyReport.objects.create(
            property=self.property_approved,
            reported_by=self.student,
            reason=PropertyReport.Reason.FAKE_LISTING,
            details="Address does not exist.",
            status=PropertyReport.Status.PENDING,
        )

        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_report_action", kwargs={"pk": report.pk})
        response = self.client.post(url, {"action": "resolve", "action_taken": "Contacted owner and verified location."})
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertEqual(report.status, PropertyReport.Status.RESOLVED)
        self.assertEqual(report.reviewed_by, self.admin_user)

    def test_admin_handle_report_suspend_property(self):
        report = PropertyReport.objects.create(
            property=self.property_approved,
            reported_by=self.student,
            reason=PropertyReport.Reason.FRAUDULENT_OWNER,
            details="Owner demanding advance transfer and unreachable.",
            status=PropertyReport.Status.PENDING,
        )

        self.client.force_login(self.admin_user)
        url = reverse("accounts:admin_report_action", kwargs={"pk": report.pk})
        response = self.client.post(url, {"action": "suspend_property"})
        self.assertEqual(response.status_code, 302)

        report.refresh_from_db()
        self.assertEqual(report.status, PropertyReport.Status.RESOLVED)

        self.property_approved.refresh_from_db()
        self.assertEqual(self.property_approved.approval_status, Property.ApprovalStatus.SUSPENDED)
        self.assertTrue(self.property_approved.is_suspended)

    # -----------------------------------------------------------------
    # 6. City, State, Locality & Landmark Management
    # -----------------------------------------------------------------

    def test_admin_create_and_delete_city(self):
        self.client.force_login(self.admin_user)

        # Create City
        url_create = reverse("accounts:admin_city_create")
        resp = self.client.post(
            url_create,
            {
                "name": "Varanasi",
                "tag": "Spiritual Capital",
                "area_summary": "BHU & Lanka Hub",
                "is_popular": "1",
            },
        )
        self.assertEqual(resp.status_code, 302)

        city = City.objects.filter(name="Varanasi").first()
        self.assertIsNotNone(city)
        self.assertTrue(city.is_popular)

        # Delete City
        url_del = reverse("accounts:admin_city_delete", kwargs={"pk": city.pk})
        resp_del = self.client.post(url_del)
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(City.objects.filter(name="Varanasi").exists())

    def test_admin_create_and_delete_landmark(self):
        self.client.force_login(self.admin_user)

        # Create Coaching Centre
        url_create = reverse("accounts:admin_landmark_create")
        resp = self.client.post(
            url_create,
            {
                "name": "Motion Education",
                "category": Landmark.Category.COACHING,
                "city": "Kota",
                "state": "Rajasthan",
                "latitude": "25.138800",
                "longitude": "75.845600",
                "aliases": "Motion Kota",
            },
        )
        self.assertEqual(resp.status_code, 302)

        landmark = Landmark.objects.filter(name="Motion Education").first()
        self.assertIsNotNone(landmark)
        self.assertEqual(landmark.category, Landmark.Category.COACHING)

        # Delete Landmark
        url_del = reverse("accounts:admin_landmark_delete", kwargs={"pk": landmark.pk})
        resp_del = self.client.post(url_del)
        self.assertEqual(resp_del.status_code, 302)
        self.assertFalse(Landmark.objects.filter(name="Motion Education").exists())

    def test_city_management_blocked_for_ordinary_users(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("accounts:admin_locations_manage"))
        self.assertEqual(resp.status_code, 403)

        resp_post = self.client.post(reverse("accounts:admin_city_create"), {"name": "TestCity"})
        self.assertEqual(resp_post.status_code, 403)

