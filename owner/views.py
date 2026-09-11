import csv
from datetime import timedelta
from django.contrib import messages
from django.db import models
from django.db.models import Count, Sum, Avg
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .decorators import owner_required
from appointments.models import Appointment, Payment, LoyaltyTransaction
from salons.models import Salon, Staff
from services.models import Service
from services.forms import ServiceForm
from accounts.models import User
from salons.forms import StaffForm


def get_admin_salon(request):
    """Retrieve salon for current user or default to Deepa Beauty Parlour."""
    if hasattr(request.user, "salon"):
        return request.user.salon
    salon = Salon.objects.filter(name__icontains="Deepa").first() or Salon.objects.first()
    if not salon:
        salon = Salon.objects.create(
            owner=request.user,
            name="Deepa Beauty Parlour",
            phone="9876543210",
            email="deepabeauty@gmail.com",
            address="Main Road, City Center",
            city="Chennai",
            state="Tamil Nadu",
            pincode="600001",
            opening_time="09:00",
            closing_time="21:00",
        )
    return salon


def scoped(request, qs):
    """Scope queryset to admin's salon."""
    salon = get_admin_salon(request)
    if salon and hasattr(qs.model, "salon"):
        return qs.filter(salon=salon)
    return qs


@owner_required
def owner_dashboard(request):
    today = timezone.localdate()
    appointments = scoped(request, Appointment.objects.all())
    payments = Payment.objects.filter(
        appointment__in=appointments,
        status=Payment.Status.VERIFIED,
    )
    month = today.replace(day=1)
    completed = appointments.filter(status=Appointment.Status.COMPLETED)
    total = appointments.count()
    health = min(100, round((completed.count() / total * 45 if total else 0) + (payments.filter(appointment__appointment_date__gte=month).count() / max(1, appointments.filter(appointment_date__gte=month).count()) * 35) + 20))
    status_counts = {status: appointments.filter(status=status).count() for status in Appointment.Status.values}
    top_staff = payments.values("appointment__staff__name").annotate(total=Sum("amount")).order_by("-total").first()
    popular_services = appointments.values("service__name").annotate(total=Count("id")).order_by("-total")[:5]
    worker_completed_count = appointments.filter(worker_completed=True).count()
    
    from reviews.models import Feedback
    feedbacks_count = Feedback.objects.count()
    avg_rating = Feedback.objects.aggregate(avg=Avg("rating"))["avg"] or 0

    context = {
        "total_customers": appointments.values("customer").distinct().count(),
        "today_appointments": appointments.filter(appointment_date=today).count(),
        "today_revenue": payments.filter(appointment__appointment_date=today).aggregate(v=Sum("amount"))["v"] or 0,
        "monthly_revenue": payments.filter(appointment__appointment_date__gte=month).aggregate(v=Sum("amount"))["v"] or 0,
        "total_staff": scoped(request, Staff.objects.all()).count(),
        "total_services": scoped(request, Service.objects.all()).count(),
        "pending_payments": Payment.objects.filter(appointment__in=appointments, status="PENDING").count(),
        "verified_payments": payments.count(),
        "cancelled": status_counts[Appointment.Status.CANCELLED],
        "completed": completed.count(),
        "worker_completed_count": worker_completed_count,
        "feedbacks_count": feedbacks_count,
        "avg_rating": round(avg_rating, 1),
        "health": health,
        "top_staff": top_staff,
        "popular_services": popular_services,
        "status_labels": list(status_counts.keys()),
        "status_values": list(status_counts.values()),
        "recent": appointments.select_related("customer", "service", "staff").order_by("-created_at")[:8]
    }
    return render(request, "owner/dashboard.html", context)


