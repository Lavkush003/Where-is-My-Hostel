from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse


class CorePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find Your Perfect Stay Near Your")
        self.assertContains(
            response,
            "Discover affordable PGs, hostels and rental rooms near your coaching centre, college or favourite location.",
        )
        self.assertContains(response, "Demo content")
        self.assertContains(response, "Ganga View Boys PG")
        self.assertContains(response, "Prayagraj")
        self.assertContains(response, "Hyderabad")
        self.assertContains(response, "Boys PG")
        self.assertContains(response, "city-prayagraj")

    def test_about_page_renders(self):
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.status_code, 200)

    def test_contact_page_renders(self):
        response = self.client.get(reverse("core:contact"))
        self.assertEqual(response.status_code, 200)

    def test_privacy_page_renders(self):
        response = self.client.get(reverse("core:privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy Policy")
        self.assertContains(response, "Sample listings")

    def test_terms_page_renders(self):
        response = self.client.get(reverse("core:terms"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Terms of Use")
        self.assertContains(response, "Sample and demo content")

    def test_health_endpoint(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_frontend_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find("css/tailwind.css"))
        self.assertIsNotNone(finders.find("js/main.js"))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_custom_404_page(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "We could not find that page", status_code=404)


class PropertyPlaceholderTests(TestCase):
    def test_property_list_page_accepts_search_parameters(self):
        response = self.client.get(
            reverse("properties:list"), {"q": "Kota", "city": "Kota"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Listings are being onboarded")
        self.assertContains(response, "Kota")

    def test_property_list_page_accepts_extended_search_parameters(self):
        response = self.client.get(
            reverse("properties:list"),
            {
                "q": "Civil Lines",
                "city": "Prayagraj",
                "type": "hostel",
                "max_rent": "8000",
                "move_in": "2026-11-15",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hostel")
        self.assertContains(response, "Up to ₹8,000/month")
        self.assertContains(response, "Move-in 2026-11-15")

    def test_sample_property_detail_renders(self):
        response = self.client.get(
            reverse("properties:detail", args=["ganga-view-boys-pg"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ganga View Boys PG")
        self.assertContains(response, "Sample listing preview")
        self.assertContains(response, "₹4,500")

    def test_unknown_sample_property_returns_404(self):
        response = self.client.get(
            reverse("properties:detail", args=["not-a-sample-property"])
        )
        self.assertEqual(response.status_code, 404)


class AuthenticatedNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="student",
            email="student@example.com",
            password="a-secure-test-password",
            is_staff=True,
        )
        self.client.force_login(self.user)

    def test_navbar_shows_profile_menu_for_authenticated_user(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="profile-menu-button"')
        self.assertContains(response, 'id="profile-menu"')
        self.assertContains(response, "student@example.com")
        self.assertContains(response, "Admin panel")
        self.assertContains(response, reverse("accounts:logout"))
