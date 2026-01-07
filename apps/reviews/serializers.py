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
        """Validate review data - basic input validation only."""
        # Validate rating scores (basic range check)
        if attrs.get('rating') and (attrs['rating'] < 1 or attrs['rating'] > 5):
            raise serializers.ValidationError({'rating': 'Rating must be between 1 and 5'})

        # Validate group context requirement
        if attrs.get('context') == 'group' and not attrs.get('group'):
            raise serializers.ValidationError({'group': 'Group is required for group context reviews'})

        return attrs


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for review creation - validation only."""

    taste_tags = TagSerializer(many=True, read_only=True)
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
            'taste_tags',
            'taste_tag_ids',
            'context',
            'group',
            'would_buy_again',
        ]

    def validate(self, attrs):
        """Validate review input data - basic validation only.

        Business logic validations (duplicate checks, group membership, etc.)
        are handled in the service layer.
        """
        # Basic rating range validation
        if attrs.get('rating') and (attrs['rating'] < 1 or attrs['rating'] > 5):
            raise serializers.ValidationError({'rating': 'Rating must be between 1 and 5'})

        # Basic group context requirement
        if attrs.get('context') == 'group' and not attrs.get('group'):
            raise serializers.ValidationError({'group': 'Group is required for group context'})

        return attrs


class UserLibraryEntrySerializer(serializers.ModelSerializer):
    """Serializer for user library entries."""

    coffeebean = CoffeeBeanMinimalSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    user_rating = serializers.SerializerMethodField()

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
            'user_rating',
        ]
        read_only_fields = ['id', 'user', 'coffeebean', 'added_by', 'added_at', 'user_rating']

    def get_user_rating(self, obj):
        """Get user's rating for this bean (if they've reviewed it)."""
        from apps.reviews.models import Review

        user = self.context.get('request').user if self.context.get('request') else obj.user
        if not user or not user.is_authenticated:
            return None

        try:
            review = Review.objects.filter(
                author=user,
                coffeebean=obj.coffeebean
            ).values('rating').first()
            return review['rating'] if review else None
        except Exception:
            return None


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