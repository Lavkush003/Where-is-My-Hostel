"""Management command to populate standard coaching institutes, universities and transport hubs."""

from django.core.management.base import BaseCommand

from locations.models import Landmark
from locations.services.geocoding import CURATED_LANDMARKS


class Command(BaseCommand):
    help = "Populate standard educational landmarks, coaching hubs, and transit stations."

    def handle(self, *args, **options):
        count = 0
        for item in CURATED_LANDMARKS:
            aliases_str = ", ".join(item.get("aliases", []))
            obj, created = Landmark.objects.update_or_create(
                name=item["name"],
                city=item["city"],
                defaults={
                    "state": item.get("state", "Uttar Pradesh"),
                    "category": item.get("category", "coaching"),
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "address": item.get("address", ""),
                    "aliases": aliases_str,
                    "is_verified": True,
                },
            )
            if created:
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {count} new landmarks ({Landmark.objects.count()} total).")
        )

