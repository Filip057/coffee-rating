from rest_framework import permissions


class IsGroupAdmin(permissions.BasePermission):
    """
    Permission: User must be group admin or owner.
    """
    
    def has_object_permission(self, request, view, obj):
        # obj is a Group instance
        return obj.is_admin(request.user)


class IsGroupMember(permissions.BasePermission):
    """
    Permission: User must be a member of the group.
    """
    
    def has_object_permission(self, request, view, obj):
        # obj is a Group instance
        return obj.has_member(request.user)


class IsGroupOwner(permissions.BasePermission):
    """
    Permission: User must be the group owner.
    """
    
    def has_object_permission(self, request, view, obj):
        # obj is a Group instance
        return obj.owner == request.user