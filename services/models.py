from django.db import models
from salons.models import Salon


class Service(models.Model):

    salon = models.ForeignKey(
        Salon,
        on_delete=models.CASCADE,
        related_name="services"
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField(
        help_text="Duration in minutes"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    image = models.ImageField(
        upload_to="services/",
        blank=True,
        null=True
    )

    is_available = models.BooleanField(default=True)
    is_trending = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
