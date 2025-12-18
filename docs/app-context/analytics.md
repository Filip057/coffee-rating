# Analytics App - Application Context

> **Last Updated:** 2025-12-18
> **Owner:** Filip Prudek
> **Status:** Development - Recently Refactored (Phases 1-5)

---

## Purpose & Responsibility

Provides read-only analytics and statistics endpoints by aggregating data from purchases, reviews, and beans. Powers dashboards, charts, and insights without storing its own data.

**Core Responsibility:**
- User consumption statistics (kg, spending, purchases)
- Group consumption with member breakdown
- Top beans rankings by various metrics
- Consumption timeseries for charts
- User taste profile analysis from reviews
- Dashboard summary aggregation

**NOT Responsible For:**
- Storing any data (no models - queries other apps)
- Purchase creation (that's `purchases` app)
- Review creation (that's `reviews` app)
- User authentication (that's `accounts` app)

---

## Models

**This app has NO models.**

Analytics is a pure query/aggregation layer that reads from other apps:
- `purchases.PurchaseRecord` and `purchases.PaymentShare` for spending data
- `reviews.Review` and `reviews.Tag` for taste profile
- `beans.CoffeeBean` for top beans rankings
- `groups.Group` and `groups.GroupMembership` for group analytics

---

## Recent Refactoring (December 2025)

**Status:** Completed Phases 1-5 of DRF best practices refactoring

### Phase 1: Domain Exceptions (`exceptions.py`)

Created custom exception classes for analytics-specific errors:

```python
# apps/analytics/exceptions.py
class AnalyticsServiceError(Exception):
    """Base exception for analytics service errors."""

class InvalidPeriodError(AnalyticsServiceError):
    """Raised when period format is invalid."""

class InvalidDateRangeError(AnalyticsServiceError):
    """Raised when date range is invalid."""

class InvalidMetricError(AnalyticsServiceError):
    """Raised when metric type is invalid."""

class InvalidGranularityError(AnalyticsServiceError):
    """Raised when granularity type is invalid."""
```

**Purpose:** Provide domain-specific error types for better error handling and testing.

### Phase 2: Input Serializers (`serializers.py`)

Created input validation serializers to move validation logic out of views:

| Serializer | Purpose | Validates |
|------------|---------|-----------|
| `PeriodQuerySerializer` | Date range validation | `period` (YYYY-MM), `start_date`, `end_date` |
| `TopBeansQuerySerializer` | Top beans parameters | `metric`, `period` (1-365), `limit` (1-100) |
| `TimeseriesQuerySerializer` | Timeseries parameters | `user_id`, `group_id`, `granularity` |

**Example:**
```python
# Before: Manual validation in views
period = request.query_params.get('period')
if period:
    try:
        year, month = period.split('-')
        # ... 15 lines of date parsing logic
    except ValueError:
        return Response({'error': 'Invalid period'}, status=400)

# After: Serializer handles validation
query_serializer = PeriodQuerySerializer(data=request.query_params)
query_serializer.is_valid(raise_exception=True)
params = query_serializer.validated_data
```

**Benefits:**
- DRY: Reusable validation logic
- Testable: Serializers have their own test suite
- Clean views: Input validation separated from business logic

### Phase 3: Custom Permissions (`permissions.py`)

Created `IsGroupMemberForAnalytics` permission class:

```python
# apps/analytics/permissions.py
class IsGroupMemberForAnalytics(BasePermission):
    """
    Permission check for group analytics access.

    - Allows access if no group_id specified (user-level analytics)
    - Allows access if user is a member of the specified group
    - Denies access if user is not a member
    """

    def has_permission(self, request, view):
        group_id = view.kwargs.get('group_id') or request.query_params.get('group_id')

        if not group_id:
            return True  # No group = user-level request

        try:
            group = Group.objects.get(id=group_id)
            return group.has_member(request.user)
        except Group.DoesNotExist:
            return False
```

**Usage:**
```python
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsGroupMemberForAnalytics])
def group_consumption(request, group_id):
    # Permission already verified by IsGroupMemberForAnalytics
    ...
```

**Benefits:**
- Declarative: Permission logic at decorator level
- Reusable: Used by multiple endpoints
- DRF-compliant: Standard permission class pattern

### Phase 4: Service Layer Refactoring

Optimized `AnalyticsQueries` service methods to return plain dictionaries instead of Django model objects:

**Before:**
```python
# Service returned Django objects
return [{
    'bean': CoffeeBean,  # Django model
    'score': float,
}]

# View had to extract and format
for item in data:
    bean_data = {
        'id': str(item['bean'].id),
        'name': item['bean'].name,
        # ... manual extraction
    }
```

**After:**
```python
# Service returns plain dicts
return [{
    'bean_id': str(bean.id),
    'bean_name': bean.name,
    'roastery_name': bean.roastery_name,
    'score': float(score),
}]

# View just returns data directly
return Response({'results': data})
```

**Key Changes:**
- `top_beans()`: Returns plain dicts with `bean_id`, `bean_name`, etc.
- `user_consumption()`: Already returned dicts (no change needed)
- `group_consumption()`: Optimized with better query structure
- All methods: Better query optimization with `select_related`/`prefetch_related`

**Benefits:**
- Cleaner separation: Services don't leak Django models to views
- JSON-serializable: No need for manual conversion
- Testable: Services return pure Python data structures

### Phase 5: Thin HTTP Handler Views

Refactored all 6 views to be thin HTTP handlers (~15-25 lines each):

**Before (example from `top_beans` view - 50 lines):**
```python
def top_beans(request):
    # Manual parameter extraction
    metric = request.query_params.get('metric', 'rating')
    period_days = request.query_params.get('period', 30)

    # Manual validation
    try:
        period_days = int(period_days)
        limit = int(limit)
    except ValueError:
        return Response({'error': 'Invalid'}, status=400)

    # Service call
    data = AnalyticsQueries.top_beans(...)

    # Manual response formatting (20+ lines)
    results = []
    for item in data:
        bean_data = {
            'id': str(item['bean'].id),
            # ... 15 more lines
        }
    return Response(results)
```

**After (24 lines):**
```python
def top_beans(request):
    """Get top-ranked coffee beans - thin HTTP handler."""
    # Validate using input serializer
    query_serializer = TopBeansQuerySerializer(data=request.query_params)
    query_serializer.is_valid(raise_exception=True)
    params = query_serializer.validated_data

    try:
        # Get data from service (already returns plain dicts)
        data = AnalyticsQueries.top_beans(
            metric=params.get('metric'),
            period_days=params.get('period'),
            limit=params.get('limit')
        )
    except InvalidMetricError as e:
        return Response({'error': str(e)}, status=400)

    return Response({
        'metric': params.get('metric'),
        'period_days': params.get('period'),
        'results': data
    })
```

**Views Refactored:**
1. `user_consumption`: 38 → 23 lines (39% reduction)
2. `group_consumption`: 34 → 18 lines (47% reduction)
3. `top_beans`: 50 → 24 lines (52% reduction)
4. `consumption_timeseries`: 36 → 27 lines (25% reduction)
5. `taste_profile`: Improved for consistency
6. `dashboard`: 30 → 25 lines (17% reduction)

**Total Impact:** views.py reduced from 313 to 243 lines (22% reduction)

### Phase 6: Test Suite

Added comprehensive test coverage for new components:

| Test File | Purpose | Test Count |
|-----------|---------|------------|
| `test_serializers.py` | Input serializer validation | 40+ tests |
| `test_permissions.py` | Permission class logic | 10+ tests |
| `test_api.py` | Endpoint integration tests | 70+ tests (existing) |

**Test Coverage:**
- All serializer validation edge cases
- Permission logic for group membership
- Date parsing and validation
- Parameter bounds checking
- UUID validation

### Architecture After Refactoring

```
apps/analytics/
├── exceptions.py          # Domain exceptions (Phase 1)
├── serializers.py         # Input + Response serializers (Phase 2)
├── permissions.py         # Custom permission classes (Phase 3)
├── analytics.py          # Service layer (optimized in Phase 4)
├── views.py              # Thin HTTP handlers (refactored in Phase 5)
├── tests/
│   ├── conftest.py       # Test fixtures
│   ├── test_api.py       # Integration tests
│   ├── test_serializers.py   # New: Serializer tests (Phase 6)
│   └── test_permissions.py   # New: Permission tests (Phase 6)
```

**Key Principles:**
- **Separation of Concerns:** Input validation (serializers) → Business logic (services) → HTTP handling (views)
- **DRF Best Practices:** Permission classes, serializers, exception handling
- **Thin Views:** Views are ~15-25 lines, delegating to services and serializers
- **Plain Dicts:** Services return JSON-serializable data structures
- **Domain Exceptions:** Specific error types for better error handling

---

## API Endpoints

### User Analytics

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/analytics/user/consumption/` | Current user's consumption | Required | IsAuthenticated |
| GET | `/api/analytics/user/{id}/consumption/` | Specific user's consumption | Required | IsAuthenticated |
| GET | `/api/analytics/user/taste-profile/` | Current user's taste profile | Required | IsAuthenticated |
| GET | `/api/analytics/user/{id}/taste-profile/` | Specific user's taste profile | Required | IsAuthenticated |

### Group Analytics

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/analytics/group/{id}/consumption/` | Group consumption with breakdown | Required | IsGroupMember |

### Bean Analytics

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/analytics/beans/top/` | Top beans by various metrics | Optional | Public |

### Charts & Dashboard

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/analytics/timeseries/` | Consumption over time | Required | IsAuthenticated |
| GET | `/api/analytics/dashboard/` | Dashboard summary | Required | IsAuthenticated |

---

## Query Parameters

### User Consumption
| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Month period (YYYY-MM) |
| `start_date` | date | Start date (YYYY-MM-DD) |
| `end_date` | date | End date (YYYY-MM-DD) |

### Group Consumption
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | date | Start date (YYYY-MM-DD) |
| `end_date` | date | End date (YYYY-MM-DD) |

### Top Beans
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `metric` | string | rating, kg, money, reviews | rating |
| `period` | int | Number of days to consider | 30 |
| `limit` | int | Number of results | 10 |

### Timeseries
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | UUID | User ID (defaults to current) |
| `group_id` | UUID | Group ID for group data |
| `granularity` | string | day, week, month | month |

---

## Business Logic & Workflows

### **AnalyticsQueries Service**

Central service class containing all analytics query methods.

### **Query 1: User Consumption**

**Purpose:** Calculate user's coffee consumption and spending.

**Algorithm:**
1. Get user's paid PaymentShares
2. Apply date filters
3. Sum spending from shares
4. Calculate weight: `(share_amount / purchase_total) * package_weight`
5. Calculate avg price per kg

**Returns:**
```python
{
    'total_kg': Decimal,      # Total weight consumed
    'total_spent_czk': Decimal,  # Total money spent
    'purchases_count': int,   # Number of purchases
    'avg_price_per_kg': Decimal,  # Average price
    'period_start': date,
    'period_end': date,
}
```

**Code:**
```python
def user_consumption(user_id, start_date=None, end_date=None):
    shares = PaymentShare.objects.filter(
        user_id=user_id,
        status=PaymentStatus.PAID
    )

    for share in shares:
        purchase = share.purchase
        if purchase.package_weight_grams:
            share_ratio = share.amount_czk / purchase.total_price_czk
            user_grams = Decimal(purchase.package_weight_grams) * share_ratio
            total_grams += user_grams
```

### **Query 2: Group Consumption**

**Purpose:** Calculate group's total consumption with per-member breakdown.

**Algorithm:**
1. Get group purchases
2. Apply date filters
3. Sum totals
4. For each member, call `user_consumption()`
5. Calculate share percentages

**Returns:**
```python
{
    'total_kg': Decimal,
    'total_spent_czk': Decimal,
    'purchases_count': int,
    'member_breakdown': [
        {
            'user': User,
            'total_kg': Decimal,
            'total_spent_czk': Decimal,
            'share_percentage': float,
        }
    ],
}
```

### **Query 3: Top Beans**

**Purpose:** Rank beans by various metrics.

**Metrics:**
| Metric | How Ranked | Min Requirement |
|--------|------------|-----------------|
| `rating` | avg_rating descending | 3+ reviews |
| `kg` | total weight purchased | Any purchase |
| `money` | total CZK spent | Any purchase |
| `reviews` | review_count descending | 1+ review |

**Returns:**
```python
[
    {
        'bean': CoffeeBean,
        'score': float,
        'metric': str,
        # Plus metric-specific fields
    }
]
```

### **Query 4: Consumption Timeseries**

**Purpose:** Get consumption data over time for charts.

**Algorithm:**
1. Group shares/purchases by month
2. Sum kg, czk, count for each period
3. Return sorted list

**Returns:**
```python
[
    {
        'period': '2025-01',
        'kg': Decimal,
        'czk': Decimal,
        'purchases_count': int,
    }
]
```

### **Query 5: User Taste Profile**

**Purpose:** Analyze user's taste preferences from reviews.

**Algorithm:**
1. Get all user's reviews with tags
2. Count tag occurrences
3. Count roast profile occurrences
4. Count origin occurrences
5. Calculate average rating

**Returns:**
```python
{
    'favorite_tags': [{'tag': str, 'count': int}],
    'avg_rating': float,
    'preferred_roast': str,
    'preferred_origin': str,
    'review_count': int,
}
```

---

## Permissions & Security

**Permission Classes:**
- `IsAuthenticated` - Most analytics endpoints (DRF built-in)
- `IsGroupMemberForAnalytics` - Custom class for group analytics (Phase 3)
- Public access - `top_beans` endpoint only

**Custom Permission Class:**
```python
# apps/analytics/permissions.py
class IsGroupMemberForAnalytics(BasePermission):
    """
    Checks group membership for analytics endpoints.
    Handles both URL kwargs and query parameters.
    """
    # Used by: group_consumption, consumption_timeseries
```

**Access Rules:**
| Endpoint | Who Can Access | Permission Classes |
|----------|----------------|-------------------|
| User consumption | Any authenticated user | `IsAuthenticated` |
| Group consumption | Group members only | `IsAuthenticated, IsGroupMemberForAnalytics` |
| Top beans | Everyone (public) | None |
| Timeseries | Authenticated (own) or group members | `IsAuthenticated, IsGroupMemberForAnalytics` |
| Taste profile | Any authenticated user | `IsAuthenticated` |
| Dashboard | Authenticated users (own data) | `IsAuthenticated` |

**Security Considerations:**
- `IsGroupMemberForAnalytics` permission class enforces membership before data access
- Permission class handles both URL kwargs (`group_id` in path) and query parameters
- User can view any other user's consumption (public stats by design)
- No PII exposed in analytics responses
- Custom exceptions provide clean error messages without leaking internal details

---

## Testing Strategy

**Test Files:**
1. `test_serializers.py` - Input serializer validation (40+ tests)
2. `test_permissions.py` - Permission class logic (10+ tests)
3. `test_api.py` - Endpoint integration tests (70+ tests)

**What to Test:**
1. **Serializer validation** - Input parameter bounds, formats, edge cases
2. **Permission enforcement** - Group membership, access control
3. **Consumption calculations** - Accuracy of kg, CZK, counts
4. **Date filtering** - Period parsing, date ranges
5. **Group member breakdown** - Share calculations
6. **Top beans ranking** - Each metric (rating, kg, money, reviews)
7. **Timeseries generation** - Monthly aggregation
8. **Taste profile analysis** - Tag counting, preferences

**Test Coverage:** 120+ test cases across 3 test files

**Critical Test Cases:**
```python
def test_user_consumption_calculation(self, analytics_user, analytics_personal_purchase):
    """Test basic consumption calculation."""
    result = AnalyticsQueries.user_consumption(analytics_user.id)

    assert result['total_spent_czk'] == Decimal('500.00')
    assert result['total_kg'] == Decimal('0.500')  # 500g

def test_group_consumption_equal_shares(self, analytics_group, analytics_group_purchase):
    """Test equal share distribution."""
    result = AnalyticsQueries.group_consumption(analytics_group.id)

    for member in result['member_breakdown']:
        if member['total_spent_czk'] > 0:
            assert member['total_spent_czk'] == Decimal('300.00')

def test_taste_profile_tag_ranking(self, analytics_user, analytics_reviews):
    """Test tag ranking is correct."""
    result = AnalyticsQueries.user_taste_profile(analytics_user.id)

    assert result['favorite_tags'][0]['tag'] == 'fruity'
    assert result['favorite_tags'][0]['count'] == 2
```

---

## Dependencies & Relationships

**This App Uses:**
- `accounts.User` - For user identification
- `purchases.PurchaseRecord` - For spending data
- `purchases.PaymentShare` - For individual consumption
- `purchases.PaymentStatus` - To filter paid shares
- `reviews.Review` - For taste profile
- `reviews.Tag` - For tag analysis
- `beans.CoffeeBean` - For top beans
- `groups.Group` - For group analytics
- `groups.GroupMembership` - For member breakdown

**Used By:**
- Frontend dashboards and charts
- No other apps depend on this

**External Services:**
- None

---

## Common Patterns

**Pattern 1: Weight Share Calculation**
```python
# User's weight share = (payment / total_price) * package_weight
share_ratio = share.amount_czk / purchase.total_price_czk
user_grams = Decimal(purchase.package_weight_grams) * share_ratio
```

**When to Use:** Calculating individual consumption from group purchases

**Pattern 2: Period-Based Aggregation**
```python
# Parse YYYY-MM period to date range
year, month = period.split('-')
start_date = datetime(int(year), int(month), 1).date()
if int(month) == 12:
    end_date = datetime(int(year) + 1, 1, 1).date() - timedelta(days=1)
else:
    end_date = datetime(int(year), int(month) + 1, 1).date() - timedelta(days=1)
```

**When to Use:** Monthly consumption queries

**Pattern 3: Dictionary-Based Aggregation**
```python
shares_by_month = {}
for share in shares:
    month_key = share.purchase.date.strftime('%Y-%m')
    if month_key not in shares_by_month:
        shares_by_month[month_key] = {'czk': Decimal('0'), 'grams': Decimal('0')}
    shares_by_month[month_key]['czk'] += share.amount_czk
```

**When to Use:** Timeseries generation without heavy SQL grouping

---

## Gotchas & Known Issues

**Issue 1: N+1 Queries in Group Breakdown**
- **Symptom:** Slow group consumption for large groups
- **Cause:** Calls `user_consumption()` for each member
- **Workaround:** Acceptable for small groups
- **Status:** TODO - Optimize with single aggregation query

**Issue 2: Missing Package Weight**
- **Symptom:** Weight shows 0 even with purchases
- **Cause:** `package_weight_grams` is optional
- **Workaround:** Only count purchases with weight
- **Status:** By design

**Issue 3: Top Beans Rating Minimum**
- **Symptom:** New beans don't appear in "top by rating"
- **Cause:** Requires 3+ reviews to be included
- **Workaround:** None - prevents gaming with single 5-star review
- **Status:** By design

---

## Future Enhancements

**Planned:**
- [ ] Caching for expensive queries (Redis)
- [ ] Export analytics to CSV/PDF
- [ ] Comparison between periods
- [ ] Group leaderboards

**Ideas:**
- [ ] ML-based taste recommendations
- [ ] Price trend analysis
- [ ] Spending predictions
- [ ] Anomaly detection (unusual spending)

**Won't Do (and Why):**
- Real-time analytics - Overkill for coffee tracking
- Complex BI dashboards - Use external tools

---

## Related Documentation

- [API Reference](../API.md#analytics-endpoints)
- [Database Schema](../DATABASE.md)
- Other App Contexts: [purchases](./purchases.md), [reviews](./reviews.md), [beans](./beans.md)

---

## Notes for Developers

> **Why No Models?**
> Analytics is a pure query layer. Storing aggregated data would create consistency issues when source data changes. Real-time calculation ensures accuracy.

> **Why Calculate Weight from Share Ratio?**
> In group purchases, weight is shared proportionally to payment. If 3 people split 1kg equally, each consumed 333g regardless of the total price.

> **Why 3-Review Minimum for Rating Ranking?**
> Prevents a single 5-star review from dominating the leaderboard. Statistical significance requires multiple data points.

---

## AI Assistant Context

**When modifying this app, ALWAYS remember:**

1. **NEVER add models to this app**
   - Analytics should remain a pure query layer
   - All data comes from other apps

2. **ALWAYS use Decimal for monetary calculations**
   - Never use float for CZK amounts
   - Round appropriately for display

3. **ALWAYS use input serializers for query parameter validation**
   - Create serializers in `serializers.py` (Phase 2 pattern)
   - Use `.is_valid(raise_exception=True)` in views
   - Don't do manual validation in views

4. **ALWAYS use permission classes for access control**
   - Use `IsGroupMemberForAnalytics` for group endpoints
   - Don't do inline permission checks in views
   - Permission classes should be declarative at the decorator level

5. **ALWAYS return plain dicts from service methods**
   - Services should return JSON-serializable data
   - Don't return Django model objects from services
   - Convert models to dicts in the service layer

6. **ALWAYS keep views thin (< 25 lines)**
   - Views should only handle HTTP concerns
   - Delegate validation to serializers
   - Delegate business logic to services
   - Delegate permissions to permission classes

7. **ALWAYS use domain exceptions**
   - Raise specific exceptions from `exceptions.py`
   - Don't return generic ValueError or TypeError
   - Handle exceptions in views appropriately

8. **ALWAYS handle missing data gracefully**
   - Users with no purchases should get zeros
   - Users with no reviews should get appropriate message
   - Never raise exceptions for empty data

9. **ALWAYS consider performance**
   - Use `select_related` and `prefetch_related`
   - Avoid N+1 queries where possible
   - Consider caching for expensive operations

**Typical Prompts:**

```
"Add spending comparison between months"
-> Consider:
1. Add endpoint with two period parameters
2. Calculate consumption for each period
3. Return difference and percentage change
4. Handle missing data for one period

"Optimize group consumption query"
-> Solution:
Use single aggregation query instead of per-member calls:
PaymentShare.objects.filter(
    purchase__group_id=group_id,
    status=PaymentStatus.PAID
).values('user_id').annotate(
    total_czk=Sum('amount_czk'),
    total_grams=Sum(...)  # Complex calculation
)

"Add caching for top beans"
-> Steps:
1. Add Django cache framework or Redis
2. Cache key: f"top_beans:{metric}:{period}:{limit}"
3. Cache timeout: 5-15 minutes
4. Invalidate on new review/purchase (via signals)
```

---

## Response Serializers Reference

The app defines response serializers for API documentation:

| Serializer | Used By | Fields |
|------------|---------|--------|
| `UserConsumptionSerializer` | user_consumption | total_kg, total_czk, purchases_count, unique_beans, avg_price_per_kg |
| `GroupConsumptionSerializer` | group_consumption | total_kg, total_czk, purchases_count, unique_beans, member_breakdown |
| `TopBeansResponseSerializer` | top_beans | metric, period_days, results |
| `TimeseriesResponseSerializer` | consumption_timeseries | granularity, data |
| `TasteProfileSerializer` | taste_profile | review_count, avg_rating, favorite_origins, favorite_roast_profiles, common_tags, brew_methods |
| `DashboardResponseSerializer` | dashboard | consumption, taste_profile, top_beans |
