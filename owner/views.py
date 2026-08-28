import csv
from datetime import timedelta
from django.contrib import messages
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .decorators import owner_required
from appointments.models import Appointment, Payment, LoyaltyTransaction
from salons.models import Staff
from services.models import Service
from services.forms import ServiceForm
from accounts.models import User
from salons.forms import StaffForm

def scoped(request, qs):
    # Owners see their salon data when they own one; platform owners retain global overview.
    if hasattr(request.user, "salon"): return qs.filter(salon=request.user.salon)
    return qs

@owner_required
def owner_dashboard(request):
    today = timezone.localdate()
    appointments = scoped(request, Appointment.objects.all())
    payments = Payment.objects.filter(
        appointment__in=appointments,
        appointment__status=Appointment.Status.COMPLETED,
        status=Payment.Status.VERIFIED,
    )
    month = today.replace(day=1)
    completed = appointments.filter(status=Appointment.Status.COMPLETED)
    total = appointments.count()
    health = min(100, round((completed.count() / total * 45 if total else 0) + (payments.filter(appointment__appointment_date__gte=month).count() / max(1, appointments.filter(appointment_date__gte=month).count()) * 35) + 20))
    status_counts = {status: appointments.filter(status=status).count() for status in Appointment.Status.values}
    top_staff = payments.values("appointment__staff__name").annotate(total=Sum("amount")).order_by("-total").first()
    popular_services = appointments.values("service__name").annotate(total=Count("id")).order_by("-total")[:5]
    context = {"total_customers": appointments.values("customer").distinct().count(), "today_appointments": appointments.filter(appointment_date=today).count(), "today_revenue": payments.filter(appointment__appointment_date=today).aggregate(v=Sum("amount"))["v"] or 0, "monthly_revenue": payments.filter(appointment__appointment_date__gte=month).aggregate(v=Sum("amount"))["v"] or 0, "total_staff": scoped(request, Staff.objects.all()).count(), "total_services": scoped(request, Service.objects.all()).count(), "pending_payments": Payment.objects.filter(appointment__in=appointments, status="PENDING").count(), "verified_payments": payments.count(), "cancelled": status_counts[Appointment.Status.CANCELLED], "completed": completed.count(), "health": health, "top_staff": top_staff, "popular_services": popular_services, "status_labels": list(status_counts.keys()), "status_values": list(status_counts.values()), "recent": appointments.select_related("customer", "service", "staff").order_by("-created_at")[:6]}
    return render(request, "owner/dashboard.html", context)

@owner_required
def appointment_list(request):
    appointments = scoped(request, Appointment.objects.select_related("customer", "salon", "service", "staff", "payment"))
    for field in ("status", "staff", "service", "salon"):
        if request.GET.get(field): appointments = appointments.filter(**{field if field == "status" else field + "_id": request.GET[field]})
    if request.GET.get("date"): appointments = appointments.filter(appointment_date=request.GET["date"])
    if request.GET.get("payment"): appointments = appointments.filter(payment__status=request.GET["payment"])
    return render(request, "owner/appointments.html", {"appointments": appointments.order_by("-appointment_date", "-appointment_time"), "staffs": scoped(request, Staff.objects.all()), "services": scoped(request, Service.objects.all())})

@owner_required
def update_appointment(request, pk, status):
    appointment = get_object_or_404(scoped(request, Appointment.objects.all()), pk=pk)
    if request.method == "POST" and status in Appointment.Status.values:
        if status in [Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED] and (not hasattr(appointment, "payment") or appointment.payment.status != Payment.Status.VERIFIED):
            messages.error(request, "This appointment cannot be confirmed until its payment is verified.")
            return redirect("owner_appointments")
        appointment.status = status; appointment.save()
        if status == Appointment.Status.COMPLETED and not LoyaltyTransaction.objects.filter(appointment=appointment).exists():
            visits = Appointment.objects.filter(customer=appointment.customer, status=Appointment.Status.COMPLETED).count()
            if visits > 3: LoyaltyTransaction.objects.create(customer=appointment.customer, appointment=appointment, points=10, note="Loyalty reward for completed salon visit")
        if status == Appointment.Status.COMPLETED:
            from appointments.views import _refresh_trending
            _refresh_trending()
        messages.success(request, f"Appointment marked {appointment.get_status_display()}.")
    return redirect("owner_appointments")

