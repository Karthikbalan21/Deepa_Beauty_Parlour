from datetime import time

from django.core.management.base import BaseCommand

from accounts.models import User
from salons.models import Salon, Staff
from services.models import Service
from services.catalog import SERVICE_CATALOG


class Command(BaseCommand):
    help = "Create ten clearly labelled demo salons, staff profiles, and services."

    def handle(self, *args, **options):
        for number in range(1, 11):
            suffix = f"{number:02d}"
            owner, owner_created = User.objects.get_or_create(
                username=f"demo_owner_{suffix}",
                defaults={"role": User.Role.OWNER, "email": f"owner{suffix}@deepabeautyparlour.demo"},
            )
            if owner_created:
                owner.set_password("DemoOwner123!")
                owner.save(update_fields=["password"])
            salon, _ = Salon.objects.update_or_create(
                owner=owner,
                defaults={
                    "name": f"Deepa Beauty Parlour Demo Salon {suffix}", "description": "A demonstration salon for testing bookings.",
                    "phone": f"9000000{number:03d}", "email": f"salon{suffix}@deepabeautyparlour.demo", "address": f"{number} Demo Avenue",
                    "city": "Pune", "state": "Maharashtra", "pincode": f"4110{number:02d}",
                    "opening_time": time(9), "closing_time": time(19), "upi_id": f"deepabeautyparlour.demo{suffix}@upi", "is_active": True,
                },
            )
            staff_user, staff_created = User.objects.get_or_create(
                username=f"demo_staff_{suffix}",
                defaults={"role": User.Role.STAFF, "phone": f"8000000{number:03d}"},
            )
            if staff_created:
                staff_user.set_password("DemoStaff123!")
                staff_user.save(update_fields=["password"])
            Staff.objects.update_or_create(
                salon=salon,
                defaults={"user": staff_user, "name": f"Demo Stylist {suffix}", "phone": f"8000000{number:03d}", "specialization": "Hair & Beauty", "experience": number, "is_available": True},
            )
            for name, duration, price in SERVICE_CATALOG:
                Service.objects.update_or_create(
                    salon=salon,
                    name=name,
                    defaults={"description": "A Deepa Beauty Parlour service.", "duration": duration, "price": price, "is_available": True},
                )
        self.stdout.write(self.style.SUCCESS("Demo data ready: 10 salons, staff members, and the full service catalogue."))
