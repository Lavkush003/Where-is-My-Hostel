from django.urls import path

from . import admin_views, views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.student_profile, name="profile"),
    path("favourites/", views.favourite_list, name="favourites"),
    path("owner/profile/", views.owner_profile, name="owner_profile"),

    # Dedicated Admin Portal & Moderation URLs
    path("admin/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("admin/properties/", admin_views.admin_property_list, name="admin_property_list"),
    path("admin/properties/<int:pk>/moderate/", admin_views.admin_property_moderate, name="admin_property_moderate"),
    path("admin/properties/<int:pk>/approve/", admin_views.admin_property_approve, name="admin_property_approve"),
    path("admin/properties/<int:pk>/reject/", admin_views.admin_property_reject, name="admin_property_reject"),
    path("admin/properties/<int:pk>/suspend/", admin_views.admin_property_suspend, name="admin_property_suspend"),
    path("admin/properties/<int:pk>/delete/", admin_views.admin_property_delete, name="admin_property_delete"),

    # Admin User Management
    path("admin/users/", admin_views.admin_user_list, name="admin_user_list"),
    path("admin/users/<int:pk>/toggle-status/", admin_views.admin_user_toggle_status, name="admin_user_toggle_status"),
    path("admin/users/<int:pk>/activity/", admin_views.admin_user_activity, name="admin_user_activity"),

    # Admin Reported Listings
    path("admin/reports/", admin_views.admin_reports_list, name="admin_reports_list"),
    path("admin/reports/<int:pk>/action/", admin_views.admin_report_action, name="admin_report_action"),

    # Admin City & Location Management
    path("admin/locations/", admin_views.admin_locations_manage, name="admin_locations_manage"),
    path("admin/locations/cities/create/", admin_views.admin_city_create, name="admin_city_create"),
    path("admin/locations/cities/<int:pk>/delete/", admin_views.admin_city_delete, name="admin_city_delete"),
    path("admin/locations/states/create/", admin_views.admin_state_create, name="admin_state_create"),
    path("admin/locations/states/<int:pk>/delete/", admin_views.admin_state_delete, name="admin_state_delete"),
    path("admin/locations/localities/create/", admin_views.admin_locality_create, name="admin_locality_create"),
    path("admin/locations/localities/<int:pk>/delete/", admin_views.admin_locality_delete, name="admin_locality_delete"),
    path("admin/locations/landmarks/create/", admin_views.admin_landmark_create, name="admin_landmark_create"),
    path("admin/locations/landmarks/<int:pk>/delete/", admin_views.admin_landmark_delete, name="admin_landmark_delete"),
]
