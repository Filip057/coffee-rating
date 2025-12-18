# Analytics App - Refactoring Checklist

> **Created:** 2025-12-17
> **App:** `apps/analytics`
> **Reference:** [ANALYTICS_APP_ANALYSIS.md](./ANALYTICS_APP_ANALYSIS.md)
> **Pattern:** DRF Best Practices for Read-Only Apps

---

## Overview

This checklist provides a **step-by-step plan** to refactor the analytics app following DRF best practices. Since analytics is a read-only query layer, the focus is on:

1. Input validation with serializers
2. Domain exceptions
3. Custom permission classes
4. Moving response formatting to serializers
5. Optimizing N+1 queries

**Note:** Transaction safety and concurrency protection are NOT needed for this read-only app.

**Total Phases:** 7
**Difficulty:** Easy-Medium

---

## Phase 1: Create Domain Exceptions

**Goal:** Define domain-specific exceptions for analytics errors

### Tasks

1. Create exceptions file:

```bash
touch apps/analytics/exceptions.py
```

2. Implement exceptions in `apps/analytics/exceptions.py`:

```python
"""Domain exceptions for analytics app."""


class AnalyticsServiceError(Exception):
    """Base exception for all analytics service errors."""
    pass


class InvalidPeriodError(AnalyticsServiceError):
    """Period format must be YYYY-MM."""
    pass


class InvalidDateRangeError(AnalyticsServiceError):
    """Start date must be before end date."""
    pass


class InvalidMetricError(AnalyticsServiceError):
    """Invalid ranking metric specified."""
    pass


class InvalidGranularityError(AnalyticsServiceError):
    """Invalid time granularity specified."""
    pass


class GroupNotFoundError(AnalyticsServiceError):
    """Group does not exist."""
    pass


class UserNotFoundError(AnalyticsServiceError):
    """User does not exist."""
    pass
```

3. Update `AnalyticsQueries.top_beans()` to use domain exception:

```python
# BEFORE
else:
    raise ValueError(f"Invalid metric: {metric}")

# AFTER
from .exceptions import InvalidMetricError

else:
    raise InvalidMetricError(
        f"Invalid metric: {metric}. Valid options: rating, kg, money, reviews"
    )
```

### Verification

- [ ] `exceptions.py` created
- [ ] All exception classes defined
- [ ] `top_beans()` raises `InvalidMetricError`
- [ ] No syntax errors

---

## Phase 2: Create Input Serializers

**Goal:** Move query parameter validation from views to serializers

### Tasks

1. Create serializers file:

```bash
touch apps/analytics/serializers.py
```

2. Move response serializers from `views.py` to `serializers.py`

3. Add input serializers in `apps/analytics/serializers.py`:

```python
"""Serializers for analytics app - input validation and output formatting."""

from rest_framework import serializers
from datetime import datetime, timedelta
from .exceptions import InvalidPeriodError, InvalidDateRangeError


# =============================================================================
# Input Serializers (Query Parameter Validation)
# =============================================================================

class PeriodQuerySerializer(serializers.Serializer):
    """Validate period and date range query parameters."""

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

        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                'start_date': 'Start date must be before end date'
            })

        return attrs


class TopBeansQuerySerializer(serializers.Serializer):
    """Validate query parameters for top beans endpoint."""

    VALID_METRICS = ('rating', 'kg', 'money', 'reviews')

    metric = serializers.ChoiceField(
        choices=VALID_METRICS,
        default='rating',
        help_text='Ranking metric: rating, kg, money, or reviews'
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
    """Validate query parameters for timeseries endpoint."""

    VALID_GRANULARITIES = ('day', 'week', 'month')

    user_id = serializers.UUIDField(required=False)
    group_id = serializers.UUIDField(required=False)
    granularity = serializers.ChoiceField(
        choices=VALID_GRANULARITIES,
        default='month',
        help_text='Time granularity: day, week, or month'
    )


# =============================================================================
# Response Serializers (move from views.py)
# =============================================================================

class UserConsumptionSerializer(serializers.Serializer):
    """Response serializer for user consumption data."""
    total_kg = serializers.FloatField()
    total_czk = serializers.FloatField()
    purchases_count = serializers.IntegerField()
    unique_beans = serializers.IntegerField(required=False)
    avg_price_per_kg = serializers.FloatField(allow_null=True)
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField(allow_null=True)


# ... (move all other response serializers from views.py)
```

### Verification

- [ ] `serializers.py` created
- [ ] Input serializers with validation
- [ ] Response serializers moved from views.py
- [ ] Period parsing moved from views to serializer

---

## Phase 3: Create Custom Permission Class

