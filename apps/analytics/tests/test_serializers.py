"""
Tests for analytics input serializers.

This module tests the input validation serializers created in Phase 2
of the analytics app refactoring.
"""
import pytest
from datetime import date
from apps.analytics.serializers import (
    PeriodQuerySerializer,
    TopBeansQuerySerializer,
    TimeseriesQuerySerializer,
)


class TestPeriodQuerySerializer:
    """Test PeriodQuerySerializer validation."""

    def test_valid_period_format(self):
        """Test valid period format (YYYY-MM)."""
        serializer = PeriodQuerySerializer(data={'period': '2025-01'})
        assert serializer.is_valid()
        assert serializer.validated_data['start_date'] == date(2025, 1, 1)
        assert serializer.validated_data['end_date'] == date(2025, 1, 31)

    def test_valid_period_december(self):
        """Test period conversion for December (edge case)."""
        serializer = PeriodQuerySerializer(data={'period': '2024-12'})
        assert serializer.is_valid()
        assert serializer.validated_data['start_date'] == date(2024, 12, 1)
        assert serializer.validated_data['end_date'] == date(2024, 12, 31)

    def test_invalid_period_format(self):
        """Test invalid period format (missing leading zero)."""
        serializer = PeriodQuerySerializer(data={'period': '2025-1'})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_invalid_period_month(self):
        """Test invalid month number."""
        serializer = PeriodQuerySerializer(data={'period': '2025-13'})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_invalid_period_year(self):
        """Test invalid year."""
        serializer = PeriodQuerySerializer(data={'period': 'abcd-01'})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_date_range_valid(self):
        """Test valid date range."""
        serializer = PeriodQuerySerializer(data={
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
        })
        assert serializer.is_valid()
        assert serializer.validated_data['start_date'] == date(2025, 1, 1)
        assert serializer.validated_data['end_date'] == date(2025, 1, 31)

    def test_date_range_validation_fails(self):
        """Test that end_date before start_date fails validation."""
        serializer = PeriodQuerySerializer(data={
            'start_date': '2025-02-01',
            'end_date': '2025-01-01',  # Before start
        })
        assert not serializer.is_valid()
        assert 'end_date' in serializer.errors

    def test_empty_data(self):
        """Test that empty data is valid (all fields optional)."""
        serializer = PeriodQuerySerializer(data={})
        assert serializer.is_valid()
        assert 'start_date' not in serializer.validated_data
        assert 'end_date' not in serializer.validated_data

    def test_period_overrides_dates(self):
        """Test that period parameter overrides explicit dates."""
        serializer = PeriodQuerySerializer(data={
            'period': '2025-01',
            'start_date': '2025-06-01',  # Should be ignored
            'end_date': '2025-06-30',    # Should be ignored
        })
        assert serializer.is_valid()
        # Period should override dates
        assert serializer.validated_data['start_date'] == date(2025, 1, 1)
        assert serializer.validated_data['end_date'] == date(2025, 1, 31)


class TestTopBeansQuerySerializer:
    """Test TopBeansQuerySerializer validation."""

    def test_valid_metric_rating(self):
        """Test valid metric: rating."""
        serializer = TopBeansQuerySerializer(data={'metric': 'rating'})
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'rating'

    def test_valid_metric_kg(self):
        """Test valid metric: kg."""
        serializer = TopBeansQuerySerializer(data={'metric': 'kg'})
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'kg'

    def test_valid_metric_money(self):
        """Test valid metric: money."""
        serializer = TopBeansQuerySerializer(data={'metric': 'money'})
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'money'

    def test_valid_metric_reviews(self):
        """Test valid metric: reviews."""
        serializer = TopBeansQuerySerializer(data={'metric': 'reviews'})
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'reviews'

    def test_invalid_metric(self):
        """Test invalid metric value."""
        serializer = TopBeansQuerySerializer(data={'metric': 'invalid'})
        assert not serializer.is_valid()
        assert 'metric' in serializer.errors

    def test_default_values(self):
        """Test default values are applied."""
        serializer = TopBeansQuerySerializer(data={})
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'rating'
        assert serializer.validated_data['period'] == 30
        assert serializer.validated_data['limit'] == 10

    def test_period_valid_range(self):
        """Test valid period values."""
        serializer = TopBeansQuerySerializer(data={'period': 7})
        assert serializer.is_valid()
        assert serializer.validated_data['period'] == 7

    def test_period_min_bound(self):
        """Test period minimum bound (1)."""
        serializer = TopBeansQuerySerializer(data={'period': 0})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_period_max_bound(self):
        """Test period maximum bound (365)."""
        serializer = TopBeansQuerySerializer(data={'period': 366})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_limit_valid_range(self):
        """Test valid limit values."""
        serializer = TopBeansQuerySerializer(data={'limit': 50})
        assert serializer.is_valid()
        assert serializer.validated_data['limit'] == 50

    def test_limit_min_bound(self):
        """Test limit minimum bound (1)."""
        serializer = TopBeansQuerySerializer(data={'limit': 0})
        assert not serializer.is_valid()
        assert 'limit' in serializer.errors

    def test_limit_max_bound(self):
        """Test limit maximum bound (100)."""
        serializer = TopBeansQuerySerializer(data={'limit': 200})
        assert not serializer.is_valid()
        assert 'limit' in serializer.errors

    def test_all_params_valid(self):
        """Test all parameters together."""
        serializer = TopBeansQuerySerializer(data={
            'metric': 'kg',
            'period': 60,
            'limit': 20,
        })
        assert serializer.is_valid()
        assert serializer.validated_data['metric'] == 'kg'
        assert serializer.validated_data['period'] == 60
        assert serializer.validated_data['limit'] == 20


