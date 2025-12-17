"""
Membership management service.

Handles group membership operations with concurrency protection.
"""

from typing import List
from uuid import UUID

from django.db import transaction, IntegrityError
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership, GroupRole

from .exceptions import (
    GroupNotFoundError,
    InvalidInviteCodeError,
    AlreadyMemberError,
    NotMemberError,
    OwnerCannotLeaveError,
    CannotRemoveOwnerError,
    InsufficientPermissionsError,
)


@transaction.atomic
def join_group(
    *,
    group_id: UUID,
    user: User,
    invite_code: str
) -> GroupMembership:
    """
    Join a group using an invite code.

    Uses row-level locking to prevent race conditions when checking
    and creating memberships.

    Args:
        group_id: UUID of the group
        user: User joining the group
        invite_code: Invite code for verification

    Returns:
        Created GroupMembership instance

    Raises:
        GroupNotFoundError: If group doesn't exist
        InvalidInviteCodeError: If invite code is incorrect
        AlreadyMemberError: If user is already a member (caught from IntegrityError)
    """
    # Lock the group to prevent concurrent joins
    try:
        group = (
            Group.objects
            .select_for_update()
            .get(id=group_id)
        )
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Verify invite code
    if group.invite_code != invite_code:
        raise InvalidInviteCodeError("Invalid invite code")

    # Check if already a member (defensive check)
    if group.has_member(user):
        raise AlreadyMemberError(f"User is already a member of {group.name}")

    # Create membership
    try:
        membership = GroupMembership.objects.create(
            user=user,
            group=group,
            role=GroupRole.MEMBER
        )
    except IntegrityError:
        # Database constraint caught duplicate membership
        raise AlreadyMemberError(f"User is already a member of {group.name}")

    return membership


@transaction.atomic
def leave_group(*, group_id: UUID, user: User) -> None:
    """
    Leave a group.

    Owner cannot leave their own group - they must transfer ownership or delete.

    Args:
        group_id: UUID of the group
        user: User leaving the group

    Raises:
        GroupNotFoundError: If group doesn't exist
        NotMemberError: If user is not a member
        OwnerCannotLeaveError: If user is the owner
    """
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Owner cannot leave
    if group.owner == user:
        raise OwnerCannotLeaveError(
            "Group owner cannot leave. Transfer ownership or delete the group."
        )

    # Get and delete membership
    try:
        membership = (
            GroupMembership.objects
            .select_for_update()
            .get(user=user, group=group)
        )
        membership.delete()
    except GroupMembership.DoesNotExist:
        raise NotMemberError(f"User is not a member of {group.name}")


@transaction.atomic
def remove_member(
    *,
    group_id: UUID,
    user_id: UUID,
    removed_by: User
) -> None:
    """
    Remove a member from a group (admin only).

    Cannot remove the group owner.

    Args:
        group_id: UUID of the group
        user_id: UUID of the user to remove
        removed_by: User performing the removal (must be admin)

    Raises:
        GroupNotFoundError: If group doesn't exist
        NotMemberError: If target user is not a member
        CannotRemoveOwnerError: If trying to remove the owner
        InsufficientPermissionsError: If removed_by is not admin
    """
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Check if remover is admin
    if not group.is_admin(removed_by):
        raise InsufficientPermissionsError("Only group admins can remove members")

    # Cannot remove owner
    if str(group.owner.id) == str(user_id):
        raise CannotRemoveOwnerError("Cannot remove the group owner")

    # Get and delete membership
    try:
        membership = (
            GroupMembership.objects
            .select_for_update()
            .get(group=group, user_id=user_id)
        )
        membership.delete()
    except GroupMembership.DoesNotExist:
        raise NotMemberError("User is not a member of this group")


def get_group_members(*, group_id: UUID) -> QuerySet[GroupMembership]:
    """
    Get all members of a group with optimized queries.

    Args:
        group_id: UUID of the group

    Returns:
        QuerySet of GroupMembership instances

    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    # Verify group exists
    if not Group.objects.filter(id=group_id).exists():
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    return (
        GroupMembership.objects
        .filter(group_id=group_id)
        .select_related('user')
        .order_by('-role', 'joined_at')
    )
