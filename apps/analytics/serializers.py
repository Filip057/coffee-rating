"""
Serializers for analytics app.

This module contains:
1. Input serializers - Query parameter validation
2. Response serializers - API documentation and output formatting

Input Serializers:
    PeriodQuerySerializer - Validates period and date range parameters
    TopBeansQuerySerializer - Validates top beans query parameters
    TimeseriesQuerySerializer - Validates timeseries query parameters

Response Serializers:
    UserConsumptionSerializer - User consumption statistics
    GroupConsumptionSerializer - Group consumption with member breakdown
    TopBeansResponseSerializer - Top beans ranking response
    TimeseriesResponseSerializer - Time series data for charts
    TasteProfileSerializer - User taste profile
    DashboardResponseSerializer - Dashboard summary
"""

from rest_framework import serializers
from datetime import datetime, timedelta


# =============================================================================
# Input Serializers (Query Parameter Validation)
# =============================================================================

class PeriodQuerySerializer(serializers.Serializer):
    """
    Validate period and date range query parameters.

    Used by: user_consumption, group_consumption

    Query Parameters:
        period (str): Month period in YYYY-MM format (e.g., '2025-01')
        start_date (date): Start of date range
        end_date (date): End of date range

    Note:
        If 'period' is provided, it takes precedence and is converted
        to start_date and end_date for the full month.
    """

    period = serializers.RegexField(
        regex=r'^\d{4}-(0[1-9]|1[0-2])$',
        required=False,
        allow_blank=True,
        help_text='Month period in YYYY-MM format'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        """Parse period into date range if provided."""
        period = attrs.get('period')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        # If period provided, convert to date range
        if period:
            try:
                year, month = period.split('-')
                year, month = int(year), int(month)
                attrs['start_date'] = datetime(year, month, 1).date()
                # Last day of month
                if month == 12:
                    attrs['end_date'] = datetime(year + 1, 1, 1).date() - timedelta(days=1)
                else:
                    attrs['end_date'] = datetime(year, month + 1, 1).date() - timedelta(days=1)
            except (ValueError, AttributeError):
                raise serializers.ValidationError({
                    'period': 'Invalid period format. Use YYYY-MM'
                })

        # Validate date range if both provided
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError({
                'start_date': 'Start date must be before end date'
            })

        return attrs


class TopBeansQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for top beans endpoint.

    Used by: top_beans

    Query Parameters:
        metric (str): Ranking metric - 'rating', 'kg', 'money', or 'reviews'
        period (int): Number of days to consider (1-365)
        limit (int): Number of results to return (1-100)
    """

    VALID_METRICS = ('rating', 'kg', 'money', 'reviews')

    metric = serializers.ChoiceField(
        choices=VALID_METRICS,
        default='rating',
        help_text="Ranking metric: 'rating', 'kg', 'money', or 'reviews'"
    )
    period = serializers.IntegerField(
        min_value=1,
        max_value=365,
        required=False,
        default=30,
        help_text='Number of days to consider (1-365)'
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=100,
        required=False,
        default=10,
        help_text='Number of results (1-100)'
    )


class TimeseriesQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for timeseries endpoint.

    Used by: consumption_timeseries

    Query Parameters:
        user_id (UUID): User ID (defaults to current user)
        group_id (UUID): Group ID for group consumption
        granularity (str): Time granularity - 'day', 'week', or 'month'
    """

    VALID_GRANULARITIES = ('day', 'week', 'month')

    user_id = serializers.UUIDField(required=False)
    group_id = serializers.UUIDField(required=False)
    granularity = serializers.ChoiceField(
        choices=VALID_GRANULARITIES,
        default='month',
        help_text="Time granularity: 'day', 'week', or 'month'"
    )


# =============================================================================
# Response Serializers (API Documentation)
# =============================================================================

class UserConsumptionSerializer(serializers.Serializer):
    """Response serializer for user consumption statistics."""
    total_kg = serializers.FloatField()
    total_czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()
    unique_beans = serializers.IntegerField(required=False)
    avg_price_per_kg = serializers.FloatField(allow_null=True)
    period_start = serializers.DateField(allow_null=True, required=False)
    period_end = serializers.DateField(allow_null=True, required=False)


class MemberBreakdownUserSerializer(serializers.Serializer):
    """Nested serializer for user in member breakdown."""
    id = serializers.CharField()
    email = serializers.EmailField()
    display_name = serializers.CharField()


class MemberBreakdownSerializer(serializers.Serializer):
    """Nested serializer for member consumption breakdown."""
    user = MemberBreakdownUserSerializer()
    kg = serializers.FloatField()
    czk = serializers.FloatField()
    share_percentage = serializers.FloatField(required=False)


class GroupConsumptionSerializer(serializers.Serializer):
    """Response serializer for group consumption statistics."""
    total_kg = serializers.FloatField()
    total_czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()
    unique_beans = serializers.IntegerField(required=False)
    member_breakdown = MemberBreakdownSerializer(many=True)


class TopBeanSerializer(serializers.Serializer):
    """Nested serializer for a single top bean entry."""
    id = serializers.CharField()
    name = serializers.CharField()
    roastery_name = serializers.CharField()
    score = serializers.FloatField()
    metric = serializers.CharField()
    review_count = serializers.IntegerField(required=False)
    avg_rating = serializers.FloatField(required=False)
    total_kg = serializers.FloatField(required=False)
    total_spent_czk = serializers.CharField(required=False)


class TopBeansResponseSerializer(serializers.Serializer):
    """Response serializer for top beans ranking."""
    metric = serializers.CharField()
    period_days = serializers.IntegerField(allow_null=True)
    results = TopBeanSerializer(many=True)


class TimeseriesPointSerializer(serializers.Serializer):
    """Nested serializer for a single timeseries data point."""
    period = serializers.CharField()
    kg = serializers.FloatField()
    czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()


class TimeseriesResponseSerializer(serializers.Serializer):
    """Response serializer for consumption timeseries."""
    granularity = serializers.CharField()
    data = TimeseriesPointSerializer(many=True)


class TasteProfileSerializer(serializers.Serializer):
    """Response serializer for user taste profile."""
    review_count = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    favorite_tags = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    favorite_origins = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    favorite_roast_profiles = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    preferred_roast = serializers.CharField(allow_null=True, required=False)
    preferred_origin = serializers.CharField(allow_null=True, required=False)
    common_tags = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    brew_methods = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class DashboardTopBeanSerializer(serializers.Serializer):
    """Nested serializer for top beans in dashboard."""
    id = serializers.CharField()
    name = serializers.CharField()
    roastery_name = serializers.CharField()
    avg_rating = serializers.FloatField()
    review_count = serializers.IntegerField()


class DashboardResponseSerializer(serializers.Serializer):
    """Response serializer for dashboard summary."""
    consumption = UserConsumptionSerializer()
    taste_profile = TasteProfileSerializer(allow_null=True)
    top_beans = DashboardTopBeanSerializer(many=True)


class ErrorSerializer(serializers.Serializer):
    """Standard error response serializer."""
    error = serializers.CharField()


class NoReviewsSerializer(serializers.Serializer):
    """Response when user has no reviews."""
    message = serializers.CharField()
    review_count = serializers.IntegerField()
