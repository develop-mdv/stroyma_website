"""Client address resolution at the trusted production proxy boundary."""

from ipaddress import ip_address

from django.conf import settings


def client_ip(request):
    peer = request.META.get('REMOTE_ADDR')
    if settings.TRUST_PROXY_CLIENT_IP and not settings.DEBUG:
        forwarded = request.META.get('HTTP_X_STROYMA_CLIENT_IP', '')
        try:
            return str(ip_address(forwarded))
        except ValueError:
            pass
    return peer
