from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from urllib.parse import quote
from .forms import AppointmentForm, PaymentProofForm
from .models import Appointment, Payment, LoyaltyTransaction


def _refresh_trending():
    from services.models import Service
    top = Appointment.objects.filter(status__in=[Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED]).values("service_id").annotate(n=Count("id")).order_by("-n")[:3]
    Service.objects.update(is_trending=False)
    Service.objects.filter(id__in=[item["service_id"] for item in top]).update(is_trending=True)


@login_required
def book_appointment(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                appointment = form.save(commit=False)
                appointment.customer = request.user
                appointment.status = Appointment.Status.PENDING
                appointment.save()
                Payment.objects.create(appointment=appointment, amount=appointment.service.price)
            messages.success(request, "Appointment booked successfully.")
            return redirect("upload_payment_proof", pk=appointment.pk)
    else:
        form = AppointmentForm()
    return render(request, "appointments/book_appointment.html", {"form": form})


@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(customer=request.user).select_related("salon", "staff", "service").order_by("-appointment_date", "-appointment_time")
    return render(request, "appointments/my_appointments.html", {"appointments": appointments})


@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, id=pk, customer=request.user)
    if request.method == "POST" and appointment.status in [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
    return redirect("my_appointments")


@login_required
def reschedule_appointment(request, pk):
    old = get_object_or_404(Appointment, id=pk, customer=request.user)
    if old.status not in [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]:
        messages.error(request, "Only active appointments can be rescheduled.")
        return redirect("my_appointments")
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            new = form.save(commit=False); new.customer = request.user; new.rescheduled_from = old; new.save()
            Payment.objects.create(appointment=new, amount=new.service.price)
            old.status = Appointment.Status.CANCELLED; old.save()
            messages.success(request, "Appointment rescheduled. Please upload payment proof for the new booking.")
            return redirect("upload_payment_proof", pk=new.pk)
    else:
        form = AppointmentForm(instance=old)
    return render(request, "appointments/book_appointment.html", {"form": form, "rescheduling": old})


@login_required
def upload_payment_proof(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)
    payment, _ = Payment.objects.get_or_create(appointment=appointment, defaults={"amount": appointment.service.price})
    if payment.status == Payment.Status.VERIFIED:
        messages.info(request, "This payment has already been verified.")
        return redirect("my_appointments")
    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            proof = form.save(commit=False)
            if proof.screenshot and proof.screenshot.size > 5 * 1024 * 1024:
                form.add_error("screenshot", "Image must be smaller than 5 MB.")
            else:
                proof.status = Payment.Status.PENDING; proof.save()
                messages.success(request, "Payment proof submitted for verification.")
                return redirect("my_appointments")
    else: form = PaymentProofForm(instance=payment)
    upi = appointment.salon.upi_id or "salon@upi"
    payload = quote(f"upi://pay?pa={upi}&pn={appointment.salon.name}&am={payment.amount}&cu=INR")
    return render(request, "appointments/payment_proof.html", {"form": form, "appointment": appointment, "payment": payment, "qr_payload": payload})
