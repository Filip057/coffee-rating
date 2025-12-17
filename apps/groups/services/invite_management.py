"""
Invite management service.

Handles group invite code operations with uniqueness guarantees.
"""

import secrets
from uuid import UUID

from django.db import transaction, IntegrityError

from apps.accounts.models import User
from apps.groups.models import Group

from .exceptions import (
    GroupNotFoundError,
    InsufficientPermissionsError,
)


@transaction.atomic
def regenerate_invite_code(
    *,
    group_id: UUID,
    user: User,
    max_retries: int = 5
) -> str:
    """
    Regenerate a group's invite code (admin only).

    Uses row-level locking and retry logic to ensure uniqueness.

    Args:
        group_id: UUID of the group
        user: User requesting regeneration (must be admin)
        max_retries: Maximum attempts to generate unique code

    Returns:
        New invite code

    Raises:
        GroupNotFoundError: If group doesn't exist
        InsufficientPermissionsError: If user is not admin
        RuntimeError: If cannot generate unique code after retries
    """
    # Lock the group
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
        raise InsufficientPermissionsError("Only group admins can regenerate invite codes")

    # Generate unique code with retry logic
    for attempt in range(max_retries):
        new_code = secrets.token_urlsafe(12)[:16]

        try:
            group.invite_code = new_code
            group.save(update_fields=['invite_code', 'updated_at'])
            return new_code
        except IntegrityError:
            # Collision detected, retry
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Failed to generate unique invite code after {max_retries} attempts"
                )
            continue

    # Should never reach here
    raise RuntimeError("Unexpected error in invite code generation")


def validate_invite_code(*, group_id: UUID, invite_code: str) -> bool:
    """
    Validate an invite code for a group.

    Args:
        group_id: UUID of the group
        invite_code: Code to validate

    Returns:
        True if valid, False otherwise

    Raises:
        GroupNotFoundError: If group doesn't exist
    """
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    return group.invite_code == invite_code
