from django import forms
from datetime import datetime, timedelta

from django.utils import timezone
from .models import Appointment
from salons.models import Staff
from services.models import Service


class AppointmentForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_available=True).select_related("salon")
        self.fields["staff"].queryset = Staff.objects.filter(is_available=True).select_related("salon")
        self.fields["staff"].required = False
        self.fields["staff"].empty_label = "✨ Auto-assign by Parlour Admin (Recommended)"

    class Meta:
        model = Appointment

        fields = [
            "service",
            "staff",
            "appointment_date",
            "appointment_time",
            "notes",
        ]

        widgets = {

            "service": forms.Select(attrs={
                "class": "form-select",
                "data-validate": "required",
            }),

            "staff": forms.Select(attrs={
                "class": "form-select",
            }),

            "appointment_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
                "data-validate": "required",
            }),

            "appointment_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
                "data-validate": "required",
            }),

            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Any special request (e.g. skin type, preferred styling)..."
            }),

        }

    def clean(self):
        cleaned = super().clean()
        service, staff = (cleaned.get(key) for key in ("service", "staff"))
        salon = service.salon if service else None
        appointment_date = cleaned.get("appointment_date")
        if staff and salon and staff.salon_id != salon.id:
            self.add_error("staff", "Please select a staff member who provides services at this location.")
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
                self.add_error("service", "This service location is currently unavailable.")
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

    def save(self, commit=True):
        appointment = super().save(commit=False)
        appointment.salon = appointment.service.salon
        if commit:
            appointment.save()
            self.save_m2m()
        return appointment


class PaymentProofForm(forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=[
            ("ONLINE", "Online Payment (Instant Simulation / Card / NetBanking / UPI)"),
            ("UPI", "UPI QR Code Scan & Screenshot Upload"),
        ],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="ONLINE"
    )
    transaction_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Reference / Transaction ID (e.g., TXN12345678)"}),
        help_text="Provide payment reference ID or leave empty for auto-generation on online pay."
    )

    class Meta:
        model = __import__("appointments.models", fromlist=["Payment"]).Payment
        fields = ["payment_method", "transaction_id", "screenshot"]
        widgets = {
            "screenshot": forms.FileInput(attrs={"class": "form-control", "accept": "image/png,image/jpeg,image/webp"}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = __import__("reviews.models", fromlist=["Feedback"]).Feedback
        fields = ["rating", "comments"]
        widgets = {
            "rating": forms.Select(attrs={"class": "form-select"}),
            "comments": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "How was your experience at Deepa Beauty Parlour? Share your review here..."
            }),
        }
