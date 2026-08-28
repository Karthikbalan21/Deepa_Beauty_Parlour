from django.urls import path

from .views import (
    UserLoginView,
    register,
    logout_view,
    profile,
    edit_profile,
)

urlpatterns = [
    path(
        "login/",
        UserLoginView.as_view(),
        name="login"
    ),
    path(
        "register/",
        register,
        name="register"
    ),
    path(
        "profile/",
        profile,
        name="profile"
    ),
    path(
    "profile/edit/",
    edit_profile,
    name="edit_profile"
),
    path(
        "logout/",
        logout_view,
        name="logout"
    ),
]