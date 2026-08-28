from django.db import migrations


SERVICE_CATALOG = [
    ("Haircut & Hair Styling", 60, 500), ("Hair Wash & Blow Dry", 45, 400), ("Hair Spa", 60, 900),
    ("Hair Coloring", 120, 1800), ("Hair Straightening / Smoothening", 180, 3500), ("Keratin Treatment", 180, 4500),
    ("Facial", 60, 1000), ("Cleanup", 45, 600), ("Bleach", 30, 400), ("De-Tan Treatment", 45, 700),
    ("Threading – Eyebrows, Upper Lip, Forehead", 20, 150), ("Waxing – Full Body / Hands / Legs", 90, 1500),
    ("Manicure", 45, 600), ("Pedicure", 60, 800), ("Nail Art", 60, 700),
    ("Makeup – Party / Bridal / Engagement", 120, 3000), ("Saree Draping", 45, 700),
    ("Eyelash & Eyebrow Services", 45, 500), ("Mehndi / Henna", 60, 800), ("Bridal Grooming Packages", 240, 8000),
    ("Head Massage", 30, 400), ("Body Massage", 60, 1500), ("Skin Care Treatments", 60, 1200),
    ("Hair Treatments", 90, 1500), ("Bridal Services", 180, 5000), ("Bridal Makeup", 150, 6000),
    ("Hairstyling", 60, 1000), ("Bridal Facial", 75, 1800), ("Full Body Waxing", 90, 1800),
    ("Manicure & Pedicure", 90, 1300), ("Mehndi", 90, 1200), ("Pre-Bridal Packages", 300, 10000),
]


def add_catalog(apps, schema_editor):
    Salon = apps.get_model("salons", "Salon")
    Service = apps.get_model("services", "Service")
    for salon in Salon.objects.all():
        for name, duration, price in SERVICE_CATALOG:
            Service.objects.get_or_create(
                salon=salon,
                name=name,
                defaults={"description": "Deepa Beauty Parlour service.", "duration": duration, "price": price, "is_available": True},
            )


class Migration(migrations.Migration):
    dependencies = [("services", "0002_service_is_trending")]
    operations = [migrations.RunPython(add_catalog, migrations.RunPython.noop)]
