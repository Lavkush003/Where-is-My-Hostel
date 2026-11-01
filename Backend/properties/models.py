"""Models for PGs, hostels, private rooms, room configurations and gallery images."""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

AVAILABLE_FACILITIES = [
    ("Wi-Fi", "Wi-Fi"),
    ("Food/Mess", "Food/Mess"),
    ("Laundry", "Laundry"),
    ("Air Conditioning", "Air Conditioning"),
    ("Study Table", "Study Table"),
    ("Wardrobe", "Wardrobe"),
    ("CCTV", "CCTV"),
    ("Power Backup", "Power Backup"),
    ("RO Water", "RO Water"),
    ("Parking", "Parking"),
    ("Housekeeping", "Housekeeping"),
    ("Attached Bathroom", "Attached Bathroom"),
    ("24/7 Water", "24/7 Water"),
    ("Security", "Security"),
    ("Common Kitchen", "Common Kitchen"),
    ("Furnished", "Furnished"),
    ("Semi-Furnished", "Semi-Furnished"),
]


class Property(models.Model):
    """A property listing managed by a property owner."""

    class PropertyType(models.TextChoices):
        PG = "pg", "PG Accommodation"
        PRIVATE_HOSTEL = "private_hostel", "Private Hostel"
        STUDENT_HOSTEL = "student_hostel", "Student Hostel"
        INDEPENDENT_ROOM = "independent_room", "Independent Room"
        SHARED_ROOM = "shared_room", "Shared Rental Room"
        COLIVING = "coliving", "Co-living Space"
        # Backwards compatibility aliases
        HOSTEL = "hostel", "Hostel"
        ROOM = "room", "Private room"

    class GenderPreference(models.TextChoices):
        BOYS = "boys", "Boys"
        GIRLS = "girls", "Girls"
        UNISEX = "unisex", "Unisex / All"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    property_type = models.CharField(
        max_length=30,
        choices=PropertyType.choices,
        default=PropertyType.PG,
    )
    gender_preference = models.CharField(
        max_length=20,
        choices=GenderPreference.choices,
        default=GenderPreference.UNISEX,
        blank=True,
    )
    description = models.TextField()

    # Address & Location Details
    address = models.CharField(max_length=255)
    locality = models.CharField("locality / area", max_length=150, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Uttar Pradesh", blank=True)
    pincode = models.CharField("PIN code", max_length=10, blank=True)
    landmark = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Base pricing & contact
    monthly_rent = models.PositiveIntegerField(
        default=0,
        help_text="Starting or default monthly rent in ₹ (or minimum room rent).",
    )
    deposit = models.CharField(max_length=120, blank=True)
    available_from = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=16)

    # Facilities (stored comma-separated for fast lookup and backward compatibility)
    facilities = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated facilities.",
    )

    # Main / Hero Image
    image = models.ImageField(
        upload_to="properties/%Y/%m/",
        blank=True,
        help_text="Upload a clear photograph of the hostel or room.",
    )

    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
        default=True,
        help_text="Listing requires administrator approval before becoming publicly visible.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "properties"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:200] or "property"
            slug = base
            suffix = 1
            while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                suffix += 1
                slug = f"{base}-{suffix}"[:220]
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("properties:detail", args=[self.slug])

    @property
    def facilities_list(self):
        return [item.strip() for item in self.facilities.split(",") if item.strip()]

    @property
    def is_publicly_visible(self):
        return self.is_active and self.is_approved

    @property
    def min_monthly_rent(self):
        """Return the lowest active room rent if available, else property monthly_rent."""
        room_rents = self.rooms.filter(is_available=True).values_list(
            "monthly_rent", flat=True
        )
        if room_rents:
            return min(room_rents)
        all_room_rents = self.rooms.values_list("monthly_rent", flat=True)
        if all_room_rents:
            return min(all_room_rents)
        return self.monthly_rent

    @property
    def total_available_beds(self):
        return sum(self.rooms.filter(is_available=True).values_list("available_beds", flat=True))

    @property
    def total_beds_count(self):
        return sum(self.rooms.values_list("total_beds", flat=True))

    @property
    def room_occupancy_labels(self):
        """Return a sorted list of unique occupancy display strings for this property."""
        occupancy_keys = self.rooms.filter(is_available=True).values_list("occupancy", flat=True).distinct()
        mapping = dict(Room.Occupancy.choices)
        return [mapping[key] for key in occupancy_keys if key in mapping]

    @property
    def primary_image_url(self):
        """Return the primary gallery image, hero image, or fallback image."""
        primary_img = self.images.filter(is_primary=True).first()
        if primary_img and primary_img.image:
            return primary_img.image.url
        first_img = self.images.first()
        if first_img and first_img.image:
            return first_img.image.url
        if self.image:
            return self.image.url
        return None


class Room(models.Model):
    """Room configuration and occupancy under a property."""

    class Occupancy(models.TextChoices):
        SINGLE = "single", "Single"
        DOUBLE = "double", "Double"
        TRIPLE = "triple", "Triple"
        FOUR = "four", "Four Sharing"

    class BathroomType(models.TextChoices):
        ATTACHED = "attached", "Attached"
        COMMON = "common", "Common"

    class AirConditioning(models.TextChoices):
        AC = "ac", "AC"
        NON_AC = "non_ac", "Non-AC"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="rooms",
    )
    room_type = models.CharField(
        max_length=100,
        help_text="For example: Deluxe AC Single, Standard Double Non-AC",
    )
    occupancy = models.CharField(
        max_length=20,
        choices=Occupancy.choices,
        default=Occupancy.SINGLE,
    )
    monthly_rent = models.PositiveIntegerField(help_text="Monthly rent per bed/room in ₹")
    security_deposit = models.PositiveIntegerField(
        default=0,
        help_text="Security deposit in ₹",
    )
    total_beds = models.PositiveIntegerField(default=1)
    available_beds = models.PositiveIntegerField(default=1)
    bathroom_type = models.CharField(
        max_length=20,
        choices=BathroomType.choices,
        default=BathroomType.ATTACHED,
    )
    air_conditioning = models.CharField(
        max_length=20,
        choices=AirConditioning.choices,
        default=AirConditioning.NON_AC,
    )
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["monthly_rent", "occupancy"]

    def __str__(self):
        return f"{self.property.name} - {self.room_type} ({self.get_occupancy_display()})"


class PropertyImage(models.Model):
    """Gallery image belonging to a property with room/facility categorisation."""

    class Category(models.TextChoices):
        EXTERIOR = "exterior", "Exterior"
        BEDROOM = "bedroom", "Bedroom"
        BATHROOM = "bathroom", "Bathroom"
        KITCHEN = "kitchen", "Kitchen"
        COMMON_AREA = "common_area", "Common areas"
        OTHER = "other", "Other facilities"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="properties/gallery/%Y/%m/")
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.BEDROOM,
    )
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"{self.property.name} - {self.get_category_display()}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            PropertyImage.objects.filter(property=self.property, is_primary=True).exclude(
                pk=self.pk
            ).update(is_primary=False)
        super().save(*args, **kwargs)


class Favourite(models.Model):
    """A property saved by a student."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favourites",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="favourited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("student", "property"),
                name="unique_student_property_favourite",
            )
        ]

    def __str__(self):
        return f"{self.student} saved {self.property}"
