from django import forms
from accounts.models import User
from .models import Staff


class StaffForm(forms.ModelForm):
    """Owner form for a staff profile, with an optional staff login account."""

    username = forms.CharField(
        required=False,
        help_text="Optional. Create a login account for this staff member.",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Required when creating a staff login.",
    )

    class Meta:
        model = Staff
        fields = ["name", "phone", "specialization", "experience", "photo", "is_available"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "specialization": forms.TextInput(attrs={"class": "form-control"}),
            "experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "photo": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        username, password = cleaned.get("username"), cleaned.get("password")
        if username and User.objects.filter(username__iexact=username).exists():
            self.add_error("username", "This username is already in use.")
        if username and not password:
            self.add_error("password", "Enter a password to create this staff login.")
        if password and not username:
            self.add_error("username", "Enter a username for the staff login.")
        return cleaned

    def save(self, salon, commit=True):
        staff = super().save(commit=False)
        staff.salon = salon
        username = self.cleaned_data.get("username")
        if username:
            user = User.objects.create_user(
                username=username,
                password=self.cleaned_data["password"],
                role=User.Role.STAFF,
                phone=staff.phone,
                first_name=staff.name,
            )
            staff.user = user
        if commit:
            staff.save()
        return staff
