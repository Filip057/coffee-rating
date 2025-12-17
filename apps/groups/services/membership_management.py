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


# Services will be implemented in Phase 3
