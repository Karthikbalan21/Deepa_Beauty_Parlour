from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_add_service_manager_role")]
    operations = [
        migrations.AlterField(
            model_name="user", name="role",
            field=models.CharField(choices=[("CUSTOMER", "Customer"), ("OWNER", "Salon Owner"), ("STAFF", "Staff"), ("SERVICE_MANAGER", "Service Management"), ("ADMIN", "Admin")], default="CUSTOMER", max_length=20),
        ),
    ]
