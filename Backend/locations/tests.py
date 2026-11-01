"""Comprehensive unit and integration tests for location-based search, Haversine formula,
Nominatim geocoding, Overpass nearby places, and nearby accommodation discovery.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from locations.models import Landmark, PlaceCache
from locations.services.distance import (
    find_nearby_properties,
    format_distance,
    haversine_distance,
)
from locations.services.geocoding import (
    geocode_location,
    get_landmark_suggestions,
    reverse_geocode,
)
from locations.services.overpass import get_nearby_places
from properties.forms import PropertyForm
from properties.models import Property, Room


class HaversineDistanceTests(TestCase):
    def test_haversine_known_coordinates(self):
        # Distance between Civil Lines Prayagraj (25.4526, 81.8349) and
        # Allahabad University (25.4593, 81.8601) is approximately 2.6 km
        dist = haversine_distance(25.4526, 81.8349, 25.4593, 81.8601)
        self.assertAlmostEqual(dist, 2.64, delta=0.2)

    def test_haversine_same_point_is_zero(self):
        dist = haversine_distance(25.1388, 75.8454, 25.1388, 75.8454)
        self.assertEqual(dist, 0.0)

    def test_haversine_invalid_coordinates_handled_gracefully(self):
        dist = haversine_distance("invalid", None, 25.0, 75.0)
        self.assertEqual(dist, 0.0)

    def test_format_distance(self):
        self.assertEqual(format_distance(0.35), "350 m")
        self.assertEqual(format_distance(0.08), "80 m")
        self.assertEqual(format_distance(1.0), "1.0 km")
        self.assertEqual(format_distance(2.45), "2.5 km")
        self.assertEqual(format_distance(10.2), "10.2 km")


class GeocodingServiceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_curated_coaching_hub_geocoding(self):
        result = geocode_location("Allen Career Institute, Kota")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "Kota")
        self.assertAlmostEqual(result["latitude"], 25.1388, places=3)
        self.assertAlmostEqual(result["longitude"], 75.8454, places=3)

    def test_curated_railway_station_geocoding(self):
        result = geocode_location("Prayagraj Junction")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "Prayagraj")
        self.assertAlmostEqual(result["latitude"], 25.4484, places=3)

    def test_database_landmark_geocoding(self):
        Landmark.objects.create(
            name="Motion IIT-JEE Academy",
            city="Kota",
            state="Rajasthan",
            category=Landmark.Category.COACHING,
            latitude=Decimal("25.139500"),
            longitude=Decimal("75.844000"),
            aliases="motion, motion kota, motion academy",
        )
        result = geocode_location("Motion IIT-JEE Academy")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Motion IIT-JEE Academy")
        self.assertAlmostEqual(result["latitude"], 25.1395, places=3)

    def test_city_fallback_geocoding(self):
        result = geocode_location("Unknown street, Kota")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "Kota")
        self.assertAlmostEqual(result["latitude"], 25.18, places=1)

    def test_landmark_autocomplete_suggestions(self):
        suggestions = get_landmark_suggestions("Kota")
        self.assertGreater(len(suggestions), 0)
        names = [s["name"] for s in suggestions]
        self.assertTrue(any("Kota" in n for n in names))


class OverpassNearbyPlacesTests(TestCase):
    def setUp(self):
        cache.clear()
        Landmark.objects.create(
            name="Allen Sangyan Campus",
            city="Kota",
            state="Rajasthan",
            category=Landmark.Category.COACHING,
            latitude=Decimal("25.138500"),
            longitude=Decimal("75.845000"),
        )
        Landmark.objects.create(
            name="Kota City Mall",
            city="Kota",
            state="Rajasthan",
            category=Landmark.Category.MARKET,
            latitude=Decimal("25.148000"),
            longitude=Decimal("75.847500"),
        )

    def test_fallback_places_from_database(self):
        data = get_nearby_places(25.1388, 75.8454, radius_meters=3000)
        self.assertIn("all", data)
        self.assertIn("by_category", data)
        self.assertGreater(data["count"], 0)
        names = [p["name"] for p in data["all"]]
        self.assertIn("Allen Sangyan Campus", names)

    @patch("urllib.request.urlopen")
    def test_overpass_response_parsing(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = (
            b'{"elements": ['
            b'  {"type": "node", "id": 1, "lat": 25.140, "lon": 75.846, "tags": {"name": "Career Point Academy", "amenity": "prep_school"}},'
            b'  {"type": "node", "id": 2, "lat": 25.145, "lon": 75.850, "tags": {"name": "City Hospital", "amenity": "hospital"}}'
            b']}'
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = get_nearby_places(25.1388, 75.8454, radius_meters=2000)
        self.assertEqual(data["count"], 2)
        names = [p["name"] for p in data["all"]]
        self.assertIn("Career Point Academy", names)
        self.assertIn("City Hospital", names)


class NearbyDiscoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="owner_geo",
            email="owner_geo@example.com",
            password="Password123!",
            role=User.Role.OWNER,
        )

        # Property 1: Right next to Allen Kota (0.15 km)
        cls.prop_near = Property.objects.create(
            owner=cls.owner,
            name="Allen Proximity PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.BOYS,
            city="Kota",
            address="Rajeev Gandhi Nagar",
            latitude=Decimal("25.139800"),
            longitude=Decimal("75.846000"),
            monthly_rent=6000,
            contact_number="9876543210",
            facilities="Wi-Fi, Food/Mess, AC",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.prop_near,
            room_type="Deluxe AC",
            occupancy=Room.Occupancy.SINGLE,
            monthly_rent=6000,
            air_conditioning=Room.AirConditioning.AC,
            bathroom_type=Room.BathroomType.ATTACHED,
            total_beds=5,
            available_beds=3,
            is_available=True,
        )

        # Property 2: 3.5 km away in Kota
        cls.prop_mid = Property.objects.create(
            owner=cls.owner,
            name="Mid-Distance Hostel",
            property_type=Property.PropertyType.STUDENT_HOSTEL,
            gender_preference=Property.GenderPreference.GIRLS,
            city="Kota",
            address="DCM Road",
            latitude=Decimal("25.170000"),
            longitude=Decimal("75.850000"),
            monthly_rent=4500,
            contact_number="9876543211",
            facilities="Wi-Fi, Laundry",
            is_active=True,
            is_approved=True,
        )
        Room.objects.create(
            property=cls.prop_mid,
            room_type="Double Non-AC",
            occupancy=Room.Occupancy.DOUBLE,
            monthly_rent=4500,
            air_conditioning=Room.AirConditioning.NON_AC,
            bathroom_type=Room.BathroomType.COMMON,
            total_beds=10,
            available_beds=4,
            is_available=True,
        )

        # Property 3: In Prayagraj (different city, ~450 km away)
        cls.prop_far = Property.objects.create(
            owner=cls.owner,
            name="Sangam Boys PG",
            property_type=Property.PropertyType.PG,
            gender_preference=Property.GenderPreference.BOYS,
            city="Prayagraj",
            address="Civil Lines",
            latitude=Decimal("25.452600"),
            longitude=Decimal("81.834900"),
            monthly_rent=5000,
            contact_number="9876543212",
            is_active=True,
            is_approved=True,
        )

    def test_find_nearby_radius_500m(self):
        # Target: Allen Kota (25.1388, 75.8454)
        results = find_nearby_properties(25.1388, 75.8454, max_radius_km=0.5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.prop_near.id)
        self.assertLess(results[0].distance_km, 0.5)

    def test_find_nearby_radius_5km(self):
        results = find_nearby_properties(25.1388, 75.8454, max_radius_km=5.0)
        self.assertEqual(len(results), 2)
        # Verify nearest sorting
        self.assertEqual(results[0].id, self.prop_near.id)
        self.assertEqual(results[1].id, self.prop_mid.id)

    def test_filter_by_gender(self):
        results = find_nearby_properties(
            25.1388, 75.8454, max_radius_km=5.0, filters={"gender": "girls"}
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.prop_mid.id)

    def test_filter_by_sharing_and_ac(self):
        results = find_nearby_properties(
            25.1388, 75.8454, max_radius_km=5.0, filters={"sharing": "single", "ac": "ac"}
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, self.prop_near.id)

    def test_sort_by_lowest_rent(self):
        results = find_nearby_properties(
            25.1388, 75.8454, max_radius_km=5.0, sort_by="rent_asc"
        )
        self.assertEqual(len(results), 2)
        # 4500 comes before 6000
        self.assertEqual(results[0].id, self.prop_mid.id)
        self.assertEqual(results[1].id, self.prop_near.id)


class LocationAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_api_geocode(self):
        res = self.client.get(reverse("locations:api_geocode"), {"q": "Allen Career Institute, Kota"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("latitude", data["result"])
        self.assertIn("longitude", data["result"])

    def test_api_suggest(self):
        res = self.client.get(reverse("locations:api_suggest"), {"q": "Prayagraj"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIsInstance(data["suggestions"], list)

    def test_api_nearby_places(self):
        res = self.client.get(
            reverse("locations:api_nearby_places"),
            {"lat": "25.1388", "lng": "75.8454", "radius": "2000"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("all", data["data"])

    def test_api_nearby_properties(self):
        res = self.client.get(
            reverse("locations:api_nearby_properties"),
            {"destination": "Kota", "radius": "10.0"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("properties", data)
        self.assertIn("all_map_markers", data)


class PropertyFormCoordinateValidationTests(TestCase):
    def test_valid_coordinates(self):
        form = PropertyForm(
            data={
                "name": "Validation PG",
                "property_type": "pg",
                "description": "Clean rooms.",
                "city": "Prayagraj",
                "address": "Civil Lines",
                "latitude": "25.435801",
                "longitude": "81.846311",
                "monthly_rent": "5000",
                "contact_number": "9876543210",
                "is_active": True,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["latitude"], Decimal("25.435801"))

    def test_invalid_latitude_out_of_range(self):
        form = PropertyForm(
            data={
                "name": "Invalid PG",
                "property_type": "pg",
                "description": "Clean rooms.",
                "city": "Prayagraj",
                "address": "Civil Lines",
                "latitude": "95.000000",  # > 90
                "longitude": "81.846311",
                "monthly_rent": "5000",
                "contact_number": "9876543210",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("latitude", form.errors)

    def test_invalid_longitude_out_of_range(self):
        form = PropertyForm(
            data={
                "name": "Invalid PG",
                "property_type": "pg",
                "description": "Clean rooms.",
                "city": "Prayagraj",
                "address": "Civil Lines",
                "latitude": "25.000000",
                "longitude": "195.000000",  # > 180
                "monthly_rent": "5000",
                "contact_number": "9876543210",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("longitude", form.errors)
