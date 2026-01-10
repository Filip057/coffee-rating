from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from decimal import Decimal
from drf_spectacular.utils import extend_schema
from .models import (
    PaymentShare, PaymentStatus,
    PersonalPurchase, GroupPurchase
)
from .serializers import (
    PaymentShareSerializer,
    # New serializers
    PersonalPurchaseSerializer,
    PersonalPurchaseCreateSerializer,
    GroupPurchaseSerializer,
    GroupPurchaseCreateSerializer,
    # Input serializers (Phase 2)
    PurchaseFilterSerializer,
    PaymentShareFilterSerializer,
    MarkPaidInputSerializer,
)
from .services import PurchaseSplitService, SPDPaymentGenerator
from .permissions import (
    IsGroupMemberForPurchase,
    CanManagePurchase,
    CanMarkPaymentPaid,
    IsGroupMemberForShare,
)
from apps.groups.models import Group
from django.conf import settings


# Response serializers for API documentation
class OutstandingPaymentsResponseSerializer(drf_serializers.Serializer):
    total_outstanding = drf_serializers.DecimalField(max_digits=10, decimal_places=2)
    count = drf_serializers.IntegerField()
    shares = PaymentShareSerializer(many=True)


class PurchasePagination(PageNumberPagination):
    """Custom pagination for purchases."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaymentShareViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for PaymentShare operations (read-only).
    
    list: Get all payment shares (for current user)
    retrieve: Get a specific payment share
    """
    
    queryset = PaymentShare.objects.select_related('purchase', 'user', 'paid_by')
    serializer_class = PaymentShareSerializer
    permission_classes = [IsAuthenticated, IsGroupMemberForShare]
    pagination_class = PurchasePagination
    
    def get_queryset(self):
        """Filter payment shares using input serializer validation."""
        user = self.request.user

        # Validate query parameters using input serializer
        filter_serializer = PaymentShareFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        params = filter_serializer.validated_data

        # Get user's own shares or shares in their groups
        queryset = PaymentShare.objects.filter(
            models.Q(user=user) |
            models.Q(purchase__group__memberships__user=user)
        ).select_related('purchase', 'user', 'paid_by').distinct()

        # Apply filters based on validated params
        if 'status' in params:
            queryset = queryset.filter(status=params['status'])
        if 'purchase' in params:
            queryset = queryset.filter(purchase_id=params['purchase'])

        return queryset
    
    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """
        Get QR code for payment share.
        
        GET /api/shares/{id}/qr_code/
        """
        share = self.get_object()
        
        if not share.qr_image_path:
            return Response(
                {'error': 'QR code not generated for this share'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return QR code info
        return Response({
            'qr_url': share.qr_url,
            'qr_image_path': share.qr_image_path,
            'payment_reference': share.payment_reference,
            'amount_czk': share.amount_czk,
        })


# =============================================================================
# NEW: Personal Purchase ViewSet
# =============================================================================


class PersonalPurchaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PersonalPurchase CRUD operations.

    list: Get all personal purchases for current user
    create: Create a new personal purchase
    retrieve: Get a specific personal purchase
    update: Update a personal purchase
    destroy: Delete a personal purchase
    """

    serializer_class = PersonalPurchaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PurchasePagination

    def get_queryset(self):
        """Filter to only current user's personal purchases."""
        return PersonalPurchase.objects.filter(user=self.request.user).select_related(
            'coffeebean',
            'variant'
        )

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return PersonalPurchaseCreateSerializer
        return PersonalPurchaseSerializer

    def perform_create(self, serializer):
        """Set user to current user."""
        serializer.save(user=self.request.user)


# =============================================================================
# NEW: Group Purchase ViewSet
# =============================================================================


class GroupPurchaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GroupPurchase CRUD operations.

    list: Get all group purchases user is involved in
    create: Create a new group purchase with payment splitting
    retrieve: Get a specific group purchase
    update: Update a group purchase
    destroy: Delete a group purchase
    """

    serializer_class = GroupPurchaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PurchasePagination

    def get_queryset(self):
        """Filter to purchases where user is a group member or has a payment share."""
        user = self.request.user
        return GroupPurchase.objects.filter(
            models.Q(group__memberships__user=user) |
            models.Q(payment_shares__user=user)
        ).select_related(
            'group',
            'bought_by',
            'coffeebean',
            'variant'
        ).prefetch_related('payment_shares').distinct()

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return GroupPurchaseCreateSerializer
        return GroupPurchaseSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create group purchase with payment splitting.
        Auto-marks buyer's share as paid.
        """
        split_members = serializer.validated_data.pop('split_members', None)
        group = serializer.validated_data['group']
        bought_by = serializer.validated_data['bought_by']

        # Create purchase
        purchase = serializer.save()

        # Create payment shares
        shares = PurchaseSplitService.create_group_purchase(
            group_id=group.id,
            bought_by_user=bought_by,
            total_price_czk=purchase.total_price_czk,
            date=purchase.date,
            coffeebean=purchase.coffeebean,
            variant=purchase.variant,
            package_weight_grams=purchase.package_weight_grams,
            note=purchase.note,
            split_members=split_members
        )

        # Auto-mark buyer's share as PAID
        buyer_share = purchase.payment_shares.filter(user=bought_by).first()
        if buyer_share:
            from django.utils import timezone
            buyer_share.status = PaymentStatus.PAID
            buyer_share.paid_at = timezone.now()
            buyer_share.paid_by = bought_by
            buyer_share.save()

            # Update purchase collection status
            purchase.update_collection_status()

        return purchase

    @action(detail=True, methods=['get'])
    def shares(self, request, pk=None):
        """
        Get all payment shares for this purchase.

        GET /api/purchases/group/{id}/shares/
        """
        purchase = self.get_object()
        shares = purchase.payment_shares.select_related('user', 'paid_by')
        serializer = PaymentShareSerializer(shares, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """
        Mark a payment share as paid.

        POST /api/purchases/group/{id}/mark_paid/
        Body: {"payment_reference": "COFFEE-...", "note": "optional"}
        """
        purchase = self.get_object()

        # Validate input
        input_serializer = MarkPaidInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        payment_reference = input_serializer.validated_data.get('payment_reference')

        # Use service method for payment reconciliation
        share = PurchaseSplitService.mark_purchase_paid(
            purchase_id=purchase.id,
            payment_reference=payment_reference,
            user=request.user if not payment_reference else None
        )

        return Response(PaymentShareSerializer(share).data)


@extend_schema(
    responses={200: OutstandingPaymentsResponseSerializer},
    description="Get all outstanding (unpaid) payment shares for the current user.",
    tags=['purchases'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_outstanding_payments(request):
    """Get all outstanding payments for current user."""
    shares = PaymentShare.objects.filter(
        user=request.user,
        status=PaymentStatus.UNPAID
    ).select_related('purchase', 'purchase__coffeebean').order_by('created_at')
    
    serializer = PaymentShareSerializer(shares, many=True)
    
    # Calculate total outstanding
    total_outstanding = sum(share.amount_czk for share in shares)
    
    return Response({
        'total_outstanding': total_outstanding,
        'count': shares.count(),
        'shares': serializer.data
    })