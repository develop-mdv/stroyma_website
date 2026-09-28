"""Response protections for account data and rate-limited requests."""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django_ratelimit.exceptions import Ratelimited

from .views import error_response


class PrivateResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code in (400, 403, 404, 405, 429, 500) and response.get('Content-Type', '').startswith('text/html'):
            replacement = error_response(response.status_code)
            if response.has_header('Allow'):
                replacement['Allow'] = response['Allow']
            response = replacement
        admin_path = '/' + settings.ADMIN_URL.lstrip('/')
        private_path = request.path.startswith(('/accounts/', '/cart/', '/checkout/', admin_path))
        error = response.status_code >= 400
        if private_path or error:
            response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        if private_path or error or request.user.is_authenticated or request.session.get('cart'):
            response['Cache-Control'] = 'no-store, private'
        return response


class RateLimitResponseMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, Ratelimited):
            return error_response(429)
        return None
