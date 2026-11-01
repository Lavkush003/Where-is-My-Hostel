from django.urls import path

from . import views

app_name = "enquiries"

urlpatterns = [
    path("mine/", views.student_enquiry_list, name="student_list"),
    path("owner/", views.owner_enquiry_list, name="owner_list"),
    path("submit/<slug:slug>/", views.submit_enquiry, name="create"),
    path("<int:pk>/status/", views.update_enquiry_status, name="update_status"),
    path("<int:pk>/cancel/", views.cancel_enquiry, name="cancel"),
    path("<int:pk>/accept/", views.owner_accept_enquiry, name="accept"),
    path("<int:pk>/reject/", views.owner_reject_enquiry, name="reject"),
]
