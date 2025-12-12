from rest_framework import serializers
from .models import PurchaseRecord, PaymentShare, PaymentStatus
from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant
from apps.groups.models import Group


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


class MarkPaidSerializer(serializers.Serializer):
    """Serializer for marking payment share as paid."""
    
    payment_reference = serializers.CharField(max_length=64, required=False)
    note = serializers.CharField(max_length=500, required=False)


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