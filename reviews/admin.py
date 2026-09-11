from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("customer", "service", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("customer__username", "comments")

