from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from appointments.models import Appointment, Payment, LoyaltyTransaction


def landing(request):
    from salons.models import Salon, Staff
    from services.models import Service
    from reviews.models import Feedback

    positive_feedbacks = Feedback.objects.filter(
        sentiment=Feedback.Sentiment.POSITIVE
    ).select_related("customer", "service", "appointment__staff").order_by("-created_at")[:6]

    return render(request, "dashboard/home.html", {
        "salon_count": Salon.objects.filter(is_active=True).count(),
        "staff_count": Staff.objects.filter(is_available=True).count(),
        "service_count": Service.objects.filter(is_available=True).count(),
        "completed_count": Appointment.objects.filter(status=Appointment.Status.COMPLETED).count(),
        "featured_services": Service.objects.filter(is_available=True).select_related("salon")[:3],
        "popular_salons": Salon.objects.filter(is_active=True)[:3],
        "positive_feedbacks": positive_feedbacks,
    })


def _staff_profile_for(user):
    """Return the linked profile, retaining compatibility with legacy staff data."""
    try:
        return user.staff_profile
    except Exception:
        from salons.models import Staff
        profile = Staff.objects.filter(name__iexact=user.username).first()
        if profile and not profile.user_id:
            profile.user = user
            profile.save(update_fields=["user"])
        return profile


def _staff_metrics(staff_profile):
    today = timezone.localdate()
    appointments = Appointment.objects.filter(staff=staff_profile)
    completed_payments = Payment.objects.filter(
        appointment__staff=staff_profile,
        appointment__status=Appointment.Status.COMPLETED,
        status=Payment.Status.VERIFIED,
    )
    amount = lambda queryset: queryset.aggregate(value=Sum("amount"))["value"] or 0
    return {
        "completed": appointments.filter(appointment_date=today, status=Appointment.Status.COMPLETED).count(),
        "pending": appointments.filter(appointment_date=today, status=Appointment.Status.PENDING).count(),
        "daily_revenue": str(amount(completed_payments.filter(appointment__appointment_date=today))),
        "weekly_revenue": str(amount(completed_payments.filter(appointment__appointment_date__gte=today - timedelta(days=6)))),
        "monthly_revenue": str(amount(completed_payments.filter(appointment__appointment_date__gte=today - timedelta(days=30)))),
    }

@login_required
def dashboard(request):
    role = request.user.role
    today = timezone.localdate()
    if role == "CUSTOMER":
        appointments = Appointment.objects.filter(customer=request.user)
        completed = appointments.filter(status=Appointment.Status.COMPLETED)
        points = LoyaltyTransaction.objects.filter(customer=request.user).aggregate(v=Sum("points"))["v"] or 0
        recent = appointments.select_related("service", "salon", "staff").order_by("-appointment_date")[:5]
        context = {"upcoming": appointments.filter(appointment_date__gte=today, status__in=["PENDING", "CONFIRMED"]).count(), "completed": completed.count(), "cancelled": appointments.filter(status="CANCELLED").count(), "spent": Payment.objects.filter(appointment__customer=request.user, status=Payment.Status.VERIFIED).aggregate(v=Sum("amount"))["v"] or 0, "points": points, "redeemed": appointments.aggregate(v=Sum("loyalty_redeemed"))["v"] or 0, "recent": recent}
        return render(request, "dashboard/customer_dashboard.html", context)
    if role in ["OWNER", "ADMIN"] or request.user.is_superuser:
        return redirect("owner_dashboard")
    if role == "SERVICE_MANAGER":
        return redirect("owner_services")
    if role == "STAFF":
        # Use the linked staff profile. The name fallback keeps existing staff
        # records (for example, Sarah) working until they are explicitly linked.
        staff_profile = _staff_profile_for(request.user)
        qs = Appointment.objects.filter(staff=staff_profile, appointment_date__gte=today - timedelta(days=30)).select_related("customer", "service", "salon", "payment") if staff_profile else Appointment.objects.none()
        metrics = _staff_metrics(staff_profile) if staff_profile else {"completed": 0, "pending": 0, "daily_revenue": 0, "weekly_revenue": 0, "monthly_revenue": 0}
        context = {
            "today": qs.filter(appointment_date=today).order_by("appointment_time"),
            "recent": qs.order_by("-appointment_date", "-appointment_time")[:20],
            "completed": metrics["completed"],
            "pending": metrics["pending"],
            "cancelled": qs.filter(appointment_date=today, status=Appointment.Status.CANCELLED).count(),
            "weekly_appointments": qs.filter(appointment_date__gte=today-timedelta(days=6)).count(),
            "monthly_appointments": qs.count(),
            **metrics,
        }
        return render(request, "dashboard/staff_dashboard.html", context)
    return render(request, "dashboard/home.html")

