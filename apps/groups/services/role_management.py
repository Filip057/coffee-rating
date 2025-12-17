"""
Role management service.

Handles member role updates with concurrency protection.
"""

from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership, GroupRole

from .exceptions import (
    GroupNotFoundError,
    NotMemberError,
    CannotChangeOwnerRoleError,
    InsufficientPermissionsError,
)


@transaction.atomic
def update_member_role(
    *,
    group_id: UUID,
    user_id: UUID,
    new_role: str,
    updated_by: User
) -> GroupMembership:
    """
    Update a member's role (admin only).

    Uses select_for_update to prevent concurrent role changes.
    Cannot change the owner's role.

    Args:
        group_id: UUID of the group
        user_id: UUID of the user whose role to update
        new_role: New role ('admin' or 'member')
        updated_by: User performing the update (must be admin)

    Returns:
        Updated GroupMembership instance

    Raises:
        GroupNotFoundError: If group doesn't exist
        NotMemberError: If target user is not a member
        CannotChangeOwnerRoleError: If trying to change owner's role
        InsufficientPermissionsError: If updated_by is not admin
        ValueError: If new_role is invalid
    """
    # Validate role
    valid_roles = [GroupRole.ADMIN, GroupRole.MEMBER]
    if new_role not in valid_roles:
        raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

    # Get group
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Check if updater is admin
    if not group.is_admin(updated_by):
        raise InsufficientPermissionsError("Only group admins can update member roles")

    # Get membership with row lock to prevent concurrent updates
    try:
        membership = (
            GroupMembership.objects
            .select_for_update()
            .get(group=group, user_id=user_id)
        )
    except GroupMembership.DoesNotExist:
        raise NotMemberError("User is not a member of this group")

    # Cannot change owner's role
    if membership.role == GroupRole.OWNER:
        raise CannotChangeOwnerRoleError("Cannot change the owner's role")

    # Update role
    membership.role = new_role
    membership.save(update_fields=['role'])

    return membership
