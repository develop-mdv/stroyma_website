"""Глобальные обработчики ошибок HTTP."""
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
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


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)


def handler403(request, exception=None):
    return render(request, '403.html', status=403)


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
                'admin_path': '/admin/',
            },
            content_type='text/plain; charset=utf-8',
        )

    site_url = (getattr(settings, 'SITE_URL', '') or '').strip().rstrip('/')
    sitemap_url = urljoin(site_url + '/', 'sitemap.xml') if site_url else ''

    admin_url = (getattr(settings, 'ADMIN_URL', 'admin/') or 'admin/').strip()
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
