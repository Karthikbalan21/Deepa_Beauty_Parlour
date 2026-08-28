from django.urls import path

from .views import (
    owner_dashboard,
    appointment_list,
    update_appointment,
    service_list,
    staff_list,
    reports,
    add_service,
    toggle_service, toggle_staff, download_report, verify_payment, edit_service, delete_service, add_staff,
)

urlpatterns = [

    path("", owner_dashboard, name="owner_dashboard"),
    path("appointments/", appointment_list, name="owner_appointments"),
    path("appointment/<int:pk>/<str:status>/", update_appointment, name="update_appointment"),
    path("payment/<int:pk>/<str:decision>/", verify_payment, name="verify_payment"),
    path("services/", service_list, name="owner_services"),
    path("staff/", staff_list, name="owner_staff"),
    path("staff/add/", add_staff, name="add_staff"),
    path("reports/", reports, name="owner_reports"),
    path("services/add/", add_service,name="add_service"),
    path("services/<int:pk>/toggle/", toggle_service, name="toggle_service"),
    path("services/<int:pk>/edit/", edit_service, name="edit_service"),
    path("services/<int:pk>/delete/", delete_service, name="delete_service"),
    path("staff/<int:pk>/toggle/", toggle_staff, name="toggle_staff"),
    path("reports/download/", download_report, name="download_report"),
]
