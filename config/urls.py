"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

from config.views import serve_frontend, health_check

urlpatterns = [
    # Health check (for Render)
    path('api/health/', health_check, name='health-check'),

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),

    # Authentication
    path('api/auth/', include('apps.accounts.urls')),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API endpoints
    path('api/beans/', include('apps.beans.urls')),
    path('api/reviews/', include('apps.reviews.urls')),
    path('api/groups/', include('apps.groups.urls')),
    path('api/purchases/', include('apps.purchases.urls')),
    path('api/analytics/', include('apps.analytics.urls')),

    # Frontend pages
    path('', serve_frontend, name='home'),
    path('login', serve_frontend, {'page': 'login'}, name='login'),
    path('login.html', serve_frontend, {'page': 'login'}, name='login-html'),
    path('dashboard', serve_frontend, {'page': 'dashboard'}, name='dashboard'),
    path('dashboard/', serve_frontend, {'page': 'dashboard'}, name='dashboard-slash'),
    path('dashboard.html', serve_frontend, {'page': 'dashboard'}, name='dashboard-html'),
    path('register', serve_frontend, {'page': 'register'}, name='register'),
    path('register.html', serve_frontend, {'page': 'register'}, name='register-html'),
    path('groups/create/', serve_frontend, {'page': 'groups/create'}, name='groups-create'),
    path('groups/list/', serve_frontend, {'page': 'groups/list'}, name='groups-list'),
    path('groups/<uuid:group_id>/', serve_frontend, {'page': 'group_detail'}, name='group-detail'),
    path('library/', serve_frontend, {'page': 'library'}, name='library'),
    path('beans/', serve_frontend, {'page': 'beans'}, name='beans'),
    path('beans/create/', serve_frontend, {'page': 'beans/create'}, name='bean-create'),
    path('beans/<uuid:bean_id>/', serve_frontend, {'page': 'bean_detail'}, name='bean-detail'),
    path('reviews/create/', serve_frontend, {'page': 'reviews/create'}, name='review-create'),
    path('profile/', serve_frontend, {'page': 'profile'}, name='profile'),
    path('purchases/', serve_frontend, {'page': 'purchases'}, name='purchases'),
    path('purchases/create/', serve_frontend, {'page': 'purchases/create'}, name='purchase-create'),
]

# Media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Custom error handlers
handler404 = 'config.views.error_404'
handler500 = 'config.views.error_500'