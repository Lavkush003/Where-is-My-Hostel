"""Management command to populate standard demonstration data for Where Is My Hostel.

Creates:
1. Standard demo users:
   - Admin: admin@whereismyhostel.example / AdminPassword123!
   - Owner: owner@whereismyhostel.example / OwnerPassword123!
   - Student: student@whereismyhostel.example / StudentPassword123!
2. Curated educational and transport landmarks across major student cities.
3. Realistic student hostels, PGs, and co-living properties with real room photos.
4. Room configurations (Single, Double, Triple, Four sharing with AC/Non-AC options).
5. Sample student enquiries with varied lifecycle statuses (Pending, Contacted, Accepted).
"""

import os
import shutil
from datetime import date, timedelta
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import OwnerProfile, User
from enquiries.models import Enquiry
from properties.models import Property, PropertyImage, Room


DEMO_USERS = {
    "admin": {
        "email": "admin@whereismyhostel.example",
        "username": "admin",
        "full_name": "Admin Team",
        "password": "AdminPassword123!",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
    },
    "owner": {
        "email": "owner@whereismyhostel.example",
        "username": "ramesh_sharma",
        "full_name": "Ramesh Sharma",
        "password": "OwnerPassword123!",
        "role": User.Role.OWNER,
        "mobile_number": "9876543210",
        "business_name": "Sharma Student Accommodations",
    },
    "student": {
        "email": "student@whereismyhostel.example",
        "username": "priya_patel",
        "full_name": "Priya Patel",
        "password": "StudentPassword123!",
        "role": User.Role.STUDENT,
        "mobile_number": "9123456780",
    },
}

