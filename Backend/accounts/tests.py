"""Comprehensive tests for authentication, user roles, profiles, and permissions."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import OwnerProfile, User
from enquiries.models import Enquiry
from properties.models import Favourite, Property


class UserModelTests(TestCase):
    def test_create_student_user(self):
        user = get_user_model().objects.create_user(
            username="student_john",
            email="john@example.com",
            password="StrongPassword123!",
            full_name="John Doe",
            mobile_number="9876543210",
            role=User.Role.STUDENT,
        )
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_owner)
        self.assertFalse(user.is_platform_admin)
        self.assertEqual(user.get_full_name(), "John Doe")
        self.assertEqual(user.get_short_name(), "John")

    def test_create_owner_user(self):
        user = get_user_model().objects.create_user(
            username="owner_raj",
            email="raj@example.com",
            password="StrongPassword123!",
            full_name="Rajesh Sharma",
            mobile_number="9876543211",
            role=User.Role.OWNER,
        )
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertFalse(user.is_student)
        self.assertTrue(user.is_owner)
        self.assertFalse(user.is_platform_admin)

    def test_create_superuser(self):
        admin = get_user_model().objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="StrongAdminPassword123!",
            full_name="Admin Supervisor",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_platform_admin)
        self.assertFalse(admin.is_student)
        self.assertFalse(admin.is_owner)

    def test_auto_generate_username_from_email(self):
        user = get_user_model().objects.create_user(
            email="priya.sharma@example.com",
            password="StrongPassword123!",
            full_name="Priya Sharma",
        )
        self.assertTrue(user.username.startswith("priya-sharma"))

    def test_email_normalized_to_lowercase(self):
        user = get_user_model().objects.create_user(
            username="caps_user",
            email="MiXeD.CaSe@ExAmPlE.CoM",
            password="StrongPassword123!",
        )
        self.assertEqual(user.email, "mixed.case@example.com")


class RegistrationTests(TestCase):
    def test_registration_page_renders(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")
        self.assertContains(response, "Full name")
        self.assertContains(response, "Email address")
        self.assertContains(response, "Mobile number")
        self.assertContains(response, "Account type")

    def test_student_registration_success(self):
        payload = {
            "full_name": "Aarav Patel",
            "email": "aarav.patel@example.com",
            "mobile_number": "9123456789",
            "password1": "SecureStudentPass2026!",
            "password2": "SecureStudentPass2026!",
            "account_type": User.Role.STUDENT,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertRedirects(response, reverse("accounts:dashboard"))

        user = get_user_model().objects.get(email="aarav.patel@example.com")
        self.assertEqual(user.full_name, "Aarav Patel")
        self.assertEqual(user.mobile_number, "9123456789")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password("SecureStudentPass2026!"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_owner_registration_success(self):
        payload = {
            "full_name": "Suresh Gupta",
            "email": "suresh.gupta@example.com",
            "mobile_number": "9811122233",
            "password1": "SecureOwnerPass2026!",
            "password2": "SecureOwnerPass2026!",
            "account_type": User.Role.OWNER,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertRedirects(response, reverse("accounts:dashboard"))

        user = get_user_model().objects.get(email="suresh.gupta@example.com")
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertTrue(hasattr(user, "owner_profile"))
        self.assertEqual(user.owner_profile.owner_name, "Suresh Gupta")
        self.assertEqual(user.owner_profile.contact_number, "9811122233")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_duplicate_email_rejected(self):
        get_user_model().objects.create_user(
            username="existing_student",
            email="duplicate@example.com",
            password="ExistingPassword123!",
            role=User.Role.STUDENT,
        )
        payload = {
            "full_name": "Another User",
            "email": "DUPLICATE@EXAMPLE.COM",  # Case-insensitive duplicate check
            "mobile_number": "9998887776",
            "password1": "SecurePass2026!",
            "password2": "SecurePass2026!",
            "account_type": User.Role.STUDENT,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email address already exists.")
        self.assertEqual(get_user_model().objects.filter(email="duplicate@example.com").count(), 1)

    def test_password_mismatch_rejected(self):
        payload = {
            "full_name": "Mismatch User",
            "email": "mismatch@example.com",
            "mobile_number": "9998887771",
            "password1": "FirstPassword123!",
            "password2": "SecondPassword123!",
            "account_type": User.Role.STUDENT,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(email="mismatch@example.com").exists())

    def test_weak_password_rejected(self):
        payload = {
            "full_name": "Weak User",
            "email": "weak@example.com",
            "mobile_number": "9998887772",
            "password1": "123",
            "password2": "123",
            "account_type": User.Role.STUDENT,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(email="weak@example.com").exists())

    def test_invalid_mobile_number_rejected(self):
        payload = {
            "full_name": "Bad Phone User",
            "email": "badphone@example.com",
            "mobile_number": "12345",  # Too short
            "password1": "ValidPassword2026!",
            "password2": "ValidPassword2026!",
            "account_type": User.Role.STUDENT,
        }
        response = self.client.post(reverse("accounts:register"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid mobile number")
        self.assertFalse(get_user_model().objects.filter(email="badphone@example.com").exists())

    def test_authenticated_user_redirected_from_register(self):
        user = get_user_model().objects.create_user(
            username="signed_in",
            email="signedin@example.com",
            password="SignedPassword123!",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:register"))
        self.assertRedirects(response, reverse("accounts:dashboard"))


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "ValidUserPassword2026!"
        cls.user = get_user_model().objects.create_user(
            username="student_login_test",
            email="login.test@example.com",
            password=cls.password,
            full_name="Login Test User",
            mobile_number="9876500000",
            role=User.Role.STUDENT,
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")

    def test_login_with_email_success(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login.test@example.com", "password": self.password},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_email_case_insensitive(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "LOGIN.TEST@EXAMPLE.COM", "password": self.password},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_username_success(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "student_login_test", "password": self.password},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login.test@example.com", "password": "WrongPassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_nonexistent_user_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "nonexistent@example.com", "password": "AnyPassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_via_post_succeeds(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_authenticated_user_redirected_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("accounts:dashboard"))


class DashboardRoleRestrictionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = get_user_model().objects.create_user(
            username="dash_student",
            email="dash_student@example.com",
            password="Password123!",
            full_name="Dashboard Student",
            role=User.Role.STUDENT,
        )
        cls.owner = get_user_model().objects.create_user(
            username="dash_owner",
            email="dash_owner@example.com",
            password="Password123!",
            full_name="Dashboard Owner",
            role=User.Role.OWNER,
        )
        cls.admin = get_user_model().objects.create_superuser(
            username="dash_admin",
            email="dash_admin@example.com",
            password="Password123!",
            full_name="Dashboard Admin",
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_student_sees_student_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard_student.html")
        self.assertContains(response, "Student dashboard")
        self.assertContains(response, "Saved stays")

    def test_owner_sees_owner_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard_owner.html")
        self.assertContains(response, "Property owner dashboard")
        self.assertContains(response, "Total properties")

    def test_admin_sees_admin_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard_admin.html")
        self.assertContains(response, "Platform overview")
        self.assertContains(response, "Open Django admin")


class StudentProfileAndFeaturesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = get_user_model().objects.create_user(
            username="student_user",
            email="student.user@example.com",
            password="Password123!",
            full_name="Original Name",
            mobile_number="9876543210",
            role=User.Role.STUDENT,
        )
        cls.owner = get_user_model().objects.create_user(
            username="owner_user",
            email="owner.user@example.com",
            password="Password123!",
            full_name="Hostel Owner",
            role=User.Role.OWNER,
        )
        cls.property = Property.objects.create(
            owner=cls.owner,
            name="Sunrise Boys PG",
            property_type=Property.PropertyType.PG,
            description="Comfortable PG near university.",
            city="Kota",
            address="Plot 10, Vigyan Nagar",
            monthly_rent=6500,
            contact_number="9876500001",
            is_active=True,
            is_approved=True,
        )

    def setUp(self):
        self.client.force_login(self.student)

    def test_view_student_profile(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student profile")
        self.assertContains(response, "Original Name")
        self.assertContains(response, "9876543210")
        self.assertContains(response, "student.user@example.com")

    def test_update_student_profile_mobile_and_name(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {"full_name": "Updated Student Name", "mobile_number": "9112233445"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, "Updated Student Name")
        self.assertEqual(self.student.mobile_number, "9112233445")

    def test_save_and_unsave_favourite_property(self):
        # Save favourite
        response = self.client.post(
            reverse("properties:favourite", args=[self.property.slug]),
            {"next": reverse("accounts:favourites")},
        )
        self.assertRedirects(response, reverse("accounts:favourites"))
        self.assertTrue(
            Favourite.objects.filter(student=self.student, property=self.property).exists()
        )

        # View favourites page
        fav_response = self.client.get(reverse("accounts:favourites"))
        self.assertEqual(fav_response.status_code, 200)
        self.assertContains(fav_response, "Sunrise Boys PG")

        # Unsave favourite
        response_remove = self.client.post(
            reverse("properties:favourite", args=[self.property.slug]),
            {"next": reverse("accounts:favourites")},
        )
        self.assertRedirects(response_remove, reverse("accounts:favourites"))
        self.assertFalse(
            Favourite.objects.filter(student=self.student, property=self.property).exists()
        )

    def test_submit_and_view_enquiry_status(self):
        enquiry_payload = {
            "message": "Is single occupancy room available from next month?",
            "contact_number": "9876543210",
        }
        response = self.client.post(
            reverse("enquiries:create", args=[self.property.slug]),
            enquiry_payload,
        )
        self.assertRedirects(
            response,
            f"{self.property.get_absolute_url()}#enquiry",
        )

        enquiry = Enquiry.objects.get(student=self.student, property=self.property)
        self.assertEqual(enquiry.status, Enquiry.Status.PENDING)

        # View student enquiries list
        list_response = self.client.get(reverse("enquiries:student_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Sunrise Boys PG")
        self.assertContains(list_response, "Pending")
        self.assertContains(list_response, "Is single occupancy room available")


class PropertyOwnerProfileAndManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="property_boss",
            email="boss@example.com",
            password="Password123!",
            full_name="Ramesh Verma",
            mobile_number="9876543299",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="enquiring_student",
            email="enquiry.student@example.com",
            password="Password123!",
            full_name="Enquiring Student",
            mobile_number="9876543288",
            role=User.Role.STUDENT,
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def test_create_and_update_owner_profile(self):
        response = self.client.get(reverse("accounts:owner_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Business profile")

        post_data = {
            "owner_name": "Ramesh Kumar Verma",
            "contact_number": "9876543299",
            "business_name": "Verma Living Spaces",
            "address": "45 Civil Lines",
            "city": "Prayagraj",
        }
        save_response = self.client.post(reverse("accounts:owner_profile"), post_data)
        self.assertRedirects(save_response, reverse("accounts:owner_profile"))

        profile = OwnerProfile.objects.get(user=self.owner)
        self.assertEqual(profile.business_name, "Verma Living Spaces")
        self.assertEqual(profile.city, "Prayagraj")
        self.assertEqual(profile.address, "45 Civil Lines")

        # Sync check on User model
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.full_name, "Ramesh Kumar Verma")

    def test_owner_manage_properties(self):
        # 1. Add property
        create_payload = {
            "name": "Green Meadows Hostel",
            "property_type": Property.PropertyType.HOSTEL,
            "description": "Spacious student hostel with Wi-Fi and mess.",
            "city": "Prayagraj",
            "address": "12 University Road",
            "landmark": "Near Central Library",
            "monthly_rent": 7000,
            "deposit": "1 Month",
            "contact_number": "9876543299",
            "facilities": "Wi-Fi, Meals, Laundry",
            "is_active": True,
            "is_approved": True,
        }
        create_resp = self.client.post(reverse("properties:create"), create_payload)
        self.assertRedirects(create_resp, reverse("properties:owner_list"))

        property_obj = Property.objects.get(name="Green Meadows Hostel")
        self.assertEqual(property_obj.owner, self.owner)
        self.assertEqual(property_obj.city, "Prayagraj")

        # 2. View owner property list
        list_resp = self.client.get(reverse("properties:owner_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "Green Meadows Hostel")

        # 3. Edit property
        edit_payload = {
            **create_payload,
            "monthly_rent": 7500,
            "landmark": "Opposite Law Faculty",
        }
        edit_resp = self.client.post(
            reverse("properties:edit", args=[property_obj.slug]),
            edit_payload,
        )
        self.assertRedirects(edit_resp, reverse("properties:owner_list"))
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.monthly_rent, 7500)
        self.assertEqual(property_obj.landmark, "Opposite Law Faculty")

        # 4. Delete property
        del_resp = self.client.post(reverse("properties:delete", args=[property_obj.slug]))
        self.assertRedirects(del_resp, reverse("properties:owner_list"))
        self.assertFalse(Property.objects.filter(pk=property_obj.pk).exists())

    def test_owner_view_and_update_student_enquiries(self):
        prop = Property.objects.create(
            owner=self.owner,
            name="Verma Residency",
            property_type=Property.PropertyType.ROOM,
            description="Quiet room for study.",
            city="Prayagraj",
            address="7 Tagore Town",
            monthly_rent=5000,
            contact_number="9876543299",
            is_active=True,
            is_approved=True,
        )
        enquiry = Enquiry.objects.create(
            property=prop,
            student=self.student,
            message="Do you provide food?",
            contact_number="9876543288",
            status=Enquiry.Status.PENDING,
        )

        # View owner enquiries list
        list_resp = self.client.get(reverse("enquiries:owner_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "Verma Residency")
        self.assertContains(list_resp, "Enquiring Student")
        self.assertContains(list_resp, "Do you provide food?")

        # Update enquiry status to Contacted
        update_resp = self.client.post(
            reverse("enquiries:update_status", args=[enquiry.pk]),
            {"status": Enquiry.Status.CONTACTED},
        )
        self.assertRedirects(update_resp, reverse("enquiries:owner_list"))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, Enquiry.Status.CONTACTED)


class PermissionRestrictionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = get_user_model().objects.create_user(
            username="perm_student",
            email="perm_student@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        cls.owner_a = get_user_model().objects.create_user(
            username="perm_owner_a",
            email="perm_owner_a@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.owner_b = get_user_model().objects.create_user(
            username="perm_owner_b",
            email="perm_owner_b@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.property_a = Property.objects.create(
            owner=cls.owner_a,
            name="Owner A Hostel",
            property_type=Property.PropertyType.HOSTEL,
            description="Hostel owned by Owner A.",
            city="Kota",
            address="Address A",
            monthly_rent=6000,
            contact_number="9876543201",
            is_active=True,
            is_approved=True,
        )
        cls.enquiry_a = Enquiry.objects.create(
            property=cls.property_a,
            student=cls.student,
            message="Question for Owner A",
            contact_number="9876543200",
        )

    def test_student_cannot_create_or_edit_properties(self):
        self.client.force_login(self.student)

        # Cannot access create property
        create_resp = self.client.get(reverse("properties:create"))
        self.assertEqual(create_resp.status_code, 403)

        # Cannot post to create property
        create_post_resp = self.client.post(
            reverse("properties:create"),
            {"name": "Student Illegal Property"},
        )
        self.assertEqual(create_post_resp.status_code, 403)

        # Cannot access edit property
        edit_resp = self.client.get(
            reverse("properties:edit", args=[self.property_a.slug])
        )
        self.assertEqual(edit_resp.status_code, 403)

        # Cannot delete property
        del_resp = self.client.post(
            reverse("properties:delete", args=[self.property_a.slug])
        )
        self.assertEqual(del_resp.status_code, 403)

        # Cannot access owner property list
        list_resp = self.client.get(reverse("properties:owner_list"))
        self.assertEqual(list_resp.status_code, 403)

    def test_student_cannot_access_owner_enquiries_or_profile(self):
        self.client.force_login(self.student)

        owner_profile_resp = self.client.get(reverse("accounts:owner_profile"))
        self.assertEqual(owner_profile_resp.status_code, 403)

        owner_enquiry_resp = self.client.get(reverse("enquiries:owner_list"))
        self.assertEqual(owner_enquiry_resp.status_code, 403)

        update_enquiry_resp = self.client.post(
            reverse("enquiries:update_status", args=[self.enquiry_a.pk]),
            {"status": Enquiry.Status.CONTACTED},
        )
        self.assertEqual(update_enquiry_resp.status_code, 403)

    def test_owner_cannot_access_student_profile_or_favourites(self):
        self.client.force_login(self.owner_a)

        student_profile_resp = self.client.get(reverse("accounts:profile"))
        self.assertEqual(student_profile_resp.status_code, 403)

        student_favs_resp = self.client.get(reverse("accounts:favourites"))
        self.assertEqual(student_favs_resp.status_code, 403)

        student_enquiries_resp = self.client.get(reverse("enquiries:student_list"))
        self.assertEqual(student_enquiries_resp.status_code, 403)

    def test_owner_can_only_manage_their_own_properties(self):
        # Owner B attempts to edit or delete Owner A's property
        self.client.force_login(self.owner_b)

        edit_resp = self.client.get(
            reverse("properties:edit", args=[self.property_a.slug])
        )
        self.assertEqual(edit_resp.status_code, 403)

        edit_post_resp = self.client.post(
            reverse("properties:edit", args=[self.property_a.slug]),
            {"name": "Hijacked Property"},
        )
        self.assertEqual(edit_post_resp.status_code, 403)

        del_resp = self.client.post(
            reverse("properties:delete", args=[self.property_a.slug])
        )
        self.assertEqual(del_resp.status_code, 403)
        self.assertTrue(Property.objects.filter(pk=self.property_a.pk).exists())

    def test_owner_can_only_manage_their_own_enquiries(self):
        # Owner B attempts to update enquiry on Owner A's property
        self.client.force_login(self.owner_b)

        update_resp = self.client.post(
            reverse("enquiries:update_status", args=[self.enquiry_a.pk]),
            {"status": Enquiry.Status.CONTACTED},
        )
        self.assertEqual(update_resp.status_code, 403)

        self.enquiry_a.refresh_from_db()
        self.assertEqual(self.enquiry_a.status, Enquiry.Status.PENDING)

    def test_unauthenticated_user_can_browse_public_listings(self):
        list_resp = self.client.get(reverse("properties:list"))
        self.assertEqual(list_resp.status_code, 200)

        detail_resp = self.client.get(
            reverse("properties:detail", args=[self.property_a.slug])
        )
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Owner A Hostel")

    def test_admin_can_access_django_admin_and_user_changelist(self):
        admin = get_user_model().objects.create_superuser(
            username="sys_admin",
            email="sys_admin@example.com",
            password="AdminPassword123!",
        )
        self.client.force_login(admin)

        index_resp = self.client.get(reverse("admin:index"))
        self.assertEqual(index_resp.status_code, 200)

        user_changelist_resp = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(user_changelist_resp.status_code, 200)
        self.assertContains(user_changelist_resp, "sys_admin")
