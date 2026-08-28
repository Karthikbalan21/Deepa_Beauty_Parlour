from django import forms
from datetime import datetime, timedelta

from django.utils import timezone
from .models import Appointment


class AppointmentForm(forms.ModelForm):

    class Meta:
        model = Appointment

        fields = [
            "salon",
            "service",
            "staff",
            "appointment_date",
            "appointment_time",
            "notes",
        ]

        widgets = {

            "salon": forms.Select(attrs={
                "class": "form-select"
            }),

            "service": forms.Select(attrs={
                "class": "form-select"
            }),

            "staff": forms.Select(attrs={
                "class": "form-select"
            }),

            "appointment_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "appointment_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time"
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Any special request..."
            }),

        }

    def clean(self):
        cleaned = super().clean()
        salon, service, staff = (cleaned.get(key) for key in ("salon", "service", "staff"))
        appointment_date = cleaned.get("appointment_date")
        if service and salon and service.salon_id != salon.id:
            self.add_error("service", "Please select a service offered by this salon.")
        if staff and salon and staff.salon_id != salon.id:
            self.add_error("staff", "Please select a staff member from this salon.")
        if service and not service.is_available:
            self.add_error("service", "This service is currently unavailable.")
        if staff and not staff.is_available:
            self.add_error("staff", "This staff member is currently unavailable.")
        appointment_time = cleaned.get("appointment_time")
        if appointment_date and appointment_date < timezone.localdate():
            self.add_error("appointment_date", "Please choose today or a future date.")
        if (
            appointment_date
            and appointment_time
            and appointment_date == timezone.localdate()
            and appointment_time <= timezone.localtime().time().replace(second=0, microsecond=0)
        ):
            self.add_error("appointment_time", "Please choose a future time.")
        if salon and appointment_time:
            if not salon.is_active:
                self.add_error("salon", "This salon is currently unavailable.")
            elif not (salon.opening_time <= appointment_time < salon.closing_time):
                self.add_error(
                    "appointment_time",
                    f"Bookings are available from {salon.opening_time:%I:%M %p} to "
                    f"{salon.closing_time:%I:%M %p}.",
                )
        if staff and service and appointment_date and appointment_time:
            start = datetime.combine(appointment_date, appointment_time)
            end = start + timedelta(minutes=service.duration)
            if salon and end.time() > salon.closing_time:
                self.add_error("appointment_time", "This service would finish after salon closing time.")
            active_appointments = Appointment.objects.filter(
                staff=staff,
                appointment_date=appointment_date,
            ).exclude(
                status__in=[Appointment.Status.CANCELLED, Appointment.Status.COMPLETED],
            ).exclude(pk=self.instance.pk)
            for appointment in active_appointments.select_related("service"):
                existing_start = datetime.combine(appointment_date, appointment.appointment_time)
                existing_end = existing_start + timedelta(minutes=appointment.service.duration)
                if start < existing_end and existing_start < end:
                    self.add_error(
                        "appointment_time",
                        "This staff member already has an appointment during this time.",
                    )
                    break
        return cleaned


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = __import__("appointments.models", fromlist=["Payment"]).Payment
        fields = ["screenshot"]
        widgets = {"screenshot": forms.FileInput(attrs={"class": "form-control", "accept": "image/png,image/jpeg,image/webp"})}
