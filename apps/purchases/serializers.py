from rest_framework import serializers
from .models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant
from apps.groups.models import Group


# =============================================================================
# Input Serializers (Phase 2)
# =============================================================================

class PurchaseFilterSerializer(serializers.Serializer):
    """
    Validate query parameters for purchase filtering.

    Query Parameters:
        group (UUID): Filter by group ID
        user (UUID): Filter by user ID (bought or has share)
        date_from (date): Filter purchases from this date
        date_to (date): Filter purchases to this date
        is_fully_paid (bool): Filter by payment status
    """

    group = serializers.UUIDField(required=False)
    user = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    is_fully_paid = serializers.BooleanField(required=False)

    def validate(self, attrs):
        """Validate date range."""
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')

        if date_from and date_to:
            if date_from > date_to:
                raise serializers.ValidationError({
                    'date_to': 'End date must be after start date'
                })

        return attrs


class PaymentShareFilterSerializer(serializers.Serializer):
    """
    Validate query parameters for payment share filtering.

    Query Parameters:
        status (str): Filter by payment status
        purchase (UUID): Filter by purchase ID
    """

    status = serializers.ChoiceField(
        choices=PaymentStatus.choices,
        required=False
    )
    purchase = serializers.UUIDField(required=False)


class MarkPaidInputSerializer(serializers.Serializer):
    """
    Validate input for marking payment as paid.

    Fields:
        payment_reference (str): Optional payment reference to mark
        note (str): Optional note for the payment
    """

    payment_reference = serializers.CharField(max_length=64, required=False)
    note = serializers.CharField(max_length=500, required=False)


# =============================================================================
# Output Serializers
# =============================================================================


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for nested serialization."""
    
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name']
        read_only_fields = fields
    
    def get_display_name(self, obj):
        return obj.get_display_name()


class CoffeeBeanMinimalSerializer(serializers.ModelSerializer):
    """Minimal bean info for nested serialization."""
    
    class Meta:
        model = CoffeeBean
        fields = ['id', 'name', 'roastery_name']
        read_only_fields = fields


class PaymentShareSerializer(serializers.ModelSerializer):
    """Serializer for payment shares."""
    
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = PaymentShare
        fields = [
            'id',
            'purchase',
            'user',
            'amount_czk',
            'currency',
            'status',
            'payment_reference',
            'qr_url',
            'qr_image_path',
            'paid_at',
            'paid_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'payment_reference',
            'qr_url',
            'qr_image_path',
            'paid_at',
            'created_at',
            'updated_at',
        ]


class PurchaseRecordSerializer(serializers.ModelSerializer):
    """Main serializer for purchase records."""
    
    bought_by = UserMinimalSerializer(read_only=True)
    coffeebean = CoffeeBeanMinimalSerializer(read_only=True)
    payment_shares = PaymentShareSerializer(many=True, read_only=True)
    
    class Meta:
        model = PurchaseRecord
        fields = [
            'id',
            'group',
            'coffeebean',
            'variant',
            'bought_by',
            'total_price_czk',
            'currency',
            'package_weight_grams',
            'date',
            'purchase_location',
            'note',
            'total_collected_czk',
            'is_fully_paid',
            'payment_shares',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'bought_by',
            'total_collected_czk',
            'is_fully_paid',
            'created_at',
            'updated_at',
        ]


class PurchaseRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating purchase records."""
    
    split_members = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of user IDs to split payment among. If not provided, splits among all group members."
    )
    
    class Meta:
        model = PurchaseRecord
        fields = [
            'group',
            'coffeebean',
            'variant',
            'total_price_czk',
            'package_weight_grams',
            'date',
            'purchase_location',
            'note',
            'split_members',
        ]
    
    def validate(self, attrs):
        """Validate purchase data."""
        # If group purchase, group is required
        if attrs.get('group') is None:
            # Personal purchase - no split needed
            pass
        else:
            # Group purchase - validate membership
            request = self.context.get('request')
            if request and request.user:
                group = attrs.get('group')
                if not group.has_member(request.user):
                    raise serializers.ValidationError({
                        'group': 'You must be a member of this group'
                    })
        
        return attrs


class PurchaseRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    
    bought_by = UserMinimalSerializer(read_only=True)
    coffeebean_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseRecord
        fields = [
            'id',
            'group',
            'coffeebean_name',
            'bought_by',
            'total_price_czk',
            'date',
            'is_fully_paid',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_coffeebean_name(self, obj):
        if obj.coffeebean:
            return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
        return None


class PurchaseSummarySerializer(serializers.Serializer):
    """Serializer for purchase summary."""
    
    purchase = PurchaseRecordSerializer()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    collected_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    outstanding_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_fully_paid = serializers.BooleanField()
    total_shares = serializers.IntegerField()
    paid_count = serializers.IntegerField()
    unpaid_count = serializers.IntegerField()
    paid_shares = PaymentShareSerializer(many=True)
    unpaid_shares = PaymentShareSerializer(many=True)