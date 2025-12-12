from rest_framework import permissions


class IsReviewAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission: Only review author can edit/delete their review.
    Anyone can read reviews.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for review author
        return obj.author == request.user


class IsLibraryOwner(permissions.BasePermission):
    """
    Permission: Only library entry owner can modify it.
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user