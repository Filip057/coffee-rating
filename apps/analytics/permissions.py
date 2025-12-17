"""
Custom permission classes for analytics app.

This module contains DRF permission classes that control access to
analytics endpoints. These replace inline permission checks in views.

Permission Classes:
    IsGroupMemberForAnalytics - Requires group membership for group analytics

Usage:
    from apps.analytics.permissions import IsGroupMemberForAnalytics

    @api_view(['GET'])
    @permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
    def group_consumption(request, group_id):
        # Permission already verified by IsGroupMemberForAnalytics
        ...
"""

from rest_framework.permissions import BasePermission
from apps.groups.models import Group


class IsGroupMemberForAnalytics(BasePermission):
    """
    Permission check for group analytics access.

    This permission class checks if the requesting user is a member of
    the group specified in the request. It handles both URL kwargs
    (for endpoints like /group/{id}/consumption/) and query parameters
    (for endpoints like /timeseries/?group_id={id}).

    Access is allowed if:
    - No group_id is specified (user-level analytics)
    - User is a member of the specified group

    Access is denied if:
    - Group doesn't exist (returns False, results in 403)
    - User is not a member of the group

    Used by:
        - group_consumption (group_id in URL)
        - consumption_timeseries (group_id in query params)

    Example:
        @permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
        def group_consumption(request, group_id):
            # If we reach here, user is authenticated AND is group member
            ...
    """

    message = 'You must be a member of this group to view its analytics.'

    def has_permission(self, request, view):
        """
        Check if user has permission to access group analytics.

        Args:
            request: The HTTP request
            view: The view being accessed

        Returns:
            bool: True if access allowed, False otherwise
        """
        # Check URL kwargs first (for group_consumption endpoint)
        group_id = view.kwargs.get('group_id')

        # Check query params if not in URL (for consumption_timeseries)
        if not group_id:
            group_id = request.query_params.get('group_id')

        # No group specified - allow access (this is a user-level request)
        if not group_id:
            return True

        # Verify group exists and user is a member
        try:
            group = Group.objects.get(id=group_id)
            return group.has_member(request.user)
        except Group.DoesNotExist:
            # Group doesn't exist - deny access
            # Note: Could also raise NotFound here, but 403 is acceptable
            return False
