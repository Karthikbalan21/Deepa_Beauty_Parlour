from django.urls import path
from .views import dashboard, update_staff_appointment, verify_staff_payment

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("staff/appointment/<int:pk>/<str:status>/", update_staff_appointment, name="update_staff_appointment"),
    path("staff/payment/<int:pk>/<str:decision>/", verify_staff_payment, name="verify_staff_payment"),
]
