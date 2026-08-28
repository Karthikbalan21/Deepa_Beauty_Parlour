from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("appointments", "0003_premium_booking_features")]

    operations = [
        migrations.RemoveField(model_name="appointment", name="queue_token"),
        migrations.RemoveField(model_name="appointment", name="queued"),
    ]
