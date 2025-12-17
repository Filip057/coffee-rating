"""Services for beans business logic."""

from .exceptions import (
    BeansServiceError,
    BeanNotFoundError,
    DuplicateBeanError,
    BeanMergeError,
    InvalidMergeError,
    VariantNotFoundError,
    DuplicateVariantError,
)
from .bean_management import (
    create_bean,
    update_bean,
    soft_delete_bean,
    get_bean_by_id,
)
from .bean_search import (
    search_beans,
    get_all_roasteries,
    get_all_origins,
)
from .rating_aggregation import (
    update_bean_rating,
    get_top_rated_beans,
    get_most_reviewed_beans,
)
from .bean_deduplication import (
    normalize_text,
    find_potential_duplicates,
    batch_find_duplicates,
    EXACT_MATCH_THRESHOLD,
    HIGH_SIMILARITY_THRESHOLD,
    MEDIUM_SIMILARITY_THRESHOLD,
)
from .bean_merging import (
    merge_beans,
)
from .variant_management import (
    create_variant,
    update_variant,
    soft_delete_variant,
)

__all__ = [
    # Exceptions
    'BeansServiceError',
    'BeanNotFoundError',
    'DuplicateBeanError',
    'BeanMergeError',
    'InvalidMergeError',
    'VariantNotFoundError',
    'DuplicateVariantError',
    # Bean Management
    'create_bean',
    'update_bean',
    'soft_delete_bean',
    'get_bean_by_id',
    # Bean Search
    'search_beans',
    'get_all_roasteries',
    'get_all_origins',
    # Rating Aggregation
    'update_bean_rating',
    'get_top_rated_beans',
    'get_most_reviewed_beans',
    # Bean Deduplication
    'normalize_text',
    'find_potential_duplicates',
    'batch_find_duplicates',
    'EXACT_MATCH_THRESHOLD',
    'HIGH_SIMILARITY_THRESHOLD',
    'MEDIUM_SIMILARITY_THRESHOLD',
    # Bean Merging
    'merge_beans',
    # Variant Management
    'create_variant',
    'update_variant',
    'soft_delete_variant',
]
