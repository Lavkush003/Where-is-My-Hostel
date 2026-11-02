from django.conf import settings


def site_context(request):
    return {
        "site_name": settings.SITE_NAME,
        "contact_email": settings.CONTACT_EMAIL,
        "mapbox_access_token": getattr(settings, "MAPBOX_ACCESS_TOKEN", ""),
    }
