# ==========================================
# apps/groups/admin.py
# ==========================================

from django.contrib import admin
from apps.groups.models import Group, GroupMembership, GroupLibraryEntry


class GroupMembershipInline(admin.TabularInline):
    """Inline admin for group memberships."""
    model = GroupMembership
    extra = 0
    fields = ['user', 'role', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin interface for Groups."""
    
    list_display = [
        'name',
        'owner',
        'member_count',
        'is_private',
        'invite_code',
        'created_at'
    ]
    list_filter = ['is_private', 'created_at']
    search_fields = ['name', 'description', 'owner__email', 'invite_code']
    readonly_fields = ['invite_code', 'created_at', 'updated_at']
    inlines = [GroupMembershipInline]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'owner', 'is_private')
        }),
        ('Invitation', {
            'fields': ('invite_code',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def member_count(self, obj):
        """Show number of members."""
        return obj.memberships.count()
    member_count.short_description = 'Members'
    
    actions = ['regenerate_invite_codes']
    
    def regenerate_invite_codes(self, request, queryset):
        """Regenerate invite codes for selected groups."""
        for group in queryset:
            group.regenerate_invite_code()
        self.message_user(request, f"Regenerated invite codes for {queryset.count()} groups")
    regenerate_invite_codes.short_description = "Regenerate invite codes"


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    """Admin interface for Group Memberships."""
    
    list_display = ['user', 'group', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__email', 'group__name']
    readonly_fields = ['joined_at']
    date_hierarchy = 'joined_at'
    ordering = ['-joined_at']
    
    def get_queryset(self, request):
        """Optimize query."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'group')


@admin.register(GroupLibraryEntry)
class GroupLibraryEntryAdmin(admin.ModelAdmin):
    """Admin interface for Group Library Entries."""
    
    list_display = [
        'group',
        'get_bean_name',
        'added_by',
        'pinned',
        'added_at'
    ]
    list_filter = ['pinned', 'added_at']
    search_fields = [
        'group__name',
        'coffeebean__name',
        'coffeebean__roastery_name'
    ]
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'
    ordering = ['-pinned', '-added_at']
    
    def get_bean_name(self, obj):
        """Display bean name."""
        return f"{obj.coffeebean.roastery_name} - {obj.coffeebean.name}"
    get_bean_name.short_description = 'Coffee Bean'
    
    def get_queryset(self, request):
        """Optimize query."""
        qs = super().get_queryset(request)
        return qs.select_related('group', 'coffeebean', 'added_by')