@login_required
def update_staff_appointment(request, pk, status):
    if request.user.role != "STAFF":
        messages.error(request, "Only staff members can update their schedules.")
        return redirect("dashboard")
    staff = _staff_profile_for(request.user)
    if not staff:
        messages.error(request, "Your login is not linked to a staff profile yet.")
        return redirect("dashboard")
    appointment = get_object_or_404(Appointment, pk=pk, staff=staff)
    allowed = {Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED, Appointment.Status.COMPLETED}
    if request.method == "POST" and status in allowed:
        appointment.status = status
        update_fields = ["status", "updated_at"]
        if status == Appointment.Status.COMPLETED:
            appointment.worker_completed = True
            appointment.worker_completed_at = timezone.now()
            notes = request.POST.get("worker_notes", "").strip()
            appointment.worker_notes = notes or "Task completed successfully by worker."
            update_fields.extend(["worker_completed", "worker_completed_at", "worker_notes"])
            if not LoyaltyTransaction.objects.filter(appointment=appointment).exists():
                visits = Appointment.objects.filter(
                    customer=appointment.customer,
                    status=Appointment.Status.COMPLETED,
                ).count()
                if visits > 3:
                    LoyaltyTransaction.objects.create(
                        customer=appointment.customer,
                        appointment=appointment,
                        points=10,
                        note="Loyalty reward for completed salon visit",
                    )
            from appointments.views import _refresh_trending
            _refresh_trending()
            messages.success(
                request,
                f"Service marked completed! Admin has been intimated that {appointment.customer.username}'s task is finished."
            )
        else:
            messages.success(request, f"Appointment marked {appointment.get_status_display()}.")
        appointment.save(update_fields=update_fields)
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({
                "ok": True,
                "status": appointment.get_status_display(),
                "metrics": _staff_metrics(staff),
            })
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"ok": False, "message": "The appointment could not be updated."}, status=400)
    return redirect("dashboard")


@login_required
def verify_staff_payment(request, pk, decision):
    """Let assigned staff manually accept or reject a submitted payment proof."""
    if request.user.role != "STAFF":
        messages.error(request, "Only staff members can verify payments.")
        return redirect("dashboard")
    staff = _staff_profile_for(request.user)
    if not staff:
        messages.error(request, "Your login is not linked to a staff profile yet.")
        return redirect("dashboard")
    payment = get_object_or_404(Payment, pk=pk, appointment__staff=staff)
    if request.method == "POST" and decision in {Payment.Status.VERIFIED, Payment.Status.REJECTED}:
        if not payment.screenshot:
            messages.error(request, "A payment screenshot is required before verification.")
        else:
            payment.status = decision
            payment.save(update_fields=["status"])
            payment.appointment.status = (
                Appointment.Status.CONFIRMED
                if decision == Payment.Status.VERIFIED
                else Appointment.Status.CANCELLED
            )
            payment.appointment.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Payment {payment.get_status_display().lower()}.")
            if request.headers.get("Accept") == "application/json":
                return JsonResponse({
                    "ok": True,
                    "status": payment.appointment.get_status_display(),
                    "metrics": _staff_metrics(staff),
                })
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"ok": False, "message": "The payment could not be verified."}, status=400)
    return redirect("dashboard")

