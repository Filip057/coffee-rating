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


# Services will be implemented in Phase 6
