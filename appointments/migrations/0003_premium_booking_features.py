from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("appointments", "0002_alter_appointment_options"), ("accounts", "0001_initial")]
    operations = [
        migrations.AddField(model_name="appointment", name="loyalty_redeemed", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="appointment", name="queue_token", field=models.CharField(blank=True, max_length=12)),
        migrations.AddField(model_name="appointment", name="queued", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="appointment", name="rescheduled_from", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reschedules", to="appointments.appointment")),
        migrations.CreateModel(name="Coupon", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("code", models.CharField(max_length=30, unique=True)), ("description", models.CharField(max_length=160)), ("discount_percent", models.PositiveIntegerField(default=10)), ("active", models.BooleanField(default=True)), ("valid_until", models.DateField(blank=True, null=True))]),
        migrations.CreateModel(name="Payment", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("amount", models.DecimalField(decimal_places=2, max_digits=9)), ("razorpay_payment_id", models.CharField(blank=True, max_length=100)), ("screenshot", models.ImageField(blank=True, null=True, upload_to="payment_proofs/")), ("status", models.CharField(choices=[("PENDING", "Pending verification"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected")], default="PENDING", max_length=12)), ("created_at", models.DateTimeField(auto_now_add=True)), ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="payment", to="appointments.appointment"))]),
        migrations.CreateModel(name="LoyaltyTransaction", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("points", models.IntegerField()), ("note", models.CharField(max_length=180)), ("created_at", models.DateTimeField(auto_now_add=True)), ("appointment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="appointments.appointment")), ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="loyalty_transactions", to="accounts.user"))]),
    ]