DEMO_PROPERTIES = [
    {
        "name": "Ganga View Boys PG",
        "city": "Prayagraj",
        "state": "Uttar Pradesh",
        "locality": "Civil Lines",
        "address": "42/12 MG Marg, Near Prayagraj Junction, Civil Lines, Prayagraj",
        "pincode": "211001",
        "latitude": 25.4526,
        "longitude": 81.8349,
        "property_type": Property.PropertyType.PG,
        "gender_preference": Property.GenderPreference.BOYS,
        "monthly_rent": 4500,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "Wi-Fi, 3 Daily Meals, RO Water, Study Desk, CCTV, Daily Housekeeping, Power Backup",
        "description": "Safe, student-friendly boys PG located in Civil Lines, within walking distance from Prayagraj Junction and coaching institutes. Offers nutritious homestyle food, 24/7 security, and dedicated quiet study areas.",
        "contact_number": "9876543210",
        "seed_image": "room_single_cozy.jpg",
        "rooms": [
            {
                "room_type": "Deluxe Single Room",
                "occupancy": Room.Occupancy.SINGLE,
                "monthly_rent": 6500,
                "security_deposit": 6500,
                "total_beds": 1,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
            {
                "room_type": "Twin Sharing Room",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 4500,
                "security_deposit": 4500,
                "total_beds": 2,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.NON_AC,
            },
            {
                "room_type": "Budget Triple Sharing",
                "occupancy": Room.Occupancy.TRIPLE,
                "monthly_rent": 3800,
                "security_deposit": 3800,
                "total_beds": 3,
                "available_beds": 2,
                "bathroom_type": Room.BathroomType.COMMON,
                "air_conditioning": Room.AirConditioning.NON_AC,
            },
        ],
    },
    {
        "name": "Sunrise Girls Hostel",
        "city": "Kota",
        "state": "Rajasthan",
        "locality": "Rajeev Gandhi Nagar",
        "address": "Plot 88, Electronic Complex Road, Near Allen SAMYAK, Rajeev Gandhi Nagar, Kota",
        "pincode": "324005",
        "latitude": 25.1388,
        "longitude": 75.8456,
        "property_type": Property.PropertyType.STUDENT_HOSTEL,
        "gender_preference": Property.GenderPreference.GIRLS,
        "monthly_rent": 6200,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "Wi-Fi, 4 Daily Meals, Biometric Entry, Female Warden, Air Conditioning, Study Room, Laundry",
        "description": "Premium girls hostel directly opposite Allen coaching campus in Rajeev Gandhi Nagar. Features round-the-clock female warden supervision, biometric entry, hygienic buffet meals, and doctor-on-call.",
        "contact_number": "9876543210",
        "seed_image": "room_twin_sharing.jpg",
        "rooms": [
            {
                "room_type": "Comfort Twin AC",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 6200,
                "security_deposit": 6200,
                "total_beds": 2,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
            {
                "room_type": "Premium Private AC",
                "occupancy": Room.Occupancy.SINGLE,
                "monthly_rent": 9500,
                "security_deposit": 9500,
                "total_beds": 1,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
        ],
    },
    {
        "name": "Scholar's Nest PG",
        "city": "Delhi",
        "state": "Delhi",
        "locality": "Mukherjee Nagar",
        "address": "B-14 Commercial Complex, Near Batra Cinema, Mukherjee Nagar, Delhi",
        "pincode": "110009",
        "latitude": 28.7107,
        "longitude": 77.2144,
        "property_type": Property.PropertyType.COLIVING,
        "gender_preference": Property.GenderPreference.UNISEX,
        "monthly_rent": 7500,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "High-Speed Wi-Fi, 24x7 Silent Library, Power Backup, RO Water, CCTV, Biometric, Meals Available",
        "description": "Co-living space purposefully engineered for UPSC and SSC aspirants in Mukherjee Nagar. Includes soundproof 24-hour reading rooms, high-speed fibre internet, ergonomic chairs, and daily housekeeping.",
        "contact_number": "9876543210",
        "seed_image": "room_student_study.jpg",
        "rooms": [
            {
                "room_type": "Study Double Sharing",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 7500,
                "security_deposit": 7500,
                "total_beds": 2,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
            {
                "room_type": "Solo Aspirant Room",
                "occupancy": Room.Occupancy.SINGLE,
                "monthly_rent": 11000,
                "security_deposit": 11000,
                "total_beds": 1,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
        ],
    },
    {
        "name": "Apex Elite Boys Hostel",
        "city": "Kota",
        "state": "Rajasthan",
        "locality": "Talwandi",
        "address": "Sector A, Near Resonance Head Office, Talwandi, Kota",
        "pincode": "324005",
        "latitude": 25.1480,
        "longitude": 75.8360,
        "property_type": Property.PropertyType.STUDENT_HOSTEL,
        "gender_preference": Property.GenderPreference.BOYS,
        "monthly_rent": 7000,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "Wi-Fi, 4 Daily Meals, AC, Power Backup, Gym, Biometric Security, Laundry Service",
        "description": "Modern boys hostel in Talwandi, situated within 300 metres of Resonance and Allen institutes. Includes full dining hall, recreational area, 24/7 security guard, and study tables in every room.",
        "contact_number": "9876543210",
        "seed_image": "hostel_bunk_dorm.jpg",
        "rooms": [
            {
                "room_type": "Standard Twin Sharing",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 7000,
                "security_deposit": 7000,
                "total_beds": 2,
                "available_beds": 2,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
            {
                "room_type": "Economy Triple Sharing",
                "occupancy": Room.Occupancy.TRIPLE,
                "monthly_rent": 5500,
                "security_deposit": 5500,
                "total_beds": 3,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.NON_AC,
            },
        ],
    },
    {
        "name": "Chanakya Student Hostel",
        "city": "Patna",
        "state": "Bihar",
        "locality": "Boring Road",
        "address": "Near AN College, Boring Road Crossing, Patna",
        "pincode": "800001",
        "latitude": 25.6120,
        "longitude": 85.1200,
        "property_type": Property.PropertyType.PG,
        "gender_preference": Property.GenderPreference.BOYS,
        "monthly_rent": 4200,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "Wi-Fi, Home Meals, Water Purifier, Study Table, CCTV, Generator Backup",
        "description": "Centrally located student accommodation on Boring Road, close to prominent IIT-JEE/NEET coaching centres and colleges. Warm, peaceful environment with balanced meals.",
        "contact_number": "9876543210",
        "seed_image": "room_luxury_attached.jpg",
        "rooms": [
            {
                "room_type": "Double Sharing Room",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 4200,
                "security_deposit": 4200,
                "total_beds": 2,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.NON_AC,
            },
            {
                "room_type": "Single Study Room",
                "occupancy": Room.Occupancy.SINGLE,
                "monthly_rent": 6000,
                "security_deposit": 6000,
                "total_beds": 1,
                "available_beds": 1,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.NON_AC,
            },
        ],
    },
    {
        "name": "Pink City Student PG",
        "city": "Jaipur",
        "state": "Rajasthan",
        "locality": "Gopalpura Bypass",
        "address": "12 Surya Nagar, Near Allen Gopalpura Bypass, Jaipur",
        "pincode": "302018",
        "latitude": 26.8600,
        "longitude": 75.7800,
        "property_type": Property.PropertyType.PG,
        "gender_preference": Property.GenderPreference.UNISEX,
        "monthly_rent": 5500,
        "deposit": "One month rent",
        "available_from": date.today(),
        "facilities": "Wi-Fi, 3 Daily Meals, AC, Power Backup, CCTV, Attached Balcony, Lift",
        "description": "Newly constructed PG for students attending coaching institutes along Gopalpura Bypass. Quiet residential setting with high ventilation, nutritious menu, and fast Wi-Fi.",
        "contact_number": "9876543210",
        "seed_image": "room_single_cozy.jpg",
        "rooms": [
            {
                "room_type": "Twin Sharing AC",
                "occupancy": Room.Occupancy.DOUBLE,
                "monthly_rent": 5500,
                "security_deposit": 5500,
                "total_beds": 2,
                "available_beds": 2,
                "bathroom_type": Room.BathroomType.ATTACHED,
                "air_conditioning": Room.AirConditioning.AC,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed standard development and demonstration data (users, properties, rooms, landmarks, enquiries)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Where Is My Hostel Demo Data..."))

        # 1. Populate standard landmarks
        self.stdout.write("1. Seeding educational & transit landmarks...")
        call_command("seed_landmarks")

        # 2. Populate users
        self.stdout.write("2. Creating demonstration accounts...")
        users = {}
        for role_key, udata in DEMO_USERS.items():
            user, created = User.objects.get_or_create(
                email=udata["email"],
                defaults={
                    "username": udata["username"],
                    "full_name": udata["full_name"],
                    "role": udata["role"],
                    "mobile_number": udata.get("mobile_number", ""),
                    "is_staff": udata.get("is_staff", False),
                    "is_superuser": udata.get("is_superuser", False),
                },
            )
            user.set_password(udata["password"])
            user.full_name = udata["full_name"]
            user.role = udata["role"]
            user.is_staff = udata.get("is_staff", False)
            user.is_superuser = udata.get("is_superuser", False)
            user.save()
            users[role_key] = user

            # Set up owner profile
            if udata["role"] == User.Role.OWNER:
                OwnerProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "owner_name": udata["full_name"],
                        "contact_number": udata.get("mobile_number", ""),
                        "business_name": udata.get("business_name", "Hostel Business"),
                        "city": "Prayagraj",
                    },
                )

            action_str = "Created" if created else "Updated"
            self.stdout.write(f"   [{action_str}] {udata['role'].upper()}: {udata['email']} (Password: {udata['password']})")

        owner = users["owner"]
        student = users["student"]

        # 3. Create properties, rooms, and images
        self.stdout.write("3. Creating sample properties and rooms...")
        source_img_dir = os.path.join(settings.BASE_DIR, "static", "images", "rooms")
        media_gallery_dir = os.path.join(settings.MEDIA_ROOT, "properties", "gallery", "seed")
        os.makedirs(media_gallery_dir, exist_ok=True)

        created_props = []
        for pdata in DEMO_PROPERTIES:
            rooms_data = pdata.pop("rooms")
            seed_img_name = pdata.pop("seed_image")

            prop, p_created = Property.objects.update_or_create(
                name=pdata["name"],
                city=pdata["city"],
                defaults={
                    "owner": owner,
                    "state": pdata["state"],
                    "locality": pdata["locality"],
                    "address": pdata["address"],
                    "pincode": pdata["pincode"],
                    "latitude": pdata["latitude"],
                    "longitude": pdata["longitude"],
                    "property_type": pdata["property_type"],
                    "gender_preference": pdata["gender_preference"],
                    "monthly_rent": pdata["monthly_rent"],
                    "deposit": pdata.get("deposit", "One month rent"),
                    "available_from": pdata["available_from"],
                    "facilities": pdata["facilities"],
                    "description": pdata["description"],
                    "contact_number": pdata["contact_number"],
                    "is_active": True,
                    "is_approved": True,
                    "approval_status": Property.ApprovalStatus.APPROVED,
                    "is_suspended": False,
                },
            )
            created_props.append(prop)

            # Copy room photo into media gallery
            source_img_path = os.path.join(source_img_dir, seed_img_name)
            if os.path.exists(source_img_path):
                dest_path = os.path.join(media_gallery_dir, seed_img_name)
                if not os.path.exists(dest_path):
                    shutil.copyfile(source_img_path, dest_path)

                # Set primary PropertyImage
                if not prop.images.exists():
                    with open(source_img_path, "rb") as f:
                        pimg = PropertyImage(
                            property=prop,
                            category=PropertyImage.Category.BEDROOM,
                            caption="Furnished student bedroom",
                            is_primary=True,
                        )
                        pimg.image.save(seed_img_name, File(f), save=True)

            # Create Room configurations
            for rdata in rooms_data:
                Room.objects.update_or_create(
                    property=prop,
                    room_type=rdata["room_type"],
                    defaults=rdata,
                )

            status_str = "Created" if p_created else "Updated"
            self.stdout.write(f"   [{status_str}] {prop.name} ({prop.city}) - Rent: Rs.{prop.monthly_rent}/mo")

        # 4. Populate sample enquiries
        self.stdout.write("4. Creating sample student enquiries...")
        if len(created_props) >= 3:
            enquiries_spec = [
                {
                    "property": created_props[0],
                    "status": Enquiry.Status.ACCEPTED,
                    "move_in_date": date.today() + timedelta(days=7),
                    "occupancy": Enquiry.OccupancyPreference.DOUBLE,
                    "message": "Hi, I am joining Allen Prayagraj next month. Can I reserve a double sharing room?",
                    "contact_number": student.mobile_number,
                },
                {
                    "property": created_props[1],
                    "status": Enquiry.Status.PENDING,
                    "move_in_date": date.today() + timedelta(days=14),
                    "occupancy": Enquiry.OccupancyPreference.SINGLE,
                    "message": "Looking for a quiet single room with AC. Is meal service included on Sundays?",
                    "contact_number": student.mobile_number,
                },
                {
                    "property": created_props[2],
                    "status": Enquiry.Status.CONTACTED,
                    "move_in_date": date.today() + timedelta(days=3),
                    "occupancy": Enquiry.OccupancyPreference.SINGLE,
                    "message": "Preparing for UPSC 2027. Want to check the library facilities in person tomorrow.",
                    "contact_number": student.mobile_number,
                },
            ]
            for espec in enquiries_spec:
                enq, e_created = Enquiry.objects.update_or_create(
                    student=student,
                    property=espec["property"],
                    defaults={
                        "status": espec["status"],
                        "move_in_date": espec["move_in_date"],
                        "occupancy": espec["occupancy"],
                        "message": espec["message"],
                        "contact_number": espec["contact_number"],
                    },
                )
                action_str = "Created" if e_created else "Updated"
                self.stdout.write(f"   [{action_str}] Enquiry for {enq.property.name} ({enq.get_status_display()})")

        self.stdout.write(self.style.SUCCESS("\nDemo data seeding completed successfully!"))
        self.stdout.write(
            """
Demonstration Login Credentials:
-----------------------------------------------------------
Admin:   admin@whereismyhostel.example   | AdminPassword123!
Owner:   owner@whereismyhostel.example   | OwnerPassword123!
Student: student@whereismyhostel.example | StudentPassword123!
-----------------------------------------------------------
"""
        )
