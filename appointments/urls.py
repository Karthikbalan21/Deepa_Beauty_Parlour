from django.urls import path

from .views import (
    book_appointment,
    my_appointments,
    cancel_appointment,
    reschedule_appointment,
    upload_payment_proof,
)
urlpatterns = [
    path("book/", book_appointment,name="book_appointment"),
    path("my/",my_appointments,name="my_appointments"),
    path("cancel/<int:pk>/",cancel_appointment,name="cancel_appointment"),
    path("reschedule/<int:pk>/", reschedule_appointment, name="reschedule_appointment"),
    path("payment/<int:pk>/", upload_payment_proof, name="upload_payment_proof"),
]
