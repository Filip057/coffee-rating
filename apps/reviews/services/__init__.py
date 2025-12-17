"""
Reviews services - Business logic layer.

This package contains all business operations for the reviews app:
- Review CRUD operations
- User library management
- Tag management
- Statistics and analytics
"""

# Phase 2: Review Management
from .review_management import (
    create_review,
    get_review_by_id,
    update_review,
    delete_review,
    get_user_reviews,
)

# Phase 3: Library Management
from .library_management import (
    add_to_library,
    remove_from_library,
    archive_library_entry,
    get_user_library,
)

# Phase 4: Tag Management
from .tag_management import (
    create_tag,
    get_tag_by_id,
    get_popular_tags,
    search_tags,
)

# Phase 5: Statistics
from .statistics import (
    get_review_statistics,
    get_bean_review_summary,
)

# Domain Exceptions
from .exceptions import (
    ReviewsServiceError,
    ReviewNotFoundError,
    DuplicateReviewError,
    InvalidRatingError,
    BeanNotFoundError,
    LibraryEntryNotFoundError,
    TagNotFoundError,
    UnauthorizedReviewActionError,
    InvalidContextError,
    GroupMembershipRequiredError,
)

__all__ = [
    # Review Management Services
    'create_review',
    'get_review_by_id',
    'update_review',
    'delete_review',
    'get_user_reviews',
    # Library Management Services
    'add_to_library',
    'remove_from_library',
    'archive_library_entry',
    'get_user_library',
    # Tag Management Services
    'create_tag',
    'get_tag_by_id',
    'get_popular_tags',
    'search_tags',
    # Statistics Services
    'get_review_statistics',
    'get_bean_review_summary',
    # Exceptions
    'ReviewsServiceError',
    'ReviewNotFoundError',
    'DuplicateReviewError',
    'InvalidRatingError',
    'BeanNotFoundError',
    'LibraryEntryNotFoundError',
    'TagNotFoundError',
    'UnauthorizedReviewActionError',
    'InvalidContextError',
    'GroupMembershipRequiredError',
]
