from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from appointments.forms import AppointmentForm
from appointments.models import Appointment
from salons.models import Salon, Staff
from services.models import Service


class AppointmentFormTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="owner", password="test-pass", role="OWNER")
        self.customer = User.objects.create_user(username="customer", password="test-pass")
        self.salon = Salon.objects.create(
            owner=owner,
            name="Test Salon",
            phone="9999999999",
            email="owner@example.com",
            address="Test address",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            opening_time=time(9, 0),
            closing_time=time(18, 0),
        )
        self.staff = Staff.objects.create(
            salon=self.salon,
            name="Stylist",
            phone="9999999998",
            specialization="Hair",
            experience=2,
        )
        self.service = Service.objects.create(
            salon=self.salon,
            name="Haircut",
            duration=60,
            price="500.00",
        )
        self.date = timezone.localdate() + timedelta(days=1)

    def form_data(self, appointment_time):
        return {
            "service": self.service.pk,
            "staff": self.staff.pk,
            "appointment_date": self.date.isoformat(),
            "appointment_time": appointment_time,
            "notes": "",
        }

    def test_rejects_booking_outside_salon_hours(self):
        form = AppointmentForm(data=self.form_data("18:00"))
        self.assertFalse(form.is_valid())
        self.assertIn("appointment_time", form.errors)

    def test_sets_salon_from_the_selected_service(self):
        form = AppointmentForm(data=self.form_data("11:00"))
        self.assertTrue(form.is_valid(), form.errors)
        appointment = form.save(commit=False)
        self.assertEqual(appointment.salon, self.salon)

    def test_rejects_overlapping_staff_booking(self):
        Appointment.objects.create(
            customer=self.customer,
            salon=self.salon,
            staff=self.staff,
            service=self.service,
            appointment_date=self.date,
            appointment_time=time(10, 0),
            status=Appointment.Status.CONFIRMED,
        )
        form = AppointmentForm(data=self.form_data("10:30"))
        self.assertFalse(form.is_valid())
        self.assertIn("appointment_time", form.errors)
