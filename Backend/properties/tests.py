"""Tests for properties models, views, favourites, and access control."""

from datetime import date
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from properties.models import Favourite, Property, PropertyImage, Room
from properties.forms import RoomForm


class PropertyModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="prop_owner",
            email="prop_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )

    def test_property_creation_and_slug(self):
        prop = Property.objects.create(
            owner=self.owner,
            name="Apex Student Residency",
            property_type=Property.PropertyType.HOSTEL,
            description="Premium student accommodation.",
            city="Kota",
            address="Vigyan Nagar Road",
            monthly_rent=8500,
            contact_number="9876543210",
            facilities="Wi-Fi, AC, Food",
        )
        self.assertEqual(prop.slug, "apex-student-residency")
        self.assertEqual(prop.facilities_list, ["Wi-Fi", "AC", "Food"])
        self.assertTrue(prop.is_publicly_visible)
        self.assertEqual(str(prop), "Apex Student Residency")


class PropertyBrowsingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="hostel_owner",
            email="hostel_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="browsing_student",
            email="browsing_student@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        cls.prop1 = Property.objects.create(
            owner=cls.owner,
            name="Kota Super Stay",
            property_type=Property.PropertyType.PG,
            description="Near top coaching classes.",
            city="Kota",
            address="15 Rajiv Gandhi Nagar",
            landmark="Near Allen",
            monthly_rent=7000,
            available_from=date(2026, 11, 1),
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )
        cls.prop2 = Property.objects.create(
            owner=cls.owner,
            name="Hidden Villa",
            property_type=Property.PropertyType.ROOM,
            description="Currently hidden.",
            city="Kota",
            address="Secret Lane",
            monthly_rent=9000,
            contact_number="9876543210",
            is_active=False,
            is_approved=True,
        )

    def test_unauthenticated_can_browse_listings(self):
        response = self.client.get(reverse("properties:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kota Super Stay")
        self.assertNotContains(response, "Hidden Villa")

    def test_search_by_query_city_and_type(self):
        response = self.client.get(
            reverse("properties:list"),
            {"q": "Allen", "city": "Kota", "type": "pg", "max_rent": "8000"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kota Super Stay")

    def test_unauthenticated_can_view_live_detail(self):
        response = self.client.get(
            reverse("properties:detail", args=[self.prop1.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kota Super Stay")
        self.assertContains(response, "Log in to enquire")

    def test_unauthenticated_cannot_view_hidden_property(self):
        response = self.client.get(
            reverse("properties:detail", args=[self.prop2.slug])
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_can_view_own_hidden_property(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("properties:detail", args=[self.prop2.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hidden Villa")
        self.assertContains(response, "Hidden from public search")


class FavouriteActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="fav_owner",
            email="fav_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="fav_student",
            email="fav_student@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        cls.property = Property.objects.create(
            owner=cls.owner,
            name="Green Fields Hostel",
            property_type=Property.PropertyType.HOSTEL,
            description="Near sports academy.",
            city="Prayagraj",
            address="Civil Lines",
            monthly_rent=6000,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )

    def test_student_can_toggle_favourite(self):
        self.client.force_login(self.student)
        toggle_url = reverse("properties:favourite", args=[self.property.slug])

        # Add to favourites
        resp1 = self.client.post(toggle_url)
        self.assertRedirects(resp1, self.property.get_absolute_url())
        self.assertTrue(
            Favourite.objects.filter(student=self.student, property=self.property).exists()
        )

        # Remove from favourites
        resp2 = self.client.post(toggle_url)
        self.assertRedirects(resp2, self.property.get_absolute_url())
        self.assertFalse(
            Favourite.objects.filter(student=self.student, property=self.property).exists()
        )

    def test_unauthenticated_cannot_favourite(self):
        toggle_url = reverse("properties:favourite", args=[self.property.slug])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_owner_cannot_favourite(self):
        self.client.force_login(self.owner)
        toggle_url = reverse("properties:favourite", args=[self.property.slug])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, 403)


class PropertyImageAndManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="upload_owner",
            email="upload_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="list_student",
            email="list_student@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )

    def _create_sample_image(self):
        image = Image.new("RGB", (100, 100), color="blue")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        return SimpleUploadedFile("test_hostel.jpg", buffer.getvalue(), content_type="image/jpeg")

    def test_owner_can_create_property_with_image(self):
        self.client.force_login(self.owner)
        img = self._create_sample_image()
        response = self.client.post(
            reverse("properties:create"),
            {
                "name": "Skyline Premium PG",
                "property_type": "pg",
                "description": "Modern PG with Wi-Fi and food.",
                "city": "Prayagraj",
                "address": "45 Katra Road",
                "landmark": "Near University",
                "monthly_rent": "5500",
                "deposit": "One month",
                "contact_number": "9876543210",
                "facilities": "Wi-Fi, Meals, RO Water",
                "image": img,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        prop = Property.objects.get(slug="skyline-premium-pg")
        self.assertTrue(bool(prop.image))
        self.assertIn("properties/", prop.image.name)

    def test_property_list_renders_favourite_button_for_student(self):
        prop = Property.objects.create(
            owner=self.owner,
            name="Campus View PG",
            property_type=Property.PropertyType.PG,
            description="Near campus.",
            city="Kota",
            address="Vigyan Nagar",
            monthly_rent=7000,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )
        Favourite.objects.create(student=self.student, property=prop)

        self.client.force_login(self.student)
        response = self.client.get(reverse("properties:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus View PG")
        self.assertContains(response, "Remove from saved")


class RoomManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner1 = get_user_model().objects.create_user(
            username="owner_one",
            email="owner_one@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.owner2 = get_user_model().objects.create_user(
            username="owner_two",
            email="owner_two@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="student_user",
            email="student_user@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )
        cls.prop = Property.objects.create(
            owner=cls.owner1,
            name="Ganga Residency",
            property_type=Property.PropertyType.PG,
            description="Premium accommodation in Civil Lines.",
            city="Prayagraj",
            address="15 Lowther Road",
            monthly_rent=6000,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )

    def test_owner_can_add_room_configuration(self):
        self.client.force_login(self.owner1)
        response = self.client.post(
            reverse("properties:room_list", args=[self.prop.slug]),
            {
                "room_type": "Deluxe AC Single",
                "occupancy": Room.Occupancy.SINGLE,
                "monthly_rent": 7500,
                "security_deposit": 7500,
                "total_beds": 10,
                "available_beds": 4,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
                "is_available": True,
            },
        )
        self.assertRedirects(response, reverse("properties:room_list", args=[self.prop.slug]))
        self.assertEqual(self.prop.rooms.count(), 1)
        room = self.prop.rooms.first()
        self.assertEqual(room.room_type, "Deluxe AC Single")
        self.assertEqual(room.monthly_rent, 7500)
        self.assertEqual(room.available_beds, 4)

    def test_room_bed_validation_available_cannot_exceed_total(self):
        form = RoomForm(
            data={
                "room_type": "Double Sharing",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 5000,
                "total_beds": 2,
                "available_beds": 5,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
                "is_available": True,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("available_beds", form.errors)
        self.assertIn("Available beds cannot exceed total beds", form.errors["available_beds"][0])

    def test_owner_can_edit_room(self):
        self.client.force_login(self.owner1)
        room = Room.objects.create(
            property=self.prop,
            room_type="Standard Double",
            occupancy=Room.Occupancy.DOUBLE,
            monthly_rent=5000,
            total_beds=4,
            available_beds=2,
            bathroom_type=Room.BathroomType.COMMON,
            air_conditioning=Room.AirConditioning.NON_AC,
        )
        response = self.client.post(
            reverse("properties:room_edit", args=[self.prop.slug, room.pk]),
            {
                "room_type": "Renovated AC Double",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 5800,
                "security_deposit": 5000,
                "total_beds": 4,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
                "is_available": True,
            },
        )
        self.assertRedirects(response, reverse("properties:room_list", args=[self.prop.slug]))
        room.refresh_from_db()
        self.assertEqual(room.room_type, "Renovated AC Double")
        self.assertEqual(room.monthly_rent, 5800)
        self.assertEqual(room.available_beds, 1)

    def test_owner_can_quick_update_room_beds_and_rent(self):
        self.client.force_login(self.owner1)
        room = Room.objects.create(
            property=self.prop,
            room_type="Triple Sharing",
            occupancy=Room.Occupancy.TRIPLE,
            monthly_rent=4000,
            total_beds=6,
            available_beds=3,
        )
        response = self.client.post(
            reverse("properties:room_update_beds", args=[self.prop.slug, room.pk]),
            {
                "available_beds": 0,
                "monthly_rent": 4200,
            },
        )
        self.assertRedirects(response, reverse("properties:room_list", args=[self.prop.slug]))
        room.refresh_from_db()
        self.assertEqual(room.available_beds, 0)
        self.assertEqual(room.monthly_rent, 4200)

    def test_owner_can_delete_room(self):
        self.client.force_login(self.owner1)
        room = Room.objects.create(
            property=self.prop,
            room_type="Single Room",
            occupancy=Room.Occupancy.SINGLE,
            monthly_rent=6000,
            total_beds=1,
            available_beds=1,
        )
        response = self.client.post(
            reverse("properties:room_delete", args=[self.prop.slug, room.pk])
        )
        self.assertRedirects(response, reverse("properties:room_list", args=[self.prop.slug]))
        self.assertFalse(Room.objects.filter(pk=room.pk).exists())

    def test_cross_owner_and_student_forbidden_from_managing_rooms(self):
        room = Room.objects.create(
            property=self.prop,
            room_type="Private Room",
            occupancy=Room.Occupancy.SINGLE,
            monthly_rent=7000,
            total_beds=2,
            available_beds=1,
        )

        # Other owner forbidden
        self.client.force_login(self.owner2)
        resp1 = self.client.get(reverse("properties:room_list", args=[self.prop.slug]))
        self.assertEqual(resp1.status_code, 403)
        resp2 = self.client.post(
            reverse("properties:room_delete", args=[self.prop.slug, room.pk])
        )
        self.assertEqual(resp2.status_code, 403)

        # Student forbidden
        self.client.force_login(self.student)
        resp3 = self.client.get(reverse("properties:room_list", args=[self.prop.slug]))
        self.assertEqual(resp3.status_code, 403)


class GalleryManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="gallery_owner",
            email="gallery_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.prop = Property.objects.create(
            owner=cls.owner,
            name="Sunrise Coliving",
            property_type=Property.PropertyType.COLIVING,
            description="Modern co-living space.",
            city="Kota",
            address="Landmark City",
            monthly_rent=9000,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )

    def _sample_image(self, name="room.jpg"):
        image = Image.new("RGB", (80, 80), color="green")
        buf = BytesIO()
        image.save(buf, format="JPEG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")

    def test_owner_can_upload_gallery_image(self):
        self.client.force_login(self.owner)
        img = self._sample_image("bedroom_1.jpg")
        response = self.client.post(
            reverse("properties:gallery_manage", args=[self.prop.slug]),
            {
                "category": PropertyImage.Category.BEDROOM,
                "caption": "Spacious student bedroom with desk",
                "image": img,
            },
        )
        self.assertRedirects(response, reverse("properties:gallery_manage", args=[self.prop.slug]))
        self.assertEqual(self.prop.images.count(), 1)
        saved = self.prop.images.first()
        self.assertEqual(saved.category, PropertyImage.Category.BEDROOM)
        self.assertEqual(saved.caption, "Spacious student bedroom with desk")

    def test_set_primary_image_and_auto_reset(self):
        self.client.force_login(self.owner)
        img1 = PropertyImage.objects.create(
            property=self.prop,
            image=self._sample_image("img1.jpg"),
            category=PropertyImage.Category.EXTERIOR,
            is_primary=True,
        )
        img2 = PropertyImage.objects.create(
            property=self.prop,
            image=self._sample_image("img2.jpg"),
            category=PropertyImage.Category.BEDROOM,
            is_primary=False,
        )
        # Set img2 as primary
        response = self.client.post(
            reverse("properties:gallery_set_primary", args=[self.prop.slug, img2.pk])
        )
        self.assertRedirects(response, reverse("properties:gallery_manage", args=[self.prop.slug]))
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)

    def test_delete_gallery_image(self):
        self.client.force_login(self.owner)
        img = PropertyImage.objects.create(
            property=self.prop,
            image=self._sample_image("to_delete.jpg"),
            category=PropertyImage.Category.KITCHEN,
        )
        response = self.client.post(
            reverse("properties:gallery_delete", args=[self.prop.slug, img.pk])
        )
        self.assertRedirects(response, reverse("properties:gallery_manage", args=[self.prop.slug]))
        self.assertFalse(PropertyImage.objects.filter(pk=img.pk).exists())


class PropertyWorkflowAndFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="workflow_owner",
            email="workflow_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.prop_boys = Property.objects.create(
            owner=cls.owner,
            name="Shree Ram Boys PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.BOYS,
            description="Near coaching institutes.",
            city="Kota",
            address="Vigyan Nagar",
            monthly_rent=6500,
            contact_number="9876543210",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.prop_boys,
            room_type="Single Room",
            occupancy=Room.Occupancy.SINGLE,
            monthly_rent=6500,
            total_beds=5,
            available_beds=2,
        )
        cls.prop_girls = Property.objects.create(
            owner=cls.owner,
            name="Saraswati Girls Hostel",
            property_type=Property.PropertyType.STUDENT_HOSTEL,
            gender_preference=Property.GenderPreference.GIRLS,
            description="Secure student hostel for girls.",
            city="Kota",
            address="Indra Vihar",
            monthly_rent=8000,
            contact_number="9876543211",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.prop_girls,
            room_type="Double Sharing",
            occupancy=Room.Occupancy.DOUBLE,
            monthly_rent=8000,
            total_beds=10,
            available_beds=4,
        )

    def test_owner_can_toggle_active_status(self):
        self.client.force_login(self.owner)
        toggle_url = reverse("properties:toggle_active", args=[self.prop_boys.slug])

        # Deactivate
        resp1 = self.client.post(toggle_url)
        self.assertRedirects(resp1, reverse("properties:owner_list"))
        self.prop_boys.refresh_from_db()
        self.assertFalse(self.prop_boys.is_active)

        # Reactivate
        resp2 = self.client.post(toggle_url)
        self.assertRedirects(resp2, reverse("properties:owner_list"))
        self.prop_boys.refresh_from_db()
        self.assertTrue(self.prop_boys.is_active)

    def test_filter_by_gender_preference(self):
        response_boys = self.client.get(reverse("properties:list"), {"gender": "boys"})
        self.assertEqual(response_boys.status_code, 200)
        self.assertContains(response_boys, "Shree Ram Boys PG")
        self.assertNotContains(response_boys, "Saraswati Girls Hostel")

        response_girls = self.client.get(reverse("properties:list"), {"gender": "girls"})
        self.assertEqual(response_girls.status_code, 200)
        self.assertContains(response_girls, "Saraswati Girls Hostel")
        self.assertNotContains(response_girls, "Shree Ram Boys PG")

    def test_filter_by_category_and_occupancy(self):
        # Filter by student hostel category
        response_cat = self.client.get(reverse("properties:list"), {"type": "student_hostel"})
        self.assertEqual(response_cat.status_code, 200)
        self.assertContains(response_cat, "Saraswati Girls Hostel")
        self.assertNotContains(response_cat, "Shree Ram Boys PG")

        # Filter by occupancy
        response_occ = self.client.get(reverse("properties:list"), {"occupancy": "single"})
        self.assertEqual(response_occ.status_code, 200)
        self.assertContains(response_occ, "Shree Ram Boys PG")


class ExplorePGsAndAdvancedSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="adv_search_owner",
            email="adv_owner@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )
        cls.student = get_user_model().objects.create_user(
            username="adv_search_student",
            email="adv_student@example.com",
            password="Password123!",
            role=User.Role.STUDENT,
        )

        # 1. Budget Boys PG with food & wifi
        cls.pg_boys = Property.objects.create(
            owner=cls.owner,
            name="Ganga Boys PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.BOYS,
            description="Budget PG with food and wifi near coaching.",
            city="Kota",
            address="15 Rajeev Gandhi Nagar",
            locality="Rajeev Gandhi Nagar",
            landmark="Allen Kota",
            latitude=25.1388,
            longitude=75.8454,
            monthly_rent=5500,
            contact_number="9876543201",
            facilities="Food/Mess, Wi-Fi, CCTV, Study Table, Wardrobe",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.pg_boys,
            room_type="Single Room",
            occupancy=Room.Occupancy.SINGLE,
            bathroom_type=Room.BathroomType.ATTACHED,
            air_conditioning=Room.AirConditioning.AC,
            monthly_rent=5500,
            total_beds=4,
            available_beds=2,
            is_available=True,
        )

        # 2. Premium Girls PG with attached bath
        cls.pg_girls = Property.objects.create(
            owner=cls.owner,
            name="Radha Rani Girls PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.GIRLS,
            description="Premium girls PG with attached bathroom and security.",
            city="Prayagraj",
            address="20 Katra Road",
            locality="Katra",
            landmark="Allahabad University",
            latitude=25.4593,
            longitude=81.8601,
            monthly_rent=9000,
            contact_number="9876543202",
            facilities="Wi-Fi, Attached Bathroom, Security, RO Water",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.pg_girls,
            room_type="Double Deluxe",
            occupancy=Room.Occupancy.DOUBLE,
            bathroom_type=Room.BathroomType.ATTACHED,
            air_conditioning=Room.AirConditioning.NON_AC,
            monthly_rent=9000,
            total_beds=6,
            available_beds=0,  # Full
            is_available=True,
        )

        # 3. Co-living space
        cls.coliving = Property.objects.create(
            owner=cls.owner,
            name="Zenith Co-living Stays",
            property_type=Property.PropertyType.COLIVING,
            gender_preference=Property.GenderPreference.UNISEX,
            description="Modern co-living space with mess and high speed internet.",
            city="Delhi",
            address="12 Mukherjee Nagar",
            locality="Mukherjee Nagar",
            latitude=28.7107,
            longitude=77.2144,
            monthly_rent=12000,
            contact_number="9876543203",
            facilities="Wi-Fi, Food/Mess, Air Conditioning, Furnished",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.coliving,
            room_type="Studio Suite",
            occupancy=Room.Occupancy.SINGLE,
            bathroom_type=Room.BathroomType.ATTACHED,
            air_conditioning=Room.AirConditioning.AC,
            monthly_rent=12000,
            total_beds=2,
            available_beds=2,
            is_available=True,
        )

        # Favourite the coliving stay to give it a popularity score
        Favourite.objects.create(student=cls.student, property=cls.coliving)

    def test_explore_pgs_view_renders_successfully(self):
        resp = self.client.get(reverse("properties:explore_pgs"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "properties/explore_pgs.html")
        self.assertContains(resp, "Explore Verified")
        self.assertContains(resp, "Ganga Boys PG")
        self.assertContains(resp, "Radha Rani Girls PG")

    def test_explore_pgs_root_alias(self):
        resp = self.client.get("/explore-pgs/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "properties/explore_pgs.html")

    def test_api_search_endpoint_returns_json(self):
        resp = self.client.get(reverse("properties:api_search"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("properties", data)
        self.assertIn("total_count", data)
        self.assertGreaterEqual(data["total_count"], 3)

    def test_api_search_filter_by_rent_range(self):
        # Filter min_rent 5000, max_rent 7000 (should only match Ganga Boys PG at 5500)
        resp = self.client.get(reverse("properties:api_search"), {
            "min_rent": "5000",
            "max_rent": "7000",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["properties"]]
        self.assertIn("Ganga Boys PG", names)
        self.assertNotIn("Radha Rani Girls PG", names)
        self.assertNotIn("Zenith Co-living Stays", names)

    def test_api_search_filter_by_food_and_wifi(self):
        resp = self.client.get(reverse("properties:api_search"), {
            "food": "1",
            "wifi": "1",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["properties"]]
        self.assertIn("Ganga Boys PG", names)
        self.assertIn("Zenith Co-living Stays", names)
        self.assertNotIn("Radha Rani Girls PG", names)  # Radha Rani has no Food

    def test_api_search_filter_by_attached_bathroom(self):
        resp = self.client.get(reverse("properties:api_search"), {
            "bathroom": "attached",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["properties"]]
        self.assertIn("Ganga Boys PG", names)
        self.assertIn("Radha Rani Girls PG", names)

    def test_api_search_filter_by_furnished(self):
        # Zenith has explicit "Furnished", Ganga has Study Table + Wardrobe (qualifies as furnished)
        resp = self.client.get(reverse("properties:api_search"), {
            "furnished": "furnished",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["properties"]]
        self.assertIn("Zenith Co-living Stays", names)
        self.assertIn("Ganga Boys PG", names)

    def test_api_search_filter_by_available_only(self):
        # Radha Rani has 0 available beds, Ganga has 2, Zenith has 2
        resp = self.client.get(reverse("properties:api_search"), {
            "available_only": "1",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        names = [p["name"] for p in data["properties"]]
        self.assertIn("Ganga Boys PG", names)
        self.assertIn("Zenith Co-living Stays", names)
        self.assertNotIn("Radha Rani Girls PG", names)

    def test_api_search_sort_by_popular(self):
        # Zenith has 1 favourite, so it should rank first in popular sort
        resp = self.client.get(reverse("properties:api_search"), {
            "sort": "popular",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data["properties"]), 1)
        self.assertEqual(data["properties"][0]["name"], "Zenith Co-living Stays")

    def test_api_search_pagination(self):
        resp = self.client.get(reverse("properties:api_search"), {
            "page": "1",
            "page_size": "2",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["properties"]), 2)
        self.assertEqual(data["page"], 1)
        self.assertTrue(data["has_next"])