class TestTimeseriesQuerySerializer:
    """Test TimeseriesQuerySerializer validation."""

    def test_valid_granularity_day(self):
        """Test valid granularity: day."""
        serializer = TimeseriesQuerySerializer(data={'granularity': 'day'})
        assert serializer.is_valid()
        assert serializer.validated_data['granularity'] == 'day'

    def test_valid_granularity_week(self):
        """Test valid granularity: week."""
        serializer = TimeseriesQuerySerializer(data={'granularity': 'week'})
        assert serializer.is_valid()
        assert serializer.validated_data['granularity'] == 'week'

    def test_valid_granularity_month(self):
        """Test valid granularity: month."""
        serializer = TimeseriesQuerySerializer(data={'granularity': 'month'})
        assert serializer.is_valid()
        assert serializer.validated_data['granularity'] == 'month'

    def test_invalid_granularity(self):
        """Test invalid granularity value."""
        serializer = TimeseriesQuerySerializer(data={'granularity': 'year'})
        assert not serializer.is_valid()
        assert 'granularity' in serializer.errors

    def test_default_granularity(self):
        """Test default granularity is 'month'."""
        serializer = TimeseriesQuerySerializer(data={})
        assert serializer.is_valid()
        assert serializer.validated_data['granularity'] == 'month'

    def test_user_id_valid(self):
        """Test valid user_id (UUID)."""
        user_uuid = '550e8400-e29b-41d4-a716-446655440000'
        serializer = TimeseriesQuerySerializer(data={'user_id': user_uuid})
        assert serializer.is_valid()
        assert str(serializer.validated_data['user_id']) == user_uuid

    def test_user_id_invalid(self):
        """Test invalid user_id (not a UUID)."""
        serializer = TimeseriesQuerySerializer(data={'user_id': 'not-a-uuid'})
        assert not serializer.is_valid()
        assert 'user_id' in serializer.errors

    def test_group_id_valid(self):
        """Test valid group_id (UUID)."""
        group_uuid = '660e8400-e29b-41d4-a716-446655440000'
        serializer = TimeseriesQuerySerializer(data={'group_id': group_uuid})
        assert serializer.is_valid()
        assert str(serializer.validated_data['group_id']) == group_uuid

    def test_group_id_invalid(self):
        """Test invalid group_id (not a UUID)."""
        serializer = TimeseriesQuerySerializer(data={'group_id': 'not-a-uuid'})
        assert not serializer.is_valid()
        assert 'group_id' in serializer.errors

    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        serializer = TimeseriesQuerySerializer(data={})
        assert serializer.is_valid()
        # Should only have granularity with default value
        assert serializer.validated_data['granularity'] == 'month'
        assert 'user_id' not in serializer.validated_data
        assert 'group_id' not in serializer.validated_data

    def test_all_params_valid(self):
        """Test all parameters together."""
        user_uuid = '550e8400-e29b-41d4-a716-446655440000'
        serializer = TimeseriesQuerySerializer(data={
            'user_id': user_uuid,
            'granularity': 'week',
        })
        assert serializer.is_valid()
        assert str(serializer.validated_data['user_id']) == user_uuid
        assert serializer.validated_data['granularity'] == 'week'
