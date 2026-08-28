from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):

    class Meta:
        model = Service

        fields = [
            "name",
            "price",
            "duration",
            "description", "image", "is_available",
        ]

        widgets = {

            "name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "price": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "duration": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4
            }),

        }
