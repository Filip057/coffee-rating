"""
Groups app services layer.

Services contain business logic and orchestrate operations across models.
All state-changing operations use transactions and concurrency protection.
"""

from .exceptions import (
    GroupsServiceError,
    GroupNotFoundError,
    InvalidInviteCodeError,
    AlreadyMemberError,
    NotMemberError,
    OwnerCannotLeaveError,
    CannotChangeOwnerRoleError,
    CannotRemoveOwnerError,
    DuplicateLibraryEntryError,
    InsufficientPermissionsError,
    BeanNotFoundError,
)

# Service functions will be imported as they are implemented in subsequent phases
from .group_management import (
    create_group,
    update_group,
    delete_group,
    get_group_by_id,
)

from .membership_management import (
    join_group,
    leave_group,
    remove_member,
    get_group_members,
)

from .role_management import (
    update_member_role,
)
#
# from .invite_management import (
#     regenerate_invite_code,
#     validate_invite_code,
# )
#
# from .library_management import (
#     add_to_library,
#     remove_from_library,
#     pin_library_entry,
#     unpin_library_entry,
#     get_group_library,
# )


__all__ = [
    # Exceptions
    'GroupsServiceError',
    'GroupNotFoundError',
    'InvalidInviteCodeError',
    'AlreadyMemberError',
    'NotMemberError',
    'OwnerCannotLeaveError',
    'CannotChangeOwnerRoleError',
    'CannotRemoveOwnerError',
    'DuplicateLibraryEntryError',
    'InsufficientPermissionsError',
    'BeanNotFoundError',

    # Group Management (Phase 2)
    'create_group',
    'update_group',
    'delete_group',
    'get_group_by_id',

    # Membership Management (Phase 3)
    'join_group',
    'leave_group',
    'remove_member',
    'get_group_members',

    # Role Management (Phase 4)
    'update_member_role',

    # Invite Management (Phase 5)
    # 'regenerate_invite_code',
    # 'validate_invite_code',

    # Library Management (Phase 6)
    # 'add_to_library',
    # 'remove_from_library',
    # 'pin_library_entry',
    # 'unpin_library_entry',
    # 'get_group_library',
]
