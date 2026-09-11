from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import LoginForm, RegisterForm, ProfileForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

    def get_success_url(self):
        role = self.request.user.role

        if role in ["OWNER", "ADMIN"] or self.request.user.is_superuser:
            return "/owner/"

        elif role == "STAFF":
            # Staff dashboard is role-aware under the shared dashboard route.
            return reverse("dashboard")

        return "/dashboard/"


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            messages.success(
                request,
                "Registration Successful."
            )

            return redirect("dashboard")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )


@login_required
def profile(request):
    return render(
        request,
        "accounts/profile.html",
        {
            "user": request.user
        }
    )


@login_required
def edit_profile(request):

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Profile updated successfully."
            )

            return redirect("profile")

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "form": form
        }
    )
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")
