from django.contrib import admin
from django.db.models import Count
from .models import Review, Tag, UserLibraryEntry


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin interface for Tags."""
    
    list_display = ['name', 'category', 'usage_count', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'category']
    ordering = ['name']
    
    def usage_count(self, obj):
        """Show how many times tag is used."""
        return obj.reviews.count()
    usage_count.short_description = 'Times Used'
    
    def get_queryset(self, request):
        """Optimize query with annotation."""
        qs = super().get_queryset(request)
        return qs.annotate(review_count=Count('reviews'))


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin interface for Reviews."""
    
    list_display = [
        'get_bean_name',
        'author',
        'rating',
        'context',
        'group',
        'created_at'
    ]
    list_filter = [
        'rating',
        'context',
        'created_at',
        'would_buy_again'
    ]
    search_fields = [
        'coffeebean__name',
        'coffeebean__roastery_name',
        'author__email',
        'notes'
    ]
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['taste_tags']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('coffeebean', 'author', 'rating', 'context', 'group')
        }),
        ('Detailed Scores', {
            'fields': (
                'aroma_score',
                'flavor_score',
                'acidity_score',
                'body_score',
                'aftertaste_score'
            ),
            'classes': ('collapse',)
        }),
        ('Review Content', {
            'fields': ('notes', 'brew_method', 'taste_tags', 'would_buy_again')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_bean_name(self, obj):
        """Display bean name in list."""
        return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
    get_bean_name.short_description = 'Coffee Bean'
    get_bean_name.admin_order_field = 'coffeebean__name'
    
    def get_queryset(self, request):
        """Optimize query with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('author', 'coffeebean', 'group')
    
    actions = ['recalculate_bean_ratings']
    
    def recalculate_bean_ratings(self, request, queryset):
        """Recalculate aggregate ratings for beans."""
        beans = set(review.coffeebean for review in queryset)
        for bean in beans:
            bean.update_aggregate_rating()
        self.message_user(request, f"Recalculated ratings for {len(beans)} beans")
    recalculate_bean_ratings.short_description = "Recalculate bean ratings"


@admin.register(UserLibraryEntry)
class UserLibraryEntryAdmin(admin.ModelAdmin):
    """Admin interface for User Library Entries."""
    
    list_display = [
        'user',
        'get_bean_name',
        'added_by',
        'added_at',
        'is_archived',
        'own_price_czk'
    ]
    list_filter = [
        'added_by',
        'is_archived',
        'added_at'
    ]
    search_fields = [
        'user__email',
        'coffeebean__name',
        'coffeebean__roastery_name'
    ]
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'
    ordering = ['-added_at']
    
    def get_bean_name(self, obj):
        """Display bean name in list."""
        return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
    get_bean_name.short_description = 'Coffee Bean'
    get_bean_name.admin_order_field = 'coffeebean__name'
    
    def get_queryset(self, request):
        """Optimize query with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'coffeebean')




