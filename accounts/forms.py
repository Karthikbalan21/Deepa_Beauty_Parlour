from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Username"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )

class RegisterForm(UserCreationForm):

    password1 = forms.CharField(
        label="Password",
        help_text="Choose a password you will remember.",
        widget=forms.PasswordInput(attrs={
            "class": "form-control password-input",
            "placeholder": "Choose a password",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Confirm password",
        help_text="Enter the same password again.",
        widget=forms.PasswordInput(attrs={
            "class": "form-control password-input",
            "placeholder": "Confirm your password",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "phone",
            "role",
            "password1",
            "password2",
        ]

        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Choose a username", "autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone number (optional)", "inputmode": "tel", "autocomplete": "tel"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not all(character.isdigit() or character in "+- ()" for character in phone):
            raise forms.ValidationError("Use only numbers and standard phone symbols.")
        if phone and not 7 <= sum(character.isdigit() for character in phone) <= 15:
            raise forms.ValidationError("Enter a phone number with 7 to 15 digits.")
        return phone

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
