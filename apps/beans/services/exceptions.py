"""Domain-specific exceptions for beans services."""


class BeansServiceError(Exception):
    """Base exception for beans services."""
    pass


class BeanNotFoundError(BeansServiceError):
    """Raised when bean does not exist."""
    pass


class DuplicateBeanError(BeansServiceError):
    """Raised when attempting to create duplicate bean."""
    pass


class BeanMergeError(BeansServiceError):
    """Raised when bean merge operation fails."""
    pass


class InvalidMergeError(BeansServiceError):
    """Raised when merge parameters are invalid."""
    pass


class VariantNotFoundError(BeansServiceError):
    """Raised when variant does not exist."""
    pass


class DuplicateVariantError(BeansServiceError):
    """Raised when variant already exists for bean/weight combo."""
    pass