**Goal:** Replace inline group membership checks with declarative permission

### Tasks

1. Create permissions file:

```bash
touch apps/analytics/permissions.py
```

2. Implement permission class in `apps/analytics/permissions.py`:

```python
"""Custom permission classes for analytics app."""

from rest_framework.permissions import BasePermission
from apps.groups.models import Group


class IsGroupMemberForAnalytics(BasePermission):
    """
    Permission check for group analytics access.

    Allows access if:
    - No group_id specified (returns True)
    - User is a member of the specified group

    Used by: group_consumption, consumption_timeseries (with group_id)
    """

    message = 'You must be a member of this group to view its analytics.'

    def has_permission(self, request, view):
        # Check URL kwargs first (for group_consumption)
        group_id = view.kwargs.get('group_id')

        # Check query params (for consumption_timeseries)
        if not group_id:
            group_id = request.query_params.get('group_id')

        # No group specified - allow (user endpoints)
        if not group_id:
            return True

        # Verify group membership
        try:
            group = Group.objects.get(id=group_id)
            return group.has_member(request.user)
        except Group.DoesNotExist:
            return False


class IsGroupMemberOrReadOnly(BasePermission):
    """
    For future use: Allow read access to public group data,
    but require membership for private groups.
    """
    pass
```

### Verification

- [ ] `permissions.py` created
- [ ] `IsGroupMemberForAnalytics` implemented
- [ ] Permission message defined

---

## Phase 4: Refactor Services Layer

**Goal:** Return plain dictionaries instead of Django objects, add date parsing

### Tasks

1. Update `AnalyticsQueries.top_beans()` to return plain dicts:

```python
# BEFORE - Returns CoffeeBean objects
return [
    {
        'bean': bean,  # Django model object
        'score': float(bean.avg_rating),
        'review_count': bean.review_count,
        'metric': 'Average Rating'
    }
    for bean in beans
]

# AFTER - Returns plain dictionaries
return [
    {
        'bean_id': str(bean.id),
        'bean_name': bean.name,
        'roastery_name': bean.roastery_name,
        'score': float(bean.avg_rating),
        'review_count': bean.review_count,
        'avg_rating': float(bean.avg_rating),
        'metric': 'Average Rating'
    }
    for bean in beans
]
```

2. Update all metric branches in `top_beans()` similarly

3. Optimize `group_consumption()` N+1 query:

```python
# BEFORE - N+1 queries (one per member)
for membership in memberships:
    user_data = AnalyticsQueries.user_consumption(
        membership.user_id,
        start_date,
        end_date
    )

# AFTER - Single aggregated query
@staticmethod
def group_consumption(group_id, start_date=None, end_date=None):
    """Calculate group consumption with optimized member breakdown."""
    from apps.groups.models import GroupMembership

    # Get group purchases
    purchases = PurchaseRecord.objects.filter(group_id=group_id)

    if start_date:
        purchases = purchases.filter(date__gte=start_date)
    if end_date:
        purchases = purchases.filter(date__lte=end_date)

    # Group totals
    totals = purchases.aggregate(
        total_czk=Coalesce(Sum('total_price_czk'), Decimal('0.00')),
        total_grams=Coalesce(Sum('package_weight_grams'), 0),
        count=Count('id')
    )

    total_kg = Decimal(totals['total_grams']) / Decimal('1000.0')

    # OPTIMIZED: Aggregate all member consumption in single query
    purchase_ids = purchases.values_list('id', flat=True)

    member_shares = PaymentShare.objects.filter(
        purchase_id__in=purchase_ids,
        status=PaymentStatus.PAID
    ).values('user_id', 'user__email', 'user__display_name').annotate(
        total_czk=Sum('amount_czk'),
        total_grams=Sum(
            Case(
                When(
                    purchase__package_weight_grams__isnull=False,
                    then=F('amount_czk') / F('purchase__total_price_czk') *
                         F('purchase__package_weight_grams')
                ),
                default=Value(0),
                output_field=DecimalField()
            )
        ),
        purchases_count=Count('purchase_id', distinct=True)
    )

    member_breakdown = []
    for share in member_shares:
        share_pct = 0.0
        if totals['total_czk'] > 0:
            share_pct = float(
                (share['total_czk'] / totals['total_czk']) * 100
            )

        member_breakdown.append({
            'user': {
                'id': str(share['user_id']),
                'email': share['user__email'],
                'display_name': share['user__display_name'] or share['user__email'],
            },
            'kg': round(Decimal(share['total_grams']) / Decimal('1000.0'), 3),
            'czk': share['total_czk'],
            'share_percentage': round(share_pct, 2),
        })

    return {
        'total_kg': round(total_kg, 3),
        'total_spent_czk': totals['total_czk'],
        'purchases_count': totals['count'],
        'member_breakdown': member_breakdown,
    }
```

