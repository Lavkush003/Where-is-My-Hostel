# Views for public informational and landing pages.
from django.http import JsonResponse
from django.shortcuts import render
from locations.demo_data import CITY_CARDS, POPULAR_CITY_SHORTCUTS
from properties.demo_data import ACCOMMODATION_TYPES, FEATURED_PROPERTIES


def home(request):
    return render(
        request,
        "core/home.html",
        {
            "popular_cities": POPULAR_CITY_SHORTCUTS,
            "city_cards": CITY_CARDS,
            "featured_properties": FEATURED_PROPERTIES,
            "accommodation_types": ACCOMMODATION_TYPES,
        },
    )


def about(request):
    return render(request, "core/about.html")


def contact(request):
    return render(request, "core/contact.html")


def privacy(request):
    return render(request, "core/privacy.html")


def terms(request):
    return render(request, "core/terms.html")


def health(request):
    return JsonResponse({"status": "ok"})


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
