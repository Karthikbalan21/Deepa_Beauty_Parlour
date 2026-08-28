from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("salons", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.AddField(model_name="staff", name="user", field=models.OneToOneField(blank=True, help_text="Login account used by this staff member", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staff_profile", to=settings.AUTH_USER_MODEL))]