4. Add import for domain exceptions at top of `analytics.py`:

```python
from .exceptions import InvalidMetricError
```

### Verification

- [ ] `top_beans()` returns plain dicts, not Django objects
- [ ] Domain exception raised for invalid metric
- [ ] `group_consumption()` uses single aggregated query
- [ ] No N+1 queries remain

---

## Phase 5: Refactor Views to Use Serializers and Permissions

**Goal:** Make views thin HTTP handlers

### Tasks

1. Update imports in `views.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .analytics import AnalyticsQueries
from .serializers import (
    PeriodQuerySerializer,
    TopBeansQuerySerializer,
    TimeseriesQuerySerializer,
    UserConsumptionSerializer,
    GroupConsumptionSerializer,
    TopBeansResponseSerializer,
    TimeseriesResponseSerializer,
    TasteProfileSerializer,
    DashboardResponseSerializer,
)
from .permissions import IsGroupMemberForAnalytics
from .exceptions import InvalidMetricError
```

2. Refactor `user_consumption` view:

```python
# BEFORE - 52 lines with inline validation

# AFTER - ~20 lines
@extend_schema(...)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_consumption(request, user_id=None):
    """Get user's coffee consumption statistics."""
    # Use current user if no ID provided
    if user_id is None:
        user_id = request.user.id
    else:
        # Verify user exists
        get_object_or_404(User, id=user_id)

    # Validate query parameters
    query_serializer = PeriodQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    # Get consumption data
    data = AnalyticsQueries.user_consumption(
        user_id=user_id,
        start_date=params.get('start_date'),
        end_date=params.get('end_date')
    )

    return Response(data)
```

3. Refactor `group_consumption` view:

```python
# AFTER - Using permission class
@extend_schema(...)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
def group_consumption(request, group_id):
    """Get group's coffee consumption statistics."""
    # Verify group exists (permission class already checked membership)
    get_object_or_404(Group, id=group_id)

    # Validate query parameters
    query_serializer = PeriodQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    # Get consumption data (already formatted by service)
    data = AnalyticsQueries.group_consumption(
        group_id=group_id,
        start_date=params.get('start_date'),
        end_date=params.get('end_date')
    )

    return Response(data)
```

4. Refactor `top_beans` view:

```python
@extend_schema(...)
@api_view(['GET'])
def top_beans(request):
    """Get top-ranked coffee beans by various metrics."""
    # Validate query parameters
    query_serializer = TopBeansQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    try:
        # Get top beans (already formatted by service)
        data = AnalyticsQueries.top_beans(
            metric=params['metric'],
            period_days=params['period'],
            limit=params['limit']
        )
    except InvalidMetricError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'metric': params['metric'],
        'period_days': params['period'],
        'results': data
    })
```

5. Refactor `consumption_timeseries` view:

```python
@extend_schema(...)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
def consumption_timeseries(request):
    """Get consumption over time for charts."""
    # Validate query parameters
    query_serializer = TimeseriesQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    user_id = params.get('user_id', request.user.id)
    group_id = params.get('group_id')

    # Get timeseries data
    data = AnalyticsQueries.consumption_timeseries(
        user_id=user_id if not group_id else None,
        group_id=group_id,
        granularity=params['granularity']
    )

    # Format response
    formatted_data = [
        {
            'period': item['period'],
            'kg': float(item['kg']),
            'czk': float(item['czk']),
            'purchases_count': item['purchases_count']
        }
        for item in data
    ]

    return Response({
        'granularity': params['granularity'],
        'data': formatted_data
    })
```

6. Remove response serializer definitions from top of `views.py` (now in `serializers.py`)

### Verification

- [ ] All views use input serializers for validation
- [ ] `group_consumption` and `timeseries` use `IsGroupMemberForAnalytics`
- [ ] No date parsing logic in views
- [ ] Response serializers imported from `serializers.py`
- [ ] Views are < 25 lines each

---

## Phase 6: Update Tests

**Goal:** Add tests for new components

### Tasks

1. Create `apps/analytics/tests/test_serializers.py`:

