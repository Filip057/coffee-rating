"""
Tests for analytics permission classes.

This module tests the custom permission classes created in Phase 3
of the analytics app refactoring.
"""
import pytest
from unittest.mock import Mock
from apps.analytics.permissions import IsGroupMemberForAnalytics


@pytest.mark.django_db
class TestIsGroupMemberForAnalytics:
    """Test IsGroupMemberForAnalytics permission class."""

    def test_no_group_id_allows_access(self, analytics_user):
        """Test that requests without group_id are allowed."""
        permission = IsGroupMemberForAnalytics()

        # Mock request and view without group_id
        request = Mock()
        request.user = analytics_user
        request.query_params = {}

        view = Mock()
        view.kwargs = {}

        # Should allow access when no group_id specified
        assert permission.has_permission(request, view) is True

    def test_member_allowed_via_url_kwargs(self, analytics_user, analytics_group):
        """Test that group members are allowed access (group_id in URL)."""
        permission = IsGroupMemberForAnalytics()

        # Mock request and view with group_id in URL kwargs
        request = Mock()
        request.user = analytics_user
        request.query_params = {}

        view = Mock()
        view.kwargs = {'group_id': str(analytics_group.id)}

        # User is owner of group, should allow access
        assert permission.has_permission(request, view) is True

    def test_member_allowed_via_query_params(
        self, analytics_member1, analytics_group
    ):
        """Test that group members are allowed access (group_id in query params)."""
        permission = IsGroupMemberForAnalytics()

        # Mock request and view with group_id in query params
        request = Mock()
        request.user = analytics_member1
        request.query_params = {'group_id': str(analytics_group.id)}

        view = Mock()
        view.kwargs = {}

        # analytics_member1 is a member of analytics_group
        assert permission.has_permission(request, view) is True

    def test_non_member_denied(self, analytics_outsider, analytics_group):
        """Test that non-members are denied access."""
        permission = IsGroupMemberForAnalytics()

        # Mock request and view
        request = Mock()
        request.user = analytics_outsider
        request.query_params = {}

        view = Mock()
        view.kwargs = {'group_id': str(analytics_group.id)}

        # analytics_outsider is not a member of analytics_group
        assert permission.has_permission(request, view) is False

    def test_nonexistent_group_denied(self, analytics_user):
        """Test that requests for nonexistent groups are denied."""
        permission = IsGroupMemberForAnalytics()

        # Mock request and view with fake group_id
        request = Mock()
        request.user = analytics_user
        request.query_params = {}

        view = Mock()
        view.kwargs = {'group_id': '00000000-0000-0000-0000-000000000000'}

        # Group doesn't exist, should deny access
        assert permission.has_permission(request, view) is False

    def test_url_kwargs_take_precedence(
        self, analytics_user, analytics_group, analytics_outsider
    ):
        """Test that URL kwargs take precedence over query params."""
        permission = IsGroupMemberForAnalytics()

        # Mock request with different group_id in kwargs vs query params
        request = Mock()
        request.user = analytics_user
        request.query_params = {
            'group_id': '00000000-0000-0000-0000-000000000000'  # Fake ID
        }

        view = Mock()
        view.kwargs = {'group_id': str(analytics_group.id)}  # Real group

        # Should use kwargs (real group), not query params
        assert permission.has_permission(request, view) is True

    def test_multiple_members_allowed(
        self, analytics_user, analytics_member1, analytics_member2, analytics_group
    ):
        """Test that all group members can access."""
        permission = IsGroupMemberForAnalytics()

        # Test owner
        request1 = Mock()
        request1.user = analytics_user
        request1.query_params = {}
        view1 = Mock()
        view1.kwargs = {'group_id': str(analytics_group.id)}
        assert permission.has_permission(request1, view1) is True

        # Test member1
        request2 = Mock()
        request2.user = analytics_member1
        request2.query_params = {}
        view2 = Mock()
        view2.kwargs = {'group_id': str(analytics_group.id)}
        assert permission.has_permission(request2, view2) is True

        # Test member2
        request3 = Mock()
        request3.user = analytics_member2
        request3.query_params = {}
        view3 = Mock()
        view3.kwargs = {'group_id': str(analytics_group.id)}
        assert permission.has_permission(request3, view3) is True

    def test_permission_message(self):
        """Test that permission has appropriate error message."""
        permission = IsGroupMemberForAnalytics()

        expected_message = 'You must be a member of this group to view its analytics.'
        assert permission.message == expected_message

    def test_empty_string_group_id_allows_access(self, analytics_user):
        """Test that empty string group_id is treated as no group_id."""
        permission = IsGroupMemberForAnalytics()

        # Mock request with empty string group_id
        request = Mock()
        request.user = analytics_user
        request.query_params = {'group_id': ''}

        view = Mock()
        view.kwargs = {}

        # Empty string should be falsy and allow access
        assert permission.has_permission(request, view) is True
