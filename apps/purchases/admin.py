# ==========================================
# apps/purchases/admin.py
# ==========================================

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from decimal import Decimal
from .models import PurchaseRecord, PaymentShare, BankTransaction, PaymentStatus


class PaymentShareInline(admin.TabularInline):
    """Inline admin for payment shares within a purchase."""
    model = PaymentShare
    extra = 0
    fields = [
        'user',
        'amount_czk',
        'status_badge',
        'payment_reference',
        'paid_at',
    ]
    readonly_fields = ['payment_reference', 'paid_at', 'status_badge']

    def status_badge(self, obj):
        """Display payment status as colored badge."""
        colors = {
            PaymentStatus.UNPAID: ('#E5C49A', '#2C1810'),
            PaymentStatus.PAID: ('#6B8E5E', 'white'),
            PaymentStatus.FAILED: ('#B85C5C', 'white'),
            PaymentStatus.REFUNDED: ('#A47449', 'white'),
        }
        bg, fg = colors.get(obj.status, ('#ccc', '#666'))
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">{}</span>',
            bg, fg, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def has_add_permission(self, request, obj=None):
        """Disable adding shares manually - they're created by the service."""
        return False


@admin.register(PurchaseRecord)
class PurchaseRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for Purchase Records.

    Provides comprehensive purchase management including:
    - Purchase listing with payment status
    - Inline payment shares
    - Filtering by payment status, group, date
    - Actions for payment reconciliation
    """

    list_display = [
        'get_bean_name',
        'bought_by',
        'get_group_name',
        'total_price_czk',
        'get_collected_display',
        'payment_status_badge',
        'date',
        'created_at',
    ]

    list_filter = [
        'is_fully_paid',
        'group',
        'date',
        'created_at',
    ]

    search_fields = [
        'coffeebean__name',
        'coffeebean__roastery_name',
        'bought_by__email',
        'bought_by__display_name',
        'group__name',
        'note',
    ]

    readonly_fields = [
        'total_collected_czk',
        'is_fully_paid',
        'created_at',
        'updated_at',
    ]

    inlines = [PaymentShareInline]
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']

    fieldsets = (
        ('Purchase Information', {
            'fields': (
                'coffeebean',
                'variant',
                'bought_by',
                'group',
            )
        }),
        ('Financial Details', {
            'fields': (
                'total_price_czk',
                'currency',
                'total_collected_czk',
                'is_fully_paid',
            )
        }),
        ('Package & Location', {
            'fields': (
                'package_weight_grams',
                'date',
                'purchase_location',
            )
        }),
        ('Notes', {
            'fields': ('note',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_bean_name(self, obj):
        """Display bean name or placeholder."""
        if obj.coffeebean:
            return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
        return "— No bean —"
    get_bean_name.short_description = 'Coffee Bean'
    get_bean_name.admin_order_field = 'coffeebean__name'

    def get_group_name(self, obj):
        """Display group name or Personal badge."""
        if obj.group:
            return obj.group.name
        return format_html(
            '<span style="background: #E8DDD4; color: #2C1810; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">Personal</span>'
        )
    get_group_name.short_description = 'Group'
    get_group_name.admin_order_field = 'group__name'

    def get_collected_display(self, obj):
        """Display collected/total amounts."""
        return f"{obj.total_collected_czk} / {obj.total_price_czk} CZK"
    get_collected_display.short_description = 'Collected'

    def payment_status_badge(self, obj):
        """Display payment status as colored badge."""
        if obj.is_fully_paid:
            return format_html(
                '<span style="background: #6B8E5E; color: white; padding: 3px 8px; '
                'border-radius: 10px; font-size: 11px;">Paid</span>'
            )
        outstanding = obj.get_outstanding_balance()
        return format_html(
            '<span style="background: #E5C49A; color: #2C1810; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">-{} CZK</span>',
            outstanding
        )
    payment_status_badge.short_description = 'Status'
    payment_status_badge.admin_order_field = 'is_fully_paid'

    actions = [
        'mark_fully_paid',
        'recalculate_collection_status',
    ]

    @admin.action(description='Mark all shares as paid')
    def mark_fully_paid(self, request, queryset):
        """Mark all payment shares as paid for selected purchases."""
        count = 0
        for purchase in queryset:
            shares = purchase.payment_shares.filter(status=PaymentStatus.UNPAID)
            for share in shares:
                share.mark_paid(paid_by_user=request.user)
                count += 1
        self.message_user(request, f'Marked {count} share(s) as paid.')

    @admin.action(description='Recalculate collection status')
    def recalculate_collection_status(self, request, queryset):
        """Recalculate total_collected_czk and is_fully_paid for selected purchases."""
        for purchase in queryset:
            purchase.update_collection_status()
        self.message_user(request, f'Recalculated status for {queryset.count()} purchase(s).')

    def get_queryset(self, request):
        """Optimize query with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('bought_by', 'coffeebean', 'group', 'variant')


