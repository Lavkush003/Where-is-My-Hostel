from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from properties import views as properties_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("explore-pgs/", properties_views.explore_pgs, name="explore_pgs_alias"),
    path("properties/", include("properties.urls")),
    path("locations/", include("locations.urls")),
    path("enquiries/", include("enquiries.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
