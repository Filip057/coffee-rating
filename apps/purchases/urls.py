from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'purchases'

# Router for ViewSets
# Note: shares must be registered BEFORE empty prefix to avoid URL conflicts
router = DefaultRouter()
router.register(r'personal', views.PersonalPurchaseViewSet, basename='personal-purchase')
router.register(r'group', views.GroupPurchaseViewSet, basename='group-purchase')
router.register(r'shares', views.PaymentShareViewSet, basename='share')
router.register(r'', views.PurchaseRecordViewSet, basename='purchase')  # Legacy, keep for now

urlpatterns = [
    # Purchase ViewSet routes
    # GET    /api/purchases/              - List purchases
    # POST   /api/purchases/              - Create purchase (with split)
    # GET    /api/purchases/{id}/         - Get purchase details
    # PUT    /api/purchases/{id}/         - Update purchase
    # PATCH  /api/purchases/{id}/         - Partial update
    # DELETE /api/purchases/{id}/         - Delete purchase
    
    # Custom purchase actions
    # GET    /api/purchases/{id}/summary/   - Get payment summary
    # GET    /api/purchases/{id}/shares/    - Get all payment shares
    # POST   /api/purchases/{id}/mark_paid/ - Mark share as paid
    
    # Payment Share routes
    # GET    /api/purchases/shares/           - List payment shares
    # GET    /api/purchases/shares/{id}/      - Get share details
    # GET    /api/purchases/shares/{id}/qr_code/ - Get QR code
    
    # Additional endpoints
    path('my_outstanding/', views.my_outstanding_payments, name='my-outstanding'),
    
    # Include router URLs
    path('', include(router.urls)),
]