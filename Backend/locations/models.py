"""Models for landmarks, coordinates, and cached geographical points of interest."""

from django.db import models


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cities",
    )
    state_name = models.CharField(max_length=100, blank=True, default="Uttar Pradesh")
    tag = models.CharField(max_length=100, blank=True, help_text="e.g. Coaching Capital, Sangam City")
    area_summary = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_popular = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class Locality(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="localities",
    )
    city_name = models.CharField(max_length=100, blank=True, db_index=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["city_name", "name"]
        verbose_name_plural = "localities"

    def __str__(self):
        city = self.city_name or (self.city.name if self.city else "")
        return f"{self.name}, {city}" if city else self.name


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
