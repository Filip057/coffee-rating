"""Domain exceptions for reviews app."""


class ReviewsServiceError(Exception):
    """Base exception for all reviews service errors."""
    pass


class ReviewNotFoundError(ReviewsServiceError):
    """Review does not exist or is inaccessible."""
    pass


class DuplicateReviewError(ReviewsServiceError):
    """User already reviewed this coffee bean."""
    pass


class InvalidRatingError(ReviewsServiceError):
    """Rating must be between 1 and 5."""
    pass


class BeanNotFoundError(ReviewsServiceError):
    """Coffee bean does not exist or is inactive."""
    pass


class LibraryEntryNotFoundError(ReviewsServiceError):
    """Library entry does not exist or belongs to another user."""
    pass


class TagNotFoundError(ReviewsServiceError):
    """Tag does not exist."""
    pass


class UnauthorizedReviewActionError(ReviewsServiceError):
    """User cannot modify this review."""
    pass


class InvalidContextError(ReviewsServiceError):
    """Invalid review context or missing required fields."""
    pass


class GroupMembershipRequiredError(ReviewsServiceError):
    """User must be group member to create group review."""
    pass