@owner_required
def verify_payment(request, pk, decision):
    payment = get_object_or_404(Payment.objects.filter(appointment__in=scoped(request, Appointment.objects.all())), pk=pk)
    if request.method == "POST" and decision in [Payment.Status.VERIFIED, Payment.Status.REJECTED]:
        if decision == Payment.Status.VERIFIED and not payment.screenshot:
            messages.error(request, "A payment screenshot is required before verification.")
            return redirect("owner_appointments")
        payment.status = decision; payment.save()
        if decision == Payment.Status.VERIFIED:
            payment.appointment.status = Appointment.Status.CONFIRMED
            payment.appointment.save(update_fields=["status", "updated_at"])
        else:
            payment.appointment.status = Appointment.Status.CANCELLED
            payment.appointment.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Payment {payment.get_status_display().lower()}.")
    return redirect("owner_appointments")

@owner_required
def edit_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    form = ServiceForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service updated.")
        return redirect("owner_services")
    return render(request, "owner/add_service.html", {"form": form, "service": service})

@owner_required
def delete_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service deleted.")
    return redirect("owner_services")

@owner_required
def service_list(request): return render(request, "owner/services.html", {"services": scoped(request, Service.objects.all())})
@owner_required
def add_service(request):
    form = ServiceForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        service = form.save(commit=False)
        if hasattr(request.user, "salon"): service.salon = request.user.salon
        service.save(); messages.success(request, "Service saved."); return redirect("owner_services")
    return render(request, "owner/add_service.html", {"form": form})
@owner_required
def toggle_service(request, pk):
    service = get_object_or_404(scoped(request, Service.objects.all()), pk=pk)
    if request.method == "POST": service.is_available = not service.is_available; service.save(); messages.success(request, "Service availability updated.")
    return redirect("owner_services")
@owner_required
def staff_list(request): return render(request, "owner/staff.html", {"staffs": scoped(request, Staff.objects.all())})


@owner_required
def add_staff(request):
    if not hasattr(request.user, "salon"):
        messages.error(request, "Create or select a salon before adding staff.")
        return redirect("owner_staff")
    form = StaffForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        staff = form.save(salon=request.user.salon)
        messages.success(request, f"{staff.name} was added to your team.")
        return redirect("owner_staff")
    return render(request, "owner/add_staff.html", {"form": form})
@owner_required
def toggle_staff(request, pk):
    staff = get_object_or_404(scoped(request, Staff.objects.all()), pk=pk)
    if request.method == "POST": staff.is_available = not staff.is_available; staff.save(); messages.success(request, "Staff availability updated.")
    return redirect("owner_staff")
@owner_required
def reports(request):
    appts = scoped(request, Appointment.objects.all())
    statuses = {s: appts.filter(status=s).count() for s in Appointment.Status.values}
    popular = appts.values("service__name").annotate(total=Count("id")).order_by("-total")[:5]
    return render(request, "owner/reports.html", {"total": appts.count(), "pending": statuses["PENDING"], "confirmed": statuses["CONFIRMED"], "completed": statuses["COMPLETED"], "cancelled": statuses["CANCELLED"], "chart_labels": [x["service__name"] for x in popular], "chart_values": [x["total"] for x in popular], "status_values": [statuses[s] for s in Appointment.Status.values]})
@owner_required
def download_report(request):
    appts = scoped(request, Appointment.objects.select_related("customer", "salon", "staff", "service").order_by("-appointment_date"))
    response = HttpResponse(content_type="text/csv"); response["Content-Disposition"] = 'attachment; filename="salon-appointments-report.csv"'
    writer = csv.writer(response); writer.writerow(["Date", "Time", "Customer", "Salon", "Staff", "Service", "Status"])
    for a in appts: writer.writerow([a.appointment_date, a.appointment_time, a.customer.username, a.salon.name, a.staff.name, a.service.name, a.status])
    return response
