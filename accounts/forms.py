from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User

from django.contrib.auth import authenticate

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Mail ID",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username or Mail ID",
            "autocomplete": "username"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password",
            "autocomplete": "current-password"
        })
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username and password:
            if "@" in username:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj:
                    username = user_obj.username
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Name",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your full name",
            "autocomplete": "name"
        })
    )
    email = forms.EmailField(
        label="Mail ID",
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "name@example.com",
            "autocomplete": "email"
        })
    )
    phone = forms.CharField(
        label="Phone number",
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter mobile number",
            "inputmode": "tel",
            "autocomplete": "tel"
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control password-input",
            "placeholder": "Choose a password",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control password-input",
            "placeholder": "Confirm your password",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "email",
            "phone",
            "password1",
            "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this Mail ID already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not all(character.isdigit() or character in "+- ()" for character in phone):
            raise forms.ValidationError("Use only numbers and standard phone symbols.")
        if phone and not 7 <= sum(character.isdigit() for character in phone) <= 15:
            raise forms.ValidationError("Enter a phone number with 7 to 15 digits.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        import re
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.email = self.cleaned_data["email"]
        user.phone = self.cleaned_data["phone"]
        user.role = User.Role.CUSTOMER

        # Auto-generate unique username based on name or email
        clean_name = re.sub(r'[^a-zA-Z0-9_.]', '', user.first_name.lower().replace(" ", ""))
        base_username = clean_name or user.email.split("@")[0].lower()
        base_username = re.sub(r'[^a-zA-Z0-9_.]', '', base_username) or "user"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username

        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class ProfileForm(forms.ModelForm):

    class Meta:

        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
        ]

        widgets = {

            "first_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "last_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "email": forms.EmailInput(attrs={
                "class": "form-control"
            }),

        }
