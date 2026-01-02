# ==========================================
# apps/accounts/admin.py
# ==========================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.

    Provides comprehensive user management including:
    - User listing with key fields
    - Filtering by status and verification
    - Search by email and display name
    - Bulk actions for user management
    - GDPR-compliant anonymization
    """

    # List display configuration
    list_display = [
        'email',
        'display_name',
        'is_active_badge',
        'is_staff_badge',
        'email_verified_badge',
        'created_at',
        'last_login',
    ]

    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'email_verified',
        'created_at',
        'last_login',
    ]

    search_fields = [
        'email',
        'display_name',
    ]

    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    # Remove username field references from BaseUserAdmin
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'display_name', 'password')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Verification', {
            'fields': ('email_verified', 'verification_token'),
            'classes': ('collapse',),
        }),
        ('Preferences', {
            'fields': ('preferences',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_login'),
            'classes': ('collapse',),
        }),
        ('GDPR', {
            'fields': ('gdpr_deleted_at',),
            'classes': ('collapse',),
            'description': 'GDPR compliance fields. Use anonymize action for data deletion requests.',
        }),
    )

    add_fieldsets = (
        ('Create User', {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'password1', 'password2'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )

    readonly_fields = [
        'created_at',
        'last_login',
        'gdpr_deleted_at',
    ]

    filter_horizontal = ['groups', 'user_permissions']

    # Custom display methods with badges
    def is_active_badge(self, obj):
        """Display active status as colored badge."""
        if obj.is_active:
            return format_html(
                '<span style="background: #6B8E5E; color: white; padding: 3px 8px; '
                'border-radius: 10px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background: #B85C5C; color: white; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'

    def is_staff_badge(self, obj):
        """Display staff status as colored badge."""
        if obj.is_staff:
            return format_html(
                '<span style="background: #A47449; color: white; padding: 3px 8px; '
                'border-radius: 10px; font-size: 11px;">Staff</span>'
            )
        return format_html(
            '<span style="background: #ccc; color: #666; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">User</span>'
        )
    is_staff_badge.short_description = 'Role'
    is_staff_badge.admin_order_field = 'is_staff'

    def email_verified_badge(self, obj):
        """Display email verification status as colored badge."""
        if obj.email_verified:
            return format_html(
                '<span style="background: #6B8E5E; color: white; padding: 3px 8px; '
                'border-radius: 10px; font-size: 11px;">Verified</span>'
            )
        return format_html(
            '<span style="background: #E5C49A; color: #2C1810; padding: 3px 8px; '
            'border-radius: 10px; font-size: 11px;">Pending</span>'
        )
    email_verified_badge.short_description = 'Email'
    email_verified_badge.admin_order_field = 'email_verified'

    # Actions
    actions = [
        'activate_users',
        'deactivate_users',
        'verify_emails',
        'unverify_emails',
        'anonymize_users',
    ]

    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        """Activate selected users."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'Activated {count} user(s).')

    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        """Deactivate selected users (excludes superusers for safety)."""
        # Don't deactivate superusers
        safe_queryset = queryset.filter(is_superuser=False)
        count = safe_queryset.update(is_active=False)
        skipped = queryset.count() - count
        msg = f'Deactivated {count} user(s).'
        if skipped:
            msg += f' Skipped {skipped} superuser(s) for safety.'
        self.message_user(request, msg)

    @admin.action(description='Mark emails as verified')
    def verify_emails(self, request, queryset):
        """Mark selected users' emails as verified."""
        count = queryset.update(email_verified=True, verification_token=None)
        self.message_user(request, f'Verified {count} email(s).')

    @admin.action(description='Mark emails as unverified')
    def unverify_emails(self, request, queryset):
        """Mark selected users' emails as unverified."""
        count = queryset.update(email_verified=False)
        self.message_user(request, f'Unverified {count} email(s).')

    @admin.action(description='GDPR: Anonymize selected users (IRREVERSIBLE)')
    def anonymize_users(self, request, queryset):
        """
        GDPR-compliant anonymization of selected users.

        WARNING: This action is IRREVERSIBLE and will:
        - Replace email with anonymized placeholder
        - Clear display name
        - Deactivate account
        - Set unusable password
        - Clear preferences
        """
        # Don't anonymize superusers or staff
        safe_queryset = queryset.filter(is_superuser=False, is_staff=False)
        count = 0
        for user in safe_queryset:
            user.anonymize()
            count += 1

        skipped = queryset.count() - count
        msg = f'Anonymized {count} user(s).'
        if skipped:
            msg += f' Skipped {skipped} staff/superuser(s) for safety.'
        self.message_user(request, msg)

    def get_queryset(self, request):
        """Optimize query."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('groups')