@admin.register(PaymentShare)
class PaymentShareAdmin(admin.ModelAdmin):
    """
    Admin interface for Payment Shares.

    Provides payment tracking including:
    - Payment status and amounts
    - QR code information
    - Bulk payment actions
    """

    list_display = [
        'user',
        'get_purchase_info',
        'amount_czk',
        'status_badge',
        'payment_reference',
        'paid_at',
        'created_at',
    ]

    list_filter = [
        'status',
        'created_at',
        'paid_at',
    ]

    search_fields = [
        'user__email',
        'user__display_name',
        'purchase__coffeebean__name',
        'purchase__coffeebean__roastery_name',
        'payment_reference',
    ]

    readonly_fields = [
        'payment_reference',
        'qr_url',
        'qr_image_path',
        'paid_at',
        'paid_by',
        'created_at',
        'updated_at',
    ]

    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'purchase',
                'user',
                'amount_czk',
                'currency',
            )
        }),
        ('Payment Status', {
            'fields': (
                'status',
                'paid_at',
                'paid_by',
            )
        }),
        ('Payment Reference & QR', {
            'fields': (
                'payment_reference',
                'qr_url',
                'qr_image_path',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_purchase_info(self, obj):
        """Display purchase info (bean name + group)."""
        bean = obj.purchase.coffeebean
        if bean:
            info = f"{bean.roastery_name} - {bean.name}"
        else:
            info = "Unknown"
        if obj.purchase.group:
            info += f" ({obj.purchase.group.name})"
        return info
    get_purchase_info.short_description = 'Purchase'

    def status_badge(self, obj):
        """Display payment status as colored badge."""
        colors = {
            PaymentStatus.UNPAID: ('#E5C49A', '#2C1810', 'Unpaid'),
            PaymentStatus.PAID: ('#6B8E5E', 'white', 'Paid'),
            PaymentStatus.FAILED: ('#B85C5C', 'white', 'Failed'),
            PaymentStatus.REFUNDED: ('#A47449', 'white', 'Refunded'),
        }
        bg, fg, label = colors.get(obj.status, ('#ccc', '#666', obj.status))
        return format_html(
            '<span style="background: {}; color: {}; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">{}</span>',
            bg, fg, label
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    actions = [
        'mark_as_paid',
        'mark_as_unpaid',
        'mark_as_failed',
    ]

    @admin.action(description='Mark selected as PAID')
    def mark_as_paid(self, request, queryset):
        """Mark selected shares as paid."""
        count = 0
        for share in queryset.filter(status__in=[PaymentStatus.UNPAID, PaymentStatus.FAILED]):
            share.mark_paid(paid_by_user=request.user)
            count += 1
        self.message_user(request, f'Marked {count} share(s) as paid.')

    @admin.action(description='Mark selected as UNPAID')
    def mark_as_unpaid(self, request, queryset):
        """Mark selected shares as unpaid (reverses payment)."""
        count = queryset.update(
            status=PaymentStatus.UNPAID,
            paid_at=None,
            paid_by=None
        )
        # Update parent purchases
        for share in queryset:
            share.purchase.update_collection_status()
        self.message_user(request, f'Marked {count} share(s) as unpaid.')

    @admin.action(description='Mark selected as FAILED')
    def mark_as_failed(self, request, queryset):
        """Mark selected shares as failed."""
        count = queryset.filter(status=PaymentStatus.UNPAID).update(status=PaymentStatus.FAILED)
        self.message_user(request, f'Marked {count} share(s) as failed.')

    def get_queryset(self, request):
        """Optimize query with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'purchase', 'purchase__coffeebean', 'purchase__group', 'paid_by')


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for Bank Transactions.

    Provides transaction matching including:
    - Imported transaction listing
    - Matching status
    - Auto-match functionality
    """

    list_display = [
        'transaction_id',
        'date',
        'amount_czk',
        'variable_symbol',
        'match_status_badge',
        'get_matched_share_info',
        'imported_at',
    ]

    list_filter = [
        'is_matched',
        'date',
        'imported_at',
    ]

    search_fields = [
        'transaction_id',
        'variable_symbol',
        'message',
    ]

    readonly_fields = [
        'transaction_id',
        'date',
        'amount_czk',
        'variable_symbol',
        'message',
        'matched_share',
        'is_matched',
        'imported_at',
        'raw_data',
    ]

    date_hierarchy = 'date'
    ordering = ['-date', '-imported_at']

    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'transaction_id',
                'date',
                'amount_czk',
            )
        }),
        ('Matching Information', {
            'fields': (
                'variable_symbol',
                'message',
                'is_matched',
                'matched_share',
            )
        }),
        ('Import Metadata', {
            'fields': ('imported_at', 'raw_data'),
            'classes': ('collapse',),
        }),
    )

    def match_status_badge(self, obj):
        """Display matching status as colored badge."""
        if obj.is_matched:
            return format_html(
                '<span style="background: #6B8E5E; color: white; padding: 3px 8px; '
                'border-radius: 10px; font-size: 11px;">Matched</span>'
            )
        return format_html(
            '<span style="background: #E5C49A; color: #2C1810; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">Unmatched</span>'
        )
    match_status_badge.short_description = 'Status'
    match_status_badge.admin_order_field = 'is_matched'

    def get_matched_share_info(self, obj):
        """Display matched share info if available."""
        if obj.matched_share:
            share = obj.matched_share
            return f"{share.user.email} - {share.amount_czk} CZK"
        return "—"
    get_matched_share_info.short_description = 'Matched To'

    actions = [
        'auto_match_transactions',
        'clear_matches',
    ]

    @admin.action(description='Auto-match transactions by variable symbol')
    def auto_match_transactions(self, request, queryset):
        """
        Attempt to auto-match unmatched transactions to payment shares
        based on variable symbol / payment reference.
        """
        matched = 0
        for transaction in queryset.filter(is_matched=False):
            if not transaction.variable_symbol:
                continue

            # Try to find matching payment share
            try:
                share = PaymentShare.objects.get(
                    payment_reference=transaction.variable_symbol,
                    status=PaymentStatus.UNPAID
                )
                # Verify amount matches
                if share.amount_czk == transaction.amount_czk:
                    share.mark_paid(paid_by_user=request.user)
                    transaction.matched_share = share
                    transaction.is_matched = True
                    transaction.save()
                    matched += 1
            except PaymentShare.DoesNotExist:
                pass

        self.message_user(request, f'Auto-matched {matched} transaction(s).')

    @admin.action(description='Clear matches (for re-matching)')
    def clear_matches(self, request, queryset):
        """Clear matching information from selected transactions."""
        count = queryset.update(matched_share=None, is_matched=False)
        self.message_user(request, f'Cleared matches for {count} transaction(s).')

    def has_add_permission(self, request):
        """Disable manual creation - transactions are imported."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing - transactions are read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return True

    def get_queryset(self, request):
        """Optimize query with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('matched_share', 'matched_share__user')
