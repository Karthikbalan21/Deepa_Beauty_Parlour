from django.contrib.auth.decorators import user_passes_test


def owner_required(view_func):

    decorated_view = user_passes_test(
        lambda user: user.is_authenticated and user.role in ["OWNER", "SERVICE_MANAGER"],
        login_url="/accounts/login/"
    )

    return decorated_view(view_func)
