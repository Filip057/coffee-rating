# ==========================================
# apps/coffeebeans/admin.py
# ==========================================

from django.contrib import admin
from apps.beans.models import CoffeeBean, CoffeeBeanVariant


class CoffeeBeanVariantInline(admin.TabularInline):
    """Inline admin for coffee bean variants."""
    model = CoffeeBeanVariant
    extra = 1
    fields = [
        'package_weight_grams',
        'price_czk',
        'price_per_gram',
        'purchase_url',
        'is_active'
    ]
    readonly_fields = ['price_per_gram']


@admin.register(CoffeeBean)
class CoffeeBeanAdmin(admin.ModelAdmin):
    """Admin interface for Coffee Beans."""
    
    list_display = [
        'name',
        'roastery_name',
        'origin_country',
        'roast_profile',
        'avg_rating',
        'review_count',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'roast_profile',
        'processing',
        'brew_method',
        'is_active',
        'origin_country',
        'created_at'
    ]
    search_fields = [
        'name',
        'roastery_name',
        'origin_country',
        'region',
        'description',
        'tasting_notes'
    ]
    readonly_fields = [
        'name_normalized',
        'roastery_normalized',
        'avg_rating',
        'review_count',
        'created_at',
        'updated_at'
    ]
    inlines = [CoffeeBeanVariantInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'roastery_name',
                'origin_country',
                'region',
                'created_by'
            )
        }),
        ('Processing & Roasting', {
            'fields': (
                'processing',
                'roast_profile',
                'roast_date',
                'brew_method'
            )
        }),
        ('Description', {
            'fields': ('description', 'tasting_notes')
        }),
        ('Statistics', {
            'fields': ('avg_rating', 'review_count'),
            'classes': ('collapse',)
        }),
        ('Normalized Fields (Auto-generated)', {
            'fields': ('name_normalized', 'roastery_normalized'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['merge_beans', 'deactivate_beans', 'activate_beans']
    
    def merge_beans(self, request, queryset):
        """Merge selected beans (requires admin confirmation)."""
        # This would redirect to a custom merge view
        self.message_user(request, "Bean merging requires manual confirmation")
    merge_beans.short_description = "Merge selected beans"
    
    def deactivate_beans(self, request, queryset):
        """Deactivate selected beans."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} beans")
    deactivate_beans.short_description = "Deactivate selected beans"
    
    def activate_beans(self, request, queryset):
        """Activate selected beans."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} beans")
    activate_beans.short_description = "Activate selected beans"


@admin.register(CoffeeBeanVariant)
class CoffeeBeanVariantAdmin(admin.ModelAdmin):
    """Admin interface for Coffee Bean Variants."""
    
    list_display = [
        'get_bean_name',
        'package_weight_grams',
        'price_czk',
        'price_per_gram',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = [
        'coffeebean__name',
        'coffeebean__roastery_name'
    ]
    readonly_fields = ['price_per_gram', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Coffee Bean', {
            'fields': ('coffeebean',)
        }),
        ('Package Details', {
            'fields': (
                'package_weight_grams',
                'price_czk',
                'price_per_gram',
                'purchase_url'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_bean_name(self, obj):
        """Display bean name."""
        return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
    get_bean_name.short_description = 'Coffee Bean'
    get_bean_name.admin_order_field = 'coffeebean__name'
    
    def get_queryset(self, request):
        """Optimize query."""
        qs = super().get_queryset(request)
        return qs.select_related('coffeebean')
