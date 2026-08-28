from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("salons", "0002_staff_user")]
    operations = [
        migrations.AddField(model_name="salon", name="upi_id", field=models.CharField(blank=True, help_text="UPI ID used for payment QR codes", max_length=100)),
        migrations.AddField(model_name="salon", name="payment_qr", field=models.ImageField(blank=True, null=True, upload_to="payment_qr/")),
    ]
