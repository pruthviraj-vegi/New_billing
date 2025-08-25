from django.conf import settings
from django.shortcuts import redirect
import re


class CustomLoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the path is exempt from login requirement
        path = request.path_info.lstrip("/")

        # Exempt static files, media files, and login page
        if any(re.match(pattern, path) for pattern in settings.LOGIN_EXEMPT_URLS):
            return self.get_response(request)

        # Check if user is authenticated
        if not request.user.is_authenticated:
            # Store the original URL to redirect back after login
            request.session["next"] = request.path
            return redirect("base:login")

        return self.get_response(request)