@owner_required
def appointment_list(request):
    all_scoped = scoped(request, Appointment.objects.all())
    total_count = all_scoped.count()
    unassigned_count = all_scoped.filter(staff__isnull=True).exclude(status=Appointment.Status.CANCELLED).count()
    pending_pay_count = Payment.objects.filter(appointment__in=all_scoped, status=Payment.Status.PENDING).count()
    completed_count = all_scoped.filter(status=Appointment.Status.COMPLETED).count()

    appointments = scoped(request, Appointment.objects.select_related("customer", "salon", "service", "staff", "payment"))
    for field in ("status", "staff", "service", "salon"):
        if request.GET.get(field):
            appointments = appointments.filter(**{field if field == "status" else field + "_id": request.GET[field]})
    if request.GET.get("date"):
        appointments = appointments.filter(appointment_date=request.GET["date"])
    if request.GET.get("payment"):
        appointments = appointments.filter(payment__status=request.GET["payment"])
    q = request.GET.get("q")
    if q:
        appointments = appointments.filter(
            models.Q(customer__username__icontains=q)
            | models.Q(customer__first_name__icontains=q)
            | models.Q(customer__phone__icontains=q)
            | models.Q(service__name__icontains=q)
            | models.Q(payment__transaction_id__icontains=q)
        )
    return render(request, "owner/appointments.html", {
        "appointments": appointments.order_by("-appointment_date", "-appointment_time"),
        "staffs": scoped(request, Staff.objects.filter(is_available=True)),
        "services": scoped(request, Service.objects.all()),
        "total_count": total_count,
        "unassigned_count": unassigned_count,
        "pending_pay_count": pending_pay_count,
        "completed_count": completed_count,
    })


@owner_required
def assign_worker(request, pk):
    appointment = get_object_or_404(scoped(request, Appointment.objects.all()), pk=pk)
    if request.method == "POST":
        staff_id = request.POST.get("staff_id")
        if staff_id:
            staff = get_object_or_404(Staff, id=staff_id)
            appointment.staff = staff
            appointment.save(update_fields=["staff", "updated_at"])
            messages.success(request, f"Worker '{staff.name}' assigned to {appointment.customer.username}'s appointment.")
        else:
            appointment.staff = None
            appointment.save(update_fields=["staff", "updated_at"])
            messages.info(request, "Worker unassigned from this appointment.")
    return redirect("owner_appointments")


@owner_required
def update_appointment(request, pk, status):
    appointment = get_object_or_404(scoped(request, Appointment.objects.all()), pk=pk)
    if request.method == "POST" and status in Appointment.Status.values:
        if status in [Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED] and (not hasattr(appointment, "payment") or appointment.payment.status != Payment.Status.VERIFIED):
            messages.error(request, "This appointment cannot be confirmed until its payment is verified.")
            return redirect("owner_appointments")
        appointment.status = status
        appointment.save()
        if status == Appointment.Status.COMPLETED and not LoyaltyTransaction.objects.filter(appointment=appointment).exists():
            visits = Appointment.objects.filter(customer=appointment.customer, status=Appointment.Status.COMPLETED).count()
            if visits > 3:
                LoyaltyTransaction.objects.create(customer=appointment.customer, appointment=appointment, points=10, note="Loyalty reward for completed salon visit")
        if status == Appointment.Status.COMPLETED:
            from appointments.views import _refresh_trending
            _refresh_trending()
        messages.success(request, f"Appointment marked {appointment.get_status_display()}.")
    return redirect("owner_appointments")


@owner_required
def verify_payment(request, pk, decision):
    payment = get_object_or_404(Payment.objects.filter(appointment__in=scoped(request, Appointment.objects.all())), pk=pk)
    if request.method == "POST" and decision in [Payment.Status.VERIFIED, Payment.Status.REJECTED]:
        payment.status = decision
        if decision == Payment.Status.VERIFIED:
            payment.verified_at = timezone.now()
            payment.appointment.status = Appointment.Status.CONFIRMED
        else:
            payment.appointment.status = Appointment.Status.CANCELLED
        payment.save(update_fields=["status", "verified_at"])
        payment.appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Payment {payment.get_status_display().lower()} successfully. Appointment updated.")
    return redirect("owner_appointments")


