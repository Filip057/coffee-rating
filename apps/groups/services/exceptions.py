"""
Domain-specific exceptions for groups app.

These exceptions represent business rule violations and should be
caught in views and converted to appropriate HTTP responses.
"""


class GroupsServiceError(Exception):
    """Base exception for all groups service errors."""
    pass


class GroupNotFoundError(GroupsServiceError):
    """Raised when a group does not exist or is inaccessible."""
    pass


class InvalidInviteCodeError(GroupsServiceError):
    """Raised when an invite code is incorrect."""
    pass


class AlreadyMemberError(GroupsServiceError):
    """Raised when a user tries to join a group they're already in."""
    pass


class NotMemberError(GroupsServiceError):
    """Raised when a user tries to perform an action requiring membership."""
    pass


class OwnerCannotLeaveError(GroupsServiceError):
    """Raised when a group owner tries to leave their group."""
    pass


class CannotChangeOwnerRoleError(GroupsServiceError):
    """Raised when attempting to change the owner's role."""
    pass


class CannotRemoveOwnerError(GroupsServiceError):
    """Raised when attempting to remove the group owner."""
    pass


class DuplicateLibraryEntryError(GroupsServiceError):
    """Raised when a bean is already in the group library."""
    pass


class InsufficientPermissionsError(GroupsServiceError):
    """Raised when a user lacks required permissions for an action."""
    pass


class BeanNotFoundError(GroupsServiceError):
    """Raised when a coffee bean does not exist."""
    pass
