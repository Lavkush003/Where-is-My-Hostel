from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.student_profile, name="profile"),
    path("favourites/", views.favourite_list, name="favourites"),
    path("owner/profile/", views.owner_profile, name="owner_profile"),
]
