"""
Domain exceptions for analytics app.

This module defines domain-specific exceptions that are raised by the
analytics services layer. These exceptions represent business rule
violations and invalid operations, separate from HTTP concerns.

Exception Hierarchy:
    AnalyticsServiceError (base)
    ├── InvalidPeriodError
    ├── InvalidDateRangeError
    ├── InvalidMetricError
    ├── InvalidGranularityError
    ├── GroupNotFoundError
    └── UserNotFoundError

Usage:
    from apps.analytics.exceptions import InvalidMetricError

    if metric not in VALID_METRICS:
        raise InvalidMetricError(f"Invalid metric: {metric}")
"""


class AnalyticsServiceError(Exception):
    """
    Base exception for all analytics service errors.

    All domain-specific exceptions in the analytics app inherit from this
    class, making it easy to catch all analytics errors in views:

        try:
            data = AnalyticsQueries.top_beans(metric='invalid')
        except AnalyticsServiceError as e:
            return Response({'error': str(e)}, status=400)
    """

    pass


class InvalidPeriodError(AnalyticsServiceError):
    """
    Raised when period format is invalid.

    Period must be in YYYY-MM format (e.g., '2025-01').

    Example:
        raise InvalidPeriodError("Invalid period format. Use YYYY-MM")
    """

    pass


class InvalidDateRangeError(AnalyticsServiceError):
    """
    Raised when date range is invalid.

    Typically when start_date is after end_date.

    Example:
        raise InvalidDateRangeError("Start date must be before end date")
    """

    pass


class InvalidMetricError(AnalyticsServiceError):
    """
    Raised when an invalid ranking metric is specified.

    Valid metrics are: rating, kg, money, reviews.

    Example:
        raise InvalidMetricError(
            "Invalid metric: 'invalid'. Valid options: rating, kg, money, reviews"
        )
    """

    pass


class InvalidGranularityError(AnalyticsServiceError):
    """
    Raised when an invalid time granularity is specified.

    Valid granularities are: day, week, month.

    Example:
        raise InvalidGranularityError(
            "Invalid granularity: 'year'. Valid options: day, week, month"
        )
    """

    pass


class GroupNotFoundError(AnalyticsServiceError):
    """
    Raised when the specified group does not exist.

    Example:
        raise GroupNotFoundError("Group not found")
    """

    pass


class UserNotFoundError(AnalyticsServiceError):
    """
    Raised when the specified user does not exist.

    Example:
        raise UserNotFoundError("User not found")
    """

    pass


class MissingParameterError(AnalyticsServiceError):
    """
    Raised when a required parameter is missing.

    Example:
        raise MissingParameterError("Either user_id or group_id is required")
    """

    pass