@owner_required
def edit_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    form = ServiceForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Service '{service.name}' updated.")
        return redirect("owner_services")
    return render(request, "owner/add_service.html", {"form": form, "service": service})


@owner_required
def delete_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    if request.method == "POST":
        name = service.name
        service.delete()
        messages.success(request, f"Service '{name}' deleted.")
    return redirect("owner_services")


@owner_required
def service_list(request):
    return render(request, "owner/services.html", {"services": scoped(request, Service.objects.all())})


@owner_required
def add_service(request):
    salon = get_admin_salon(request)
    form = ServiceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        service.salon = salon
        service.save()
        messages.success(request, f"Beauty activity '{service.name}' added successfully.")
        return redirect("owner_services")
    return render(request, "owner/add_service.html", {"form": form})


@owner_required
def toggle_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    if request.method == "POST":
        service.is_available = not service.is_available
        service.save()
        messages.success(request, f"Service '{service.name}' availability updated.")
    return redirect("owner_services")


@owner_required
def staff_list(request):
    return render(request, "owner/staff.html", {"staffs": scoped(request, Staff.objects.all())})


@owner_required
def add_staff(request):
    salon = get_admin_salon(request)
    form = StaffForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        staff = form.save(salon=salon)
        messages.success(request, f"Worker '{staff.name}' added with login credentials.")
        return redirect("owner_staff")
    return render(request, "owner/add_staff.html", {"form": form})


@owner_required
def toggle_staff(request, pk):
    staff = get_object_or_404(scoped(request, Staff.objects.all()), pk=pk)
    if request.method == "POST":
        staff.is_available = not staff.is_available
        staff.save()
        messages.success(request, f"Worker '{staff.name}' availability updated.")
    return redirect("owner_staff")

@owner_required
def edit_staff(request, pk):
    staff = get_object_or_404(scoped(request, Staff.objects.all()), pk=pk)
    from salons.forms import StaffEditForm
    form = StaffEditForm(request.POST or None, request.FILES or None, instance=staff)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Worker '{staff.name}' details updated successfully.")
        return redirect("owner_staff")
    return render(request, "owner/edit_staff.html", {"form": form, "staff": staff})


@owner_required
def delete_staff(request, pk):
    staff = get_object_or_404(scoped(request, Staff.objects.all()), pk=pk)
    if request.method == "POST":
        name = staff.name
        user = staff.user
        staff.delete()
        if user and user.role == User.Role.STAFF:
            user.delete()
        messages.success(request, f"Worker '{name}' and login credentials deleted.")
    return redirect("owner_staff")


@owner_required
def delete_feedback(request, pk):
    from reviews.models import Feedback
    feedback = get_object_or_404(Feedback, pk=pk)
    if request.method == "POST":
        feedback.delete()
        messages.success(request, "Customer feedback deleted successfully.")
    return redirect("owner_feedbacks")


@owner_required
def feedback_list(request):
    from reviews.models import Feedback
    all_feedbacks = Feedback.objects.select_related("customer", "appointment", "service", "appointment__staff")
    
    total_feedbacks = all_feedbacks.count()
    positive_count = all_feedbacks.filter(sentiment=Feedback.Sentiment.POSITIVE).count()
    neutral_count = all_feedbacks.filter(sentiment=Feedback.Sentiment.NEUTRAL).count()
    negative_count = all_feedbacks.filter(sentiment=Feedback.Sentiment.NEGATIVE).count()
    avg_rating = all_feedbacks.aggregate(avg=Avg("rating"))["avg"] or 0

    sentiment = request.GET.get("sentiment")
    feedbacks = all_feedbacks.order_by("-created_at")
    if sentiment in Feedback.Sentiment.values:
        feedbacks = feedbacks.filter(sentiment=sentiment)

    q = request.GET.get("q")
    if q:
        feedbacks = feedbacks.filter(
            models.Q(customer__username__icontains=q)
            | models.Q(customer__first_name__icontains=q)
            | models.Q(comments__icontains=q)
            | models.Q(service__name__icontains=q)
        )

    return render(request, "owner/feedbacks.html", {
        "feedbacks": feedbacks,
        "total_feedbacks": total_feedbacks,
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "avg_rating": round(avg_rating, 1),
    })


