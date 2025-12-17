"""Library management service - User's personal coffee library operations."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet, Q
from uuid import UUID
from typing import Optional

from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.reviews.models import UserLibraryEntry
from .exceptions import (
    BeanNotFoundError,
    LibraryEntryNotFoundError,
)


@transaction.atomic
def add_to_library(
    *,
    user: User,
    coffeebean_id: UUID,
    added_by: str = 'manual'
) -> tuple[UserLibraryEntry, bool]:
    """
    Add a coffee bean to user's personal library.

    Uses get_or_create to handle duplicates gracefully.
    If bean already in library, returns existing entry.

    This operation:
    1. Validates coffee bean exists and is active
    2. Creates or retrieves library entry atomically
    3. Handles race conditions with IntegrityError catch

    Args:
        user: User adding the bean
        coffeebean_id: UUID of coffee bean to add
        added_by: Source ('review', 'purchase', 'manual')

    Returns:
        Tuple of (UserLibraryEntry, created: bool)
        - created=True: New entry was created
        - created=False: Entry already existed

    Raises:
        BeanNotFoundError: If coffee bean doesn't exist or inactive
    """
    # Validate coffee bean exists and is active
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Get or create library entry
    try:
        entry, created = UserLibraryEntry.objects.get_or_create(
            user=user,
            coffeebean=coffeebean,
            defaults={'added_by': added_by}
        )
    except IntegrityError:
        # Rare race condition: entry created between get and create
        # Fetch the existing entry
        entry = UserLibraryEntry.objects.get(user=user, coffeebean=coffeebean)
        created = False

    return entry, created


@transaction.atomic
def remove_from_library(*, entry_id: UUID, user: User) -> None:
    """
    Remove a coffee bean from user's library.

    This operation:
    1. Locks the library entry row
    2. Verifies user ownership
    3. Deletes the entry atomically

    Args:
        entry_id: UUID of library entry to remove
        user: User removing the entry (must be owner)

    Raises:
        LibraryEntryNotFoundError: If entry doesn't exist or belongs to another user
    """
    # Get entry with row lock
    try:
        entry = (
            UserLibraryEntry.objects
            .select_for_update()
            .get(id=entry_id, user=user)
        )
    except UserLibraryEntry.DoesNotExist:
        raise LibraryEntryNotFoundError(
            "Library entry not found or does not belong to you"
        )

    entry.delete()


@transaction.atomic
def archive_library_entry(
    *,
    entry_id: UUID,
    user: User,
    is_archived: bool = True
) -> UserLibraryEntry:
    """
    Archive or unarchive a library entry.

    Archived entries are hidden from main library view but preserved.
    Useful for coffees that are no longer available or not currently drinking.

    This operation:
    1. Locks the library entry row
    2. Verifies user ownership
    3. Updates archive status atomically

    Args:
        entry_id: UUID of library entry
        user: User performing the action (must be owner)
        is_archived: True to archive, False to unarchive

    Returns:
        Updated UserLibraryEntry

    Raises:
        LibraryEntryNotFoundError: If entry doesn't exist or belongs to another user
    """
    # Get entry with row lock
    try:
        entry = (
            UserLibraryEntry.objects
            .select_for_update()
            .get(id=entry_id, user=user)
        )
    except UserLibraryEntry.DoesNotExist:
        raise LibraryEntryNotFoundError(
            "Library entry not found or does not belong to you"
        )

    entry.is_archived = is_archived
    entry.save(update_fields=['is_archived'])

    return entry


def get_user_library(
    *,
    user: User,
    is_archived: bool = False,
    search: Optional[str] = None
) -> QuerySet[UserLibraryEntry]:
    """
    Get user's coffee library with optional filtering.

    Returns active or archived entries based on is_archived parameter.
    Can search across coffee bean name and roastery name.

    Args:
        user: User whose library to retrieve
        is_archived: Show archived (True) or active (False) entries
        search: Search in coffee bean name or roastery (case-insensitive)

    Returns:
        QuerySet of UserLibraryEntry instances ordered by most recent first
    """
    queryset = UserLibraryEntry.objects.filter(
        user=user,
        is_archived=is_archived
    ).select_related('coffeebean')

    if search:
        queryset = queryset.filter(
            Q(coffeebean__name__icontains=search) |
            Q(coffeebean__roastery_name__icontains=search)
        )

    return queryset.order_by('-added_at')
