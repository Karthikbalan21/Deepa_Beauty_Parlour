from django.contrib.auth.decorators import user_passes_test


def owner_required(view_func):

    decorated_view = user_passes_test(
        lambda user: user.is_authenticated and (user.role in ["ADMIN", "OWNER", "SERVICE_MANAGER"] or user.is_superuser or user.is_staff),
        login_url="/accounts/login/"
    )

    return decorated_view(view_func)
