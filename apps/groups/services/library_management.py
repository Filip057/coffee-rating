"""
Library management service.

Handles group coffee library operations.
"""

from uuid import UUID

from django.db import transaction, IntegrityError
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group, GroupLibraryEntry

from .exceptions import (
    GroupNotFoundError,
    BeanNotFoundError,
    NotMemberError,
    DuplicateLibraryEntryError,
)


@transaction.atomic
def add_to_library(
    *,
    group_id: UUID,
    coffeebean_id: UUID,
    user: User,
    notes: str = '',
    pinned: bool = False
) -> GroupLibraryEntry:
    """
    Add a coffee bean to the group library.

    Args:
        group_id: UUID of the group
        coffeebean_id: UUID of the coffee bean
        user: User adding the bean (must be a member)
        notes: Optional notes about the bean
        pinned: Whether to pin the entry

    Returns:
        Created GroupLibraryEntry

    Raises:
        GroupNotFoundError: If group doesn't exist
        BeanNotFoundError: If coffee bean doesn't exist
        NotMemberError: If user is not a member
        DuplicateLibraryEntryError: If bean already in library
    """
    # Verify group exists
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Check if user is member
    if not group.has_member(user):
        raise NotMemberError("You must be a member to add to the library")

    # Verify bean exists
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Coffee bean with ID {coffeebean_id} not found")

    # Create library entry
    try:
        entry = GroupLibraryEntry.objects.create(
            group=group,
            coffeebean=coffeebean,
            added_by=user,
            notes=notes,
            pinned=pinned
        )
    except IntegrityError:
        # unique_together constraint caught duplicate
        raise DuplicateLibraryEntryError(
            f"{coffeebean.name} is already in the group library"
        )

    return entry


@transaction.atomic
def remove_from_library(
    *,
    entry_id: UUID,
    user: User
) -> None:
    """
    Remove a bean from the group library.

    Args:
        entry_id: UUID of the library entry
        user: User removing the entry (must be a member)

    Raises:
        GroupLibraryEntry.DoesNotExist: If entry doesn't exist
        NotMemberError: If user is not a member
    """
    entry = (
        GroupLibraryEntry.objects
        .select_related('group')
        .get(id=entry_id)
    )

    # Check if user is member
    if not entry.group.has_member(user):
        raise NotMemberError("You must be a member to modify the library")

    entry.delete()


@transaction.atomic
def pin_library_entry(*, entry_id: UUID, user: User) -> GroupLibraryEntry:
    """
    Pin a library entry (member only).

    Args:
        entry_id: UUID of the library entry
        user: User pinning the entry (must be a member)

    Returns:
        Updated GroupLibraryEntry

    Raises:
        GroupLibraryEntry.DoesNotExist: If entry doesn't exist
        NotMemberError: If user is not a member
    """
    entry = (
        GroupLibraryEntry.objects
        .select_for_update()
        .select_related('group')
        .get(id=entry_id)
    )

    # Check if user is member
    if not entry.group.has_member(user):
        raise NotMemberError("You must be a member to modify the library")

    entry.pinned = True
    entry.save(update_fields=['pinned'])

    return entry


@transaction.atomic
def unpin_library_entry(*, entry_id: UUID, user: User) -> GroupLibraryEntry:
    """
    Unpin a library entry (member only).

    Args:
        entry_id: UUID of the library entry
        user: User unpinning the entry (must be a member)

    Returns:
        Updated GroupLibraryEntry

    Raises:
        GroupLibraryEntry.DoesNotExist: If entry doesn't exist
        NotMemberError: If user is not a member
    """
    entry = (
        GroupLibraryEntry.objects
        .select_for_update()
        .select_related('group')
        .get(id=entry_id)
    )

    # Check if user is member
    if not entry.group.has_member(user):
        raise NotMemberError("You must be a member to modify the library")

    entry.pinned = False
    entry.save(update_fields=['pinned'])

    return entry


def get_group_library(*, group_id: UUID, user: User) -> QuerySet[GroupLibraryEntry]:
    """
    Get group's coffee library (member only).

    Args:
        group_id: UUID of the group
        user: User requesting the library (must be a member)

    Returns:
        QuerySet of GroupLibraryEntry instances

    Raises:
        GroupNotFoundError: If group doesn't exist
        NotMemberError: If user is not a member
    """
    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        raise GroupNotFoundError(f"Group with ID {group_id} not found")

    # Check if user is member
    if not group.has_member(user):
        raise NotMemberError("You must be a member to view the group library")

    return (
        GroupLibraryEntry.objects
        .filter(group=group)
        .select_related('coffeebean', 'added_by')
        .order_by('-pinned', '-added_at')
    )
