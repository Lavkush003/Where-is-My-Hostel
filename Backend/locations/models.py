"""Models for landmarks, coordinates, and cached geographical points of interest."""

from django.db import models


class Landmark(models.Model):
    """
    Known educational institutions, transit hubs, commercial centres,
    and coaching hubs used for fast, high-accuracy student discovery.
    """

    class Category(models.TextChoices):
        COACHING = "coaching", "Coaching Institute"
        COLLEGE = "college", "College"
        UNIVERSITY = "university", "University"
        RAILWAY_STATION = "railway_station", "Railway Station"
        BUS_STATION = "bus_station", "Bus Station"
        METRO_STATION = "metro_station", "Metro Station"
        HOSPITAL = "hospital", "Hospital"
        MARKET = "market", "Market / Shopping Mall"
        LOCALITY = "locality", "Locality / Area"
        CITY = "city", "City Hub"

    name = models.CharField(max_length=200, db_index=True)
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.COACHING,
        db_index=True,
    )
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, default="Uttar Pradesh", blank=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    aliases = models.TextField(
        blank=True,
        help_text="Comma-separated keywords or alternative names for search matching.",
    )
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["city", "name"]
        indexes = [
            models.Index(fields=["city", "category"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def coordinates(self):
        return (float(self.latitude), float(self.longitude))

    @property
    def aliases_list(self):
        if not self.aliases:
            return []
        return [a.strip() for a in self.aliases.split(",") if a.strip()]


class PlaceCache(models.Model):
    """
    Persistent cache for Overpass API POIs and Nominatim geocoding responses.
    Prevents repeated external API calls and conforms to OpenStreetMap fair usage.
    """

    cache_key = models.CharField(max_length=255, unique=True, db_index=True)
    category = models.CharField(max_length=50, blank=True)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.cache_key
