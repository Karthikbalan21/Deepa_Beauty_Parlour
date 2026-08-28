from django.conf import settings
from django.db import models


class Salon(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salon"
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    upi_id = models.CharField(max_length=100, blank=True, help_text="UPI ID used for payment QR codes")
    payment_qr = models.ImageField(upload_to="payment_qr/", blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    logo = models.ImageField(
        upload_to="salon_logos/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Staff(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="staff_profile",
        blank=True,
        null=True,
        help_text="Login account used by this staff member",
    )

    salon = models.ForeignKey(
        Salon,
        on_delete=models.CASCADE,
        related_name="staff_members"
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    specialization = models.CharField(max_length=100)
    experience = models.PositiveIntegerField(
        help_text="Years"
    )

    photo = models.ImageField(
        upload_to="staff/",
        blank=True,
        null=True
    )

    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name