```python
import pytest
from apps.analytics.serializers import (
    PeriodQuerySerializer,
    TopBeansQuerySerializer,
    TimeseriesQuerySerializer,
)


class TestPeriodQuerySerializer:
    def test_valid_period(self):
        serializer = PeriodQuerySerializer(data={'period': '2025-01'})
        assert serializer.is_valid()
        assert serializer.validated_data['start_date'].month == 1

    def test_invalid_period_format(self):
        serializer = PeriodQuerySerializer(data={'period': '2025-1'})
        assert not serializer.is_valid()
        assert 'period' in serializer.errors

    def test_invalid_period_month(self):
        serializer = PeriodQuerySerializer(data={'period': '2025-13'})
        assert not serializer.is_valid()

    def test_date_range_validation(self):
        serializer = PeriodQuerySerializer(data={
            'start_date': '2025-02-01',
            'end_date': '2025-01-01',  # Before start
        })
        assert not serializer.is_valid()


class TestTopBeansQuerySerializer:
    def test_valid_metric(self):
        serializer = TopBeansQuerySerializer(data={'metric': 'rating'})
        assert serializer.is_valid()

    def test_invalid_metric(self):
        serializer = TopBeansQuerySerializer(data={'metric': 'invalid'})
        assert not serializer.is_valid()

    def test_limit_bounds(self):
        serializer = TopBeansQuerySerializer(data={'limit': 200})
        assert not serializer.is_valid()  # Max 100
```

2. Create `apps/analytics/tests/test_permissions.py`:

```python
import pytest
from rest_framework.test import APIRequestFactory
from apps.analytics.permissions import IsGroupMemberForAnalytics


@pytest.mark.django_db
class TestIsGroupMemberForAnalytics:
    def test_no_group_id_allows_access(self, analytics_user):
        # Test logic...
        pass

    def test_member_allowed(self, analytics_user, analytics_group):
        # Test logic...
        pass

    def test_non_member_denied(self, analytics_outsider, analytics_group):
        # Test logic...
        pass
```

3. Update existing tests to verify new behavior

### Verification

- [ ] Serializer validation tests added
- [ ] Permission class tests added
- [ ] Existing tests still pass

---

## Phase 7: Documentation

**Goal:** Update app context documentation

### Tasks

1. Update `docs/app-context/analytics.md` to reflect:
   - New `serializers.py` file
   - New `permissions.py` file
   - New `exceptions.py` file
   - Updated service layer patterns
   - Optimized group_consumption query

2. Add "Refactoring Changes" section to app context

### Verification

- [ ] App context updated
- [ ] New files documented
- [ ] Architecture changes explained

---

## Summary Checklist

### Must Complete (Essential)

- [ ] Phase 1: Domain exceptions
- [ ] Phase 2: Input serializers
- [ ] Phase 3: Custom permission class
- [ ] Phase 4: Refactor services layer
- [ ] Phase 5: Refactor views

### Should Complete (Important)

- [ ] Phase 6: Update tests
- [ ] Phase 7: Documentation

### Final Verification

- [ ] All views are thin HTTP handlers (< 25 lines)
- [ ] No business logic in views
- [ ] Input validation via serializers
- [ ] Domain exceptions used
- [ ] Custom permission class for group membership
- [ ] No N+1 queries
- [ ] Services return plain dicts, not Django objects
- [ ] All existing tests pass
- [ ] New tests for serializers and permissions

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `apps/analytics/exceptions.py` | Domain-specific exceptions |
| `apps/analytics/serializers.py` | Input and response serializers |
| `apps/analytics/permissions.py` | Custom permission classes |
| `apps/analytics/tests/test_serializers.py` | Serializer tests |
| `apps/analytics/tests/test_permissions.py` | Permission tests |

### Modified Files

| File | Changes |
|------|---------|
| `apps/analytics/views.py` | Use serializers, permissions, remove formatting |
| `apps/analytics/analytics.py` | Return plain dicts, fix N+1, use exceptions |
| `apps/analytics/tests/test_api.py` | Update for new behavior |
| `docs/app-context/analytics.md` | Document new architecture |

---

## Success Metrics

### Before Refactoring

- Views with business logic: 6/7 (86%)
- Input serializers: 0
- Domain exceptions: 0
- Custom permission classes: 0
- N+1 queries: 1

### After Refactoring

- Views with business logic: 0%
- Input serializers: 3+
- Domain exceptions: 6+
- Custom permission classes: 1+
- N+1 queries: 0

---

## Notes

1. **No Transaction Safety Needed:** This is a read-only app with no state changes.

2. **No Concurrency Protection Needed:** No writes means no race conditions.

3. **Consider ViewSets:** For consistency with other apps, could migrate to class-based views with ViewSets in the future. Not essential for a read-only app with simple endpoints.

4. **Caching Opportunity:** After refactoring, consider adding Redis caching for expensive queries like `top_beans` and `group_consumption`.

---

Good luck with the refactoring! 🚀
