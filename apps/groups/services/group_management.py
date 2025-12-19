"""
Group management service.

Handles group CRUD operations with proper transaction safety.
"""

import secrets
from typing import Optional
from uuid import UUID

from django.db import transaction, IntegrityError
from django.db.models import Prefetch

from apps.accounts.models import User
from apps.groups.models import Group, GroupMembership, GroupRole

from .exceptions import (
    GroupNotFoundError,
    InsufficientPermissionsError,
)


def create_group(
    *,
    name: str,
    owner: User,
    description: str = '',
    is_private: bool = True,
    max_retries: int = 5
) -> Group:
    """
    Create a new group and add the creator as owner.

    This is a multi-step operation wrapped in a transaction:
    1. Generate unique invite code
    2. Create the group
    3. Create owner membership

    Args:
        name: Group name
        owner: User who will own the group
        description: Optional group description
        is_private: Whether group is private (default True)
        max_retries: Maximum attempts to generate unique invite code

    Returns:
        Created Group instance

    Raises:
        RuntimeError: If cannot generate unique invite code after retries
    """
    # Retry logic outside transaction to handle invite code collisions
    for attempt in range(max_retries):
        invite_code = secrets.token_urlsafe(12)[:16]

        try:
            # Each attempt is a separate transaction
            with transaction.atomic():
                # Create group with generated code
                group = Group.objects.create(
                    name=name,
                    owner=owner,
                    description=description,
                    is_private=is_private,
                    invite_code=invite_code
                )

                # Create owner membership
                GroupMembership.objects.create(
                    user=owner,
                    group=group,
                    role=GroupRole.OWNER
                )

                return group

        except IntegrityError:
            # Invite code collision (very rare)
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to generate unique invite code after {max_retries} attempts"
                )
            continue

    # Should never reach here
    raise RuntimeError("Unexpected error in group creation")


def get_group_by_id(*, group_id: UUID) -> Group:
    """
    Get a group by ID with optimized queries.

    Uses select_related and prefetch_related to minimize database queries.

    Args:
        group_id: UUID of the group

    Returns:
        Group instance

    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    try:
        return (
            Group.objects
            .select_related('owner')
            .prefetch_related(
                Prefetch(
                    'memberships',
                    queryset=GroupMembership.objects.select_related('user')
                )
            )
            .get(id=group_id)
        )
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")


@transaction.atomic
def update_group(
    *,
    group_id: UUID,
    user: User,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_private: Optional[bool] = None
) -> Group:
    """
    Update group details (admin only).

    Uses select_for_update to prevent concurrent modifications.

    Args:
        group_id: UUID of the group
        user: User performing the update (must be admin)
        name: New name (optional)
        description: New description (optional)
        is_private: New privacy setting (optional)

    Returns:
        Updated Group instance

    Raises:
        GroupNotFoundError: If group doesn't exist
        InsufficientPermissionsError: If user is not admin
    """
    try:
        group = (
            Group.objects
            .select_for_update()
            .get(id=group_id)
        )
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Check if user is admin
    if not group.is_admin(user):
        raise InsufficientPermissionsError("Only group admins can update the group")

    # Update fields if provided
    update_fields = ['updated_at']

    if name is not None:
        group.name = name
        update_fields.append('name')

    if description is not None:
        group.description = description
        update_fields.append('description')

    if is_private is not None:
        group.is_private = is_private
        update_fields.append('is_private')

    group.save(update_fields=update_fields)

    return group


@transaction.atomic
def delete_group(*, group_id: UUID, user: User) -> None:
    """
    Delete a group (owner only).

    Cascading deletes will automatically remove:
    - All memberships
    - All library entries

    Args:
        group_id: UUID of the group
        user: User requesting deletion (must be owner)

    Raises:
        GroupNotFoundError: If group doesn't exist
        InsufficientPermissionsError: If user is not the owner
    """
    try:
        group = (
            Group.objects
            .select_for_update()
            .get(id=group_id)
        )
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Only owner can delete
    if group.owner != user:
        raise InsufficientPermissionsError("Only the group owner can delete the group")

    group.delete()
