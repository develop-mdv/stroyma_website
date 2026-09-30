"""Глобальные обработчики ошибок HTTP."""
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from django.template.response import TemplateResponse


def pwa_manifest(request):
    content = (settings.BASE_DIR / 'static' / 'pwa' / 'manifest.webmanifest').read_bytes()
    response = HttpResponse(content, content_type='application/manifest+json; charset=utf-8')
    response['Cache-Control'] = 'public, max-age=3600'
    return response


def service_worker(request):
    content = (settings.BASE_DIR / 'static' / 'js' / 'service-worker.js').read_bytes()
    response = HttpResponse(content, content_type='text/javascript; charset=utf-8')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Service-Worker-Allowed'] = '/'
    return response


def error_response(status):
    # Keep error pages independent of database-backed context processors.
    response = HttpResponse(get_template(f'{status}.html').render(), status=status)
    response['Cache-Control'] = 'no-store, private'
    response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    return response


def handler400(request, exception=None):
    return error_response(400)


def handler404(request, exception=None):
    return error_response(404)


def handler500(request):
    return error_response(500)


def handler403(request, exception=None):
    return error_response(403)


def csrf_failure(request, reason=''):
    return error_response(403)


def robots_txt(request):
    """
    robots.txt is environment-sensitive:
    - production: allow indexing + point Sitemap to canonical SITE_URL
    - non-production: disallow all
    """
    if not getattr(settings, 'ALLOW_ROBOTS_INDEXING', False):
        return TemplateResponse(
            request,
            'robots.txt',
            {
                'disallow_all': True,
                'sitemap_url': '',
                'admin_path': '/' + settings.ADMIN_URL,
            },
            content_type='text/plain; charset=utf-8',
        )

    site_url = (getattr(settings, 'SITE_URL', '') or '').strip().rstrip('/')
    sitemap_url = urljoin(site_url + '/', 'sitemap.xml') if site_url else ''

    admin_url = (getattr(settings, 'ADMIN_URL', 'management-stroyma-7x4/') or 'management-stroyma-7x4/').strip()
    admin_url = admin_url.lstrip('/')
    if not admin_url.endswith('/'):
        admin_url += '/'
    admin_path = '/' + admin_url

    return TemplateResponse(
        request,
        'robots.txt',
        {
            'disallow_all': False,
            'sitemap_url': sitemap_url,
            'admin_path': admin_path,
        },
        content_type='text/plain; charset=utf-8',
    )
