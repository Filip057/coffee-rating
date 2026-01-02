from django.http import JsonResponse, FileResponse, Http404
from django.conf import settings


def serve_frontend(request, page='login.html', **kwargs):
    """Serve frontend HTML pages."""
    # Map clean URLs to HTML files
    page_map = {
        '': 'login.html',
        'login': 'login.html',
        'dashboard': 'dashboard.html',
        'register': 'register.html',
        'groups/create': 'groups_create.html',
        'groups/list': 'groups_list.html',
        'group_detail': 'group_detail.html',
        'library': 'library.html',
        'beans': 'beans.html',
        'bean_detail': 'bean_detail.html',
        'reviews/create': 'review_create.html',
        'profile': 'profile.html',
        'purchases': 'purchases.html',
        'purchases/create': 'purchase_create.html',
    }

    # Get the actual filename
    filename = page_map.get(page, f'{page}.html' if not page.endswith('.html') else page)
    filepath = settings.FRONTEND_DIR / filename

    if filepath.exists() and filepath.is_file():
        return FileResponse(open(filepath, 'rb'), content_type='text/html')

    raise Http404(f'Page not found: {page}')


def error_404(request, exception):
    """Custom 404 handler."""
    return JsonResponse({
        'error': 'Not found',
        'status': 404
    }, status=404)


def error_500(request):
    """Custom 500 handler."""
    return JsonResponse({
        'error': 'Internal server error',
        'status': 500
    }, status=500)