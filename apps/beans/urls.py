from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'beans'

# Router for ViewSets
# Note: variants must be registered BEFORE empty prefix to avoid URL conflicts
router = DefaultRouter()
router.register(r'variants', views.CoffeeBeanVariantViewSet, basename='variant')
router.register(r'', views.CoffeeBeanViewSet, basename='coffeebean')

urlpatterns = [
    # Bean ViewSet routes
    # GET    /api/beans/              - List all beans
    # POST   /api/beans/              - Create bean
    # GET    /api/beans/{id}/         - Get bean details
    # PUT    /api/beans/{id}/         - Update bean
    # PATCH  /api/beans/{id}/         - Partial update
    # DELETE /api/beans/{id}/         - Deactivate bean
    
    # Custom actions
    # GET    /api/beans/roasteries/   - List all roasteries
    # GET    /api/beans/origins/      - List all origin countries
    
    # Variant routes
    # GET    /api/beans/variants/           - List all variants
    # POST   /api/beans/variants/           - Create variant
    # GET    /api/beans/variants/{id}/      - Get variant
    # PATCH  /api/beans/variants/{id}/      - Update variant
    # DELETE /api/beans/variants/{id}/      - Deactivate variant
    
    # Include router URLs
    path('', include(router.urls)),
]