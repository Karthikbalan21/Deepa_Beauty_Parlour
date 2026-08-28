from django.conf import settings
from django.db import models

from salons.models import Salon, Staff
from services.models import Service


class Appointment(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    salon = models.ForeignKey(
        Salon,
        on_delete=models.CASCADE
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    notes = models.TextField(
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    loyalty_redeemed = models.PositiveIntegerField(default=0)
    rescheduled_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reschedules")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta: #Prevent the double Booking
        ordering = ["appointment_date", "appointment_time"]
    def __str__(self):
        return f"{self.customer.username} - {self.appointment_date}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending verification"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    screenshot = models.ImageField(upload_to="payment_proofs/", blank=True, null=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)


class LoyaltyTransaction(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty_transactions")
    points = models.IntegerField()
    appointment = models.ForeignKey(Appointment, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=160)
    discount_percent = models.PositiveIntegerField(default=10)
    active = models.BooleanField(default=True)
    valid_until = models.DateField(null=True, blank=True)
