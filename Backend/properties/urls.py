from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    path("", views.property_list, name="list"),
    path("explore-pgs/", views.explore_pgs, name="explore_pgs"),
    path("api/search/", views.api_property_search, name="api_search"),
    path("manage/", views.owner_property_list, name="owner_list"),
    path("manage/new/", views.property_create, name="create"),
    path("manage/<slug:slug>/edit/", views.property_edit, name="edit"),
    path("manage/<slug:slug>/delete/", views.property_delete, name="delete"),
    path("manage/<slug:slug>/toggle-active/", views.property_toggle_active, name="toggle_active"),
    path("manage/<slug:slug>/rooms/", views.room_list, name="room_list"),
    path("manage/<slug:slug>/rooms/<int:room_pk>/edit/", views.room_edit, name="room_edit"),
    path("manage/<slug:slug>/rooms/<int:room_pk>/delete/", views.room_delete, name="room_delete"),
    path("manage/<slug:slug>/rooms/<int:room_pk>/update-beds/", views.room_update_beds, name="room_update_beds"),
    path("manage/<slug:slug>/gallery/", views.gallery_manage, name="gallery_manage"),
    path("manage/<slug:slug>/gallery/<int:image_pk>/delete/", views.gallery_delete, name="gallery_delete"),
    path("manage/<slug:slug>/gallery/<int:image_pk>/primary/", views.gallery_set_primary, name="gallery_set_primary"),
    path("favourite/<slug:slug>/", views.toggle_favourite, name="favourite"),
    path("<slug:slug>/", views.property_detail, name="detail"),
]
