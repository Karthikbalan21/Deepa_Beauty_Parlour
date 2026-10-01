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
    return render(request, "appointments/book_appointment.html", _booking_context(form))


def _booking_context(form, **extra):
    """Expose booking form state to the template."""
    context = {
        "form": form,
        "has_available_services": form.fields["service"].queryset.exists(),
    }
    context.update(extra)
    return context


@login_required
def my_appointments(request):
    appointments = (
        Appointment.objects.filter(customer=request.user)
        .select_related("salon", "staff", "service", "payment")
        .prefetch_related("feedbacks")
        .order_by("-appointment_date", "-appointment_time")
    )
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
            messages.success(request, "Appointment rescheduled. Please complete payment for the new booking.")
            return redirect("upload_payment_proof", pk=new.pk)
    else:
        form = AppointmentForm(instance=old)
    return render(request, "appointments/book_appointment.html", _booking_context(form, rescheduling=old))


@login_required
def upload_payment_proof(request, pk):
    import uuid
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)
    payment, _ = Payment.objects.get_or_create(appointment=appointment, defaults={"amount": appointment.service.price})
    if payment.status == Payment.Status.VERIFIED:
        messages.info(request, "This payment has already been verified.")
        return redirect("my_appointments")
    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            proof = form.save(commit=False)
            method = form.cleaned_data.get("payment_method") or "ONLINE"
            proof.payment_method = method
            txn = form.cleaned_data.get("transaction_id")
            if not txn:
                proof.transaction_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
            else:
                proof.transaction_id = txn
            if proof.screenshot and proof.screenshot.size > 5 * 1024 * 1024:
                form.add_error("screenshot", "Image must be smaller than 5 MB.")
            else:
                proof.status = Payment.Status.PENDING
                proof.save()
                messages.success(
                    request,
                    f"Payment details recorded successfully (Txn ID: {proof.transaction_id}). "
                    f"Admin will verify details and assign your worker."
                )
                return redirect("my_appointments")
    else:
        form = PaymentProofForm(instance=payment)
    upi = appointment.salon.upi_id or "deepabeauty@upi"
    payload = quote(f"upi://pay?pa={upi}&pn={appointment.salon.name}&am={payment.amount}&cu=INR")
    return render(
        request,
        "appointments/payment_proof.html",
        {"form": form, "appointment": appointment, "payment": payment, "qr_payload": payload}
    )


@login_required
def submit_feedback(request, pk):
    from reviews.models import Feedback
    from .forms import FeedbackForm
    appointment = get_object_or_404(Appointment, pk=pk, customer=request.user)
    if appointment.status != Appointment.Status.COMPLETED:
        messages.error(request, "Feedback can only be provided for completed appointments.")
        return redirect("my_appointments")
    existing = Feedback.objects.filter(appointment=appointment).first()
    if request.method == "POST":
        form = FeedbackForm(request.POST, instance=existing)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.customer = request.user
            fb.appointment = appointment
            fb.service = appointment.service
            fb.save()
            messages.success(request, "Thank you! Your feedback has been sent to the parlour admin.")
            return redirect("my_appointments")
    else:
        form = FeedbackForm(instance=existing)
    return render(request, "reviews/feedback_form.html", {"form": form, "appointment": appointment, "existing": existing})
