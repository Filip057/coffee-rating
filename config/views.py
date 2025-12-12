from django.http import JsonResponse


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