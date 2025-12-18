from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from drf_spectacular.utils import extend_schema
from .models import PurchaseRecord, PaymentShare, PaymentStatus
from .serializers import (
    PurchaseRecordSerializer,
    PurchaseRecordCreateSerializer,
    PurchaseRecordListSerializer,
    PaymentShareSerializer,
    PurchaseSummarySerializer,
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


class PurchaseRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PurchaseRecord CRUD operations.
    
    list: Get all purchases (filterable by user/group)
    create: Create a new purchase (with payment split for groups)
    retrieve: Get a specific purchase
    update: Update a purchase
    destroy: Delete a purchase
    """
    
    queryset = PurchaseRecord.objects.select_related(
        'bought_by',
        'group',
        'coffeebean',
        'variant'
    ).prefetch_related('payment_shares')
    serializer_class = PurchaseRecordSerializer
    permission_classes = [IsAuthenticated, IsGroupMemberForPurchase]
    pagination_class = PurchasePagination

    def get_permissions(self):
        """Use different permissions for different actions."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManagePurchase()]
        elif self.action == 'mark_paid':
            return [IsAuthenticated(), CanMarkPaymentPaid()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter purchases using input serializer validation."""
        queryset = super().get_queryset()
        user = self.request.user

        # Validate query parameters using input serializer
        filter_serializer = PurchaseFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        params = filter_serializer.validated_data

        # Apply filters based on validated params
        group_id = params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        else:
            # Show purchases where user is involved (bought or has payment share)
            queryset = queryset.filter(
                models.Q(bought_by=user) |
                models.Q(payment_shares__user=user)
            ).distinct()

        # Filter by user
        user_id = params.get('user')
        if user_id:
            queryset = queryset.filter(
                models.Q(bought_by_id=user_id) |
                models.Q(payment_shares__user_id=user_id)
            ).distinct()

        # Filter by date range
        if 'date_from' in params:
            queryset = queryset.filter(date__gte=params['date_from'])
        if 'date_to' in params:
            queryset = queryset.filter(date__lte=params['date_to'])

        # Filter by payment status
        if 'is_fully_paid' in params:
            queryset = queryset.filter(is_fully_paid=params['is_fully_paid'])

        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return PurchaseRecordListSerializer
        elif self.action == 'create':
            return PurchaseRecordCreateSerializer
        return PurchaseRecordSerializer
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create purchase with payment split (if group purchase).
        """
        split_members = serializer.validated_data.pop('split_members', None)
        group = serializer.validated_data.get('group')
        
        if group:
            # Group purchase - use split service
            purchase, shares = PurchaseSplitService.create_group_purchase(
                group_id=group.id,
                bought_by_user=self.request.user,
                total_price_czk=serializer.validated_data['total_price_czk'],
                date=serializer.validated_data['date'],
                coffeebean=serializer.validated_data.get('coffeebean'),
                variant=serializer.validated_data.get('variant'),
                package_weight_grams=serializer.validated_data.get('package_weight_grams'),
                note=serializer.validated_data.get('note', ''),
                split_members=split_members
            )
            
            # Generate QR codes if bank details configured
            bank_iban = getattr(settings, 'PAYMENT_QR_BANK_IBAN', None)
            recipient_name = getattr(settings, 'PAYMENT_RECIPIENT_NAME', 'Coffee Group')
            
            if bank_iban:
                for share in shares:
                    try:
                        SPDPaymentGenerator.generate_for_payment_share(
                            share=share,
                            bank_iban=bank_iban,
                            recipient_name=recipient_name
                        )
                    except Exception as e:
                        # Log error but don't fail the purchase
                        print(f"Failed to generate QR for share {share.id}: {e}")
            
            return purchase
        else:
            # Personal purchase - no split
            return serializer.save(bought_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get detailed summary of purchase and payment status.
        
        GET /api/purchases/{id}/summary/
        """
        purchase = self.get_object()
        summary = PurchaseSplitService.get_purchase_summary(purchase.id)
        serializer = PurchaseSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def shares(self, request, pk=None):
        """
        Get all payment shares for this purchase.
        
        GET /api/purchases/{id}/shares/
        """
        purchase = self.get_object()
        shares = purchase.payment_shares.select_related('user', 'paid_by')
        serializer = PaymentShareSerializer(shares, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """
        Mark a payment share as paid.

        POST /api/purchases/{id}/mark_paid/
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


# Fix import
from django.db import models