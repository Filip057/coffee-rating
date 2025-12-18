"""
Domain exceptions for purchases app.

This module defines the exception hierarchy for purchase-related errors,
providing specific error types for better error handling and testing.

Created in Phase 1 of purchases app refactoring.
"""
from rest_framework.exceptions import APIException


class PurchaseServiceError(Exception):
    """Base exception for purchase service errors."""
    pass


class NoParticipantsError(PurchaseServiceError):
    """Raised when no participants found for purchase split."""
    pass


class InvalidSplitError(PurchaseServiceError):
    """Raised when split calculation is invalid."""
    pass


class PaymentShareNotFoundError(APIException):
    """Payment share not found."""
    status_code = 404
    default_detail = 'Payment share not found.'
    default_code = 'payment_share_not_found'


class PaymentAlreadyPaidError(APIException):
    """Payment share already marked as paid."""
    status_code = 400
    default_detail = 'Payment share is already marked as paid.'
    default_code = 'payment_already_paid'


class InvalidStateTransitionError(APIException):
    """Invalid payment state transition."""
    status_code = 400
    default_detail = 'Invalid state transition for payment share.'
    default_code = 'invalid_state_transition'


class InsufficientPermissionsError(APIException):
    """User doesn't have permission for operation."""
    status_code = 403
    default_detail = 'You do not have permission to perform this action.'
    default_code = 'insufficient_permissions'


class InvalidGroupMembershipError(APIException):
    """User is not a member of the required group."""
    status_code = 403
    default_detail = 'You must be a member of this group.'
    default_code = 'invalid_group_membership'


class PurchaseNotFoundError(APIException):
    """Purchase record not found."""
    status_code = 404
    default_detail = 'Purchase record not found.'
    default_code = 'purchase_not_found'


class SPDGenerationError(PurchaseServiceError):
    """SPD QR code generation failed."""
    pass
