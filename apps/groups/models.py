# ==========================================
# apps/groups/models.py
# ==========================================

from django.db import models
import uuid
import secrets
from apps.beans.models import CoffeeBean

class GroupRole(models.TextChoices):
    OWNER = 'owner', 'Owner'
    ADMIN = 'admin', 'Admin'
    MEMBER = 'member', 'Member'


class Group(models.Model):
    """Team/group for shared coffee tracking."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_private = models.BooleanField(default=True)
    invite_code = models.CharField(max_length=16, unique=True, db_index=True, editable=False)
    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='owned_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'groups'
        indexes = [
            models.Index(fields=['owner', 'created_at']),
            models.Index(fields=['invite_code']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = secrets.token_urlsafe(12)[:16]
        super().save(*args, **kwargs)
    
    def regenerate_invite_code(self):
        self.invite_code = secrets.token_urlsafe(12)[:16]
        self.save(update_fields=['invite_code', 'updated_at'])
        return self.invite_code
    
    def has_member(self, user):
        return self.memberships.filter(user=user).exists()
    
    def get_user_role(self, user):
        try:
            return self.memberships.get(user=user).role
        except GroupMembership.DoesNotExist:
            return None
    
    def is_admin(self, user):
        role = self.get_user_role(user)
        return role in [GroupRole.OWNER, GroupRole.ADMIN]


class GroupMembership(models.Model):
    """User membership in a group with role."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=GroupRole.choices, default=GroupRole.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_memberships'
        unique_together = [['user', 'group']]
        indexes = [
            models.Index(fields=['group', 'role']),
            models.Index(fields=['user', 'joined_at']),
        ]
        ordering = ['joined_at']
    
    def __str__(self):
        return f"{self.user.get_display_name()} in {self.group.name} ({self.role})"
    
    def save(self, *args, **kwargs):
        if self.group.owner_id == self.user_id:
            self.role = GroupRole.OWNER
        super().save(*args, **kwargs)


class GroupLibraryEntry(models.Model):
    """Group's shared coffee library."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='library_entries')
    coffeebean = models.ForeignKey('beans.CoffeeBean', on_delete=models.CASCADE, related_name='group_libraries')
    added_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='added_group_beans')
    added_at = models.DateTimeField(auto_now_add=True)
    pinned = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'group_library_entries'
        unique_together = [['group', 'coffeebean']]
        indexes = [
            models.Index(fields=['group', 'pinned', 'added_at']),
            models.Index(fields=['group', 'added_at']),
        ]
        ordering = ['-pinned', '-added_at']
    
    def __str__(self):
        return f"{self.group.name} - {self.coffeebean.name}"





