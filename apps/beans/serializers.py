from rest_framework import serializers
from .models import CoffeeBean, CoffeeBeanVariant


class CoffeeBeanVariantSerializer(serializers.ModelSerializer):
    """Serializer for coffee bean variants (package sizes/prices)."""
    
    class Meta:
        model = CoffeeBeanVariant
        fields = [
            'id',
            'coffeebean',
            'package_weight_grams',
            'price_czk',
            'price_per_gram',
            'purchase_url',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'price_per_gram', 'created_at', 'updated_at']


class CoffeeBeanSerializer(serializers.ModelSerializer):
    """Main serializer for coffee beans."""
    
    variants = CoffeeBeanVariantSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    
    class Meta:
        model = CoffeeBean
        fields = [
            'id',
            'name',
            'roastery_name',
            'origin_country',
            'region',
            'processing',
            'roast_profile',
            'roast_date',
            'brew_method',
            'description',
            'tasting_notes',
            'avg_rating',
            'review_count',
            'variants',
            'is_active',
            'created_by',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'name_normalized',
            'roastery_normalized',
            'avg_rating',
            'review_count',
            'created_at',
            'updated_at',
        ]


class CoffeeBeanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating coffee beans."""
    
    class Meta:
        model = CoffeeBean
        fields = [
            'name',
            'roastery_name',
            'origin_country',
            'region',
            'processing',
            'roast_profile',
            'roast_date',
            'brew_method',
            'description',
            'tasting_notes',
        ]


class CoffeeBeanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    
    class Meta:
        model = CoffeeBean
        fields = [
            'id',
            'name',
            'roastery_name',
            'origin_country',
            'roast_profile',
            'avg_rating',
            'review_count',
            'created_at',
        ]
        read_only_fields = fields