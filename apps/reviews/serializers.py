from rest_framework import serializers
from .models import Review, Tag, UserLibraryEntry
from apps.beans.models import CoffeeBean
from apps.groups.models import Group
from apps.accounts.models import User


class TagSerializer(serializers.ModelSerializer):
    """Serializer for taste tags."""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'category']
        read_only_fields = ['id']


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
        fields = ['id', 'name', 'roastery_name', 'avg_rating', 'review_count']
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    """Main review serializer."""
    
    author = UserMinimalSerializer(read_only=True)
    coffeebean_detail = CoffeeBeanMinimalSerializer(source='coffeebean', read_only=True)
    taste_tags = TagSerializer(many=True, read_only=True)
    taste_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Review
        fields = [
            'id',
            'coffeebean',
            'coffeebean_detail',
            'author',
            'rating',
            'aroma_score',
            'flavor_score',
            'acidity_score',
            'body_score',
            'aftertaste_score',
            'notes',
            'brew_method',
            'taste_tags',
            'taste_tag_ids',
            'context',
            'group',
            'would_buy_again',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'coffeebean_detail', 'taste_tags']
    
    def validate(self, attrs):
        """Validate review data."""
        # Validate rating scores
        if attrs.get('rating') and (attrs['rating'] < 1 or attrs['rating'] > 5):
            raise serializers.ValidationError({'rating': 'Rating must be between 1 and 5'})
        
        # Validate group context
        if attrs.get('context') == 'group' and not attrs.get('group'):
            raise serializers.ValidationError({'group': 'Group is required for group context reviews'})
        
        # Check if user is member of group (if group context)
        if attrs.get('group'):
            request = self.context.get('request')
            if request and request.user:
                if not attrs['group'].has_member(request.user):
                    raise serializers.ValidationError({'group': 'You are not a member of this group'})
        
        return attrs
    
    def create(self, validated_data):
        """Create review with tag association."""
        taste_tag_ids = validated_data.pop('taste_tag_ids', [])
        
        review = Review.objects.create(**validated_data)
        
        # Associate tags
        if taste_tag_ids:
            tags = Tag.objects.filter(id__in=taste_tag_ids)
            review.taste_tags.set(tags)
        
        return review
    
    def update(self, instance, validated_data):
        """Update review with tag association."""
        taste_tag_ids = validated_data.pop('taste_tag_ids', None)
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if taste_tag_ids is not None:
            tags = Tag.objects.filter(id__in=taste_tag_ids)
            instance.taste_tags.set(tags)
        
        return instance


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for review creation."""
    
    taste_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Review
        fields = [
            'coffeebean',
            'rating',
            'aroma_score',
            'flavor_score',
            'acidity_score',
            'body_score',
            'aftertaste_score',
            'notes',
            'brew_method',
            'taste_tag_ids',
            'context',
            'group',
            'would_buy_again',
        ]
    
    def validate(self, attrs):
        """Validate review data."""
        # Rating validation
        if attrs.get('rating') and (attrs['rating'] < 1 or attrs['rating'] > 5):
            raise serializers.ValidationError({'rating': 'Rating must be between 1 and 5'})
        
        # Group context validation
        if attrs.get('context') == 'group' and not attrs.get('group'):
            raise serializers.ValidationError({'group': 'Group is required for group context'})
        
        # Check group membership
        if attrs.get('group'):
            request = self.context.get('request')
            if request and request.user:
                if not attrs['group'].has_member(request.user):
                    raise serializers.ValidationError({'group': 'You must be a member of this group'})
        
        # Check if user already reviewed this bean
        request = self.context.get('request')
        if request and request.user:
            existing = Review.objects.filter(
                author=request.user,
                coffeebean=attrs.get('coffeebean')
            ).exists()
            if existing:
                raise serializers.ValidationError({
                    'coffeebean': 'You have already reviewed this coffee bean'
                })
        
        return attrs


class UserLibraryEntrySerializer(serializers.ModelSerializer):
    """Serializer for user library entries."""
    
    coffeebean = CoffeeBeanMinimalSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = UserLibraryEntry
        fields = [
            'id',
            'user',
            'coffeebean',
            'added_by',
            'added_at',
            'own_price_czk',
            'is_archived',
        ]
        read_only_fields = ['id', 'user', 'coffeebean', 'added_by', 'added_at']


class ReviewStatisticsSerializer(serializers.Serializer):
    """Serializer for review statistics."""
    
    total_reviews = serializers.IntegerField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    rating_distribution = serializers.DictField()
    top_tags = serializers.ListField()
    reviews_by_month = serializers.DictField()


class BeanReviewSummarySerializer(serializers.Serializer):
    """Summary of reviews for a specific bean."""
    
    bean_id = serializers.UUIDField()
    bean_name = serializers.CharField()
    total_reviews = serializers.IntegerField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    rating_breakdown = serializers.DictField()
    common_tags = serializers.ListField()
    recent_reviews = ReviewSerializer(many=True)