@owner_required
def reports(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    appts = scoped(request, Appointment.objects.all())
    payments = Payment.objects.filter(appointment__in=appts, status=Payment.Status.VERIFIED)
    
    total_sales = payments.aggregate(v=Sum("amount"))["v"] or 0
    today_sales = payments.filter(appointment__appointment_date=today).aggregate(v=Sum("amount"))["v"] or 0
    month_sales = payments.filter(appointment__appointment_date__gte=month_start).aggregate(v=Sum("amount"))["v"] or 0
    
    statuses = {s: appts.filter(status=s).count() for s in Appointment.Status.values}
    popular = appts.values("service__name").annotate(total=Count("id")).order_by("-total")[:8]
    
    worker_performance = Staff.objects.filter(salon=get_admin_salon(request)).annotate(
        tasks_completed=Count("appointments", filter=models.Q(appointments__status=Appointment.Status.COMPLETED)),
        tasks_assigned=Count("appointments"),
    )
    
    context = {
        "total": appts.count(),
        "total_sales": total_sales,
        "today_sales": today_sales,
        "month_sales": month_sales,
        "pending": statuses["PENDING"],
        "confirmed": statuses["CONFIRMED"],
        "completed": statuses["COMPLETED"],
        "cancelled": statuses["CANCELLED"],
        "popular_services": popular,
        "worker_performance": worker_performance,
        "chart_labels": [x["service__name"] for x in popular],
        "chart_values": [x["total"] for x in popular],
        "status_values": [statuses[s] for s in Appointment.Status.values],
    }
    return render(request, "owner/reports.html", context)


@owner_required
def download_report(request):
    appts = scoped(request, Appointment.objects.select_related("customer", "salon", "staff", "service", "payment").order_by("-appointment_date"))
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="deepa-beauty-parlour-sales-report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Time", "Customer", "Service", "Price", "Worker/Staff", "Payment Method", "Txn ID", "Payment Status", "Booking Status", "Worker Completed"])
    for a in appts:
        worker_name = a.staff.name if a.staff else "Unassigned"
        pay_method = a.payment.get_payment_method_display() if hasattr(a, "payment") else "—"
        txn_id = a.payment.transaction_id if hasattr(a, "payment") else "—"
        pay_status = a.payment.get_status_display() if hasattr(a, "payment") else "—"
        price = a.service.price if a.service else 0
        worker_done = "Yes" if a.worker_completed else "No"
        writer.writerow([a.appointment_date, a.appointment_time, a.customer.username, a.service.name, price, worker_name, pay_method, txn_id, pay_status, a.status, worker_done])
    return response


@owner_required
def user_list(request):
    users = User.objects.all().annotate(total_bookings=Count("appointments")).order_by("-id")
    role = request.GET.get("role")
    if role:
        users = users.filter(role=role)
    q = request.GET.get("q")
    if q:
        users = users.filter(
            models.Q(username__icontains=q)
            | models.Q(first_name__icontains=q)
            | models.Q(email__icontains=q)
            | models.Q(phone__icontains=q)
        )
    return render(request, "owner/users.html", {
        "users": users,
        "total_users": User.objects.count(),
        "customer_count": User.objects.filter(role=User.Role.CUSTOMER).count(),
        "staff_count": User.objects.filter(role=User.Role.STAFF).count(),
        "admin_count": User.objects.filter(role__in=[User.Role.ADMIN, User.Role.OWNER]).count(),
    })


@owner_required
def delete_user(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if user_to_delete.id == request.user.id:
            messages.error(request, "You cannot delete your own logged-in admin account.")
            return redirect("owner_users")
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"User account '{username}' has been deleted successfully.")
    return redirect("owner_users")

