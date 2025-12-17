# Analytics App - DRF Best Practices Analysis

> **Created:** 2025-12-17
> **App:** `apps/analytics`
> **Reference:** [DRF_best_practices.md](../DRF_best_practices.md)
> **App Context:** [app-context/analytics.md](./app-context/analytics.md)

---

## Executive Summary

The analytics app is a **read-only query layer** with no models. It aggregates data from other apps (purchases, reviews, beans) to provide statistics and insights. This unique nature means some DRF patterns (transactions, concurrency) don't apply.

| Category | Current Score | Notes |
|----------|--------------|-------|
| **Views (Thin HTTP Layer)** | 60% | Views contain formatting logic |
| **Services (Business Logic)** | 85% | `AnalyticsQueries` class exists, well-documented |
| **Serializers (Validation)** | 40% | Response serializers exist, no input validation |
| **Error Handling** | 30% | No domain exceptions, inline HTTP errors |
| **Permissions** | 70% | Works, but inline checks |
| **Transaction Safety** | N/A | Read-only app |
| **Concurrency** | N/A | Read-only app |
| **Testing** | 90% | Excellent test coverage |

**Overall Score: 65%** (adjusted for read-only nature)

---

## Detailed Analysis

### 1. Core Architecture (✅ Mostly Good)

```
Current Architecture:
Views (views.py) → AnalyticsQueries (analytics.py) → Other Apps' Models
     ↓                      ↓
Response Serializers    Pure SQL Aggregations
```

**What's Good:**
- Clear separation between HTTP handling and query logic
- `AnalyticsQueries` acts as a service layer with static methods
- No models (correct for aggregation layer)
- Methods use `select_related` and `prefetch_related`

**Issues Found:**
- Views contain response formatting logic (should be in serializers)
- Input validation in views (should be in input serializers)
- No domain exceptions (uses HTTP responses inline)

---

### 2. Views Layer Analysis

**File:** `apps/analytics/views.py` (386 lines)

#### Issue 1: Views Contain Response Formatting (Lines 242-268, 373-385)

```python
# CURRENT - Business logic in views
@api_view(['GET'])
def top_beans(request):
    data = AnalyticsQueries.top_beans(...)

    # THIS SHOULD BE IN A SERIALIZER
    results = []
    for item in data:
        bean_data = {
            'id': str(item['bean'].id),
            'name': item['bean'].name,
            'roastery_name': item['bean'].roastery_name,
            'score': item['score'],
            'metric': item.get('metric', metric),
        }
        # ... more formatting
        results.append(bean_data)

    return Response({...})
```

**Best Practice Violation:** Views should only handle HTTP concerns, not transform data.

#### Issue 2: Input Validation in Views (Lines 125-143)

```python
# CURRENT - Date parsing in view
if period:
    try:
        year, month = period.split('-')
        start_date = datetime(int(year), int(month), 1).date()
        # ... complex date calculation
    except (ValueError, AttributeError):
        return Response({'error': 'Invalid period format...'}, status=400)
```

**Best Practice Violation:** Input validation should be in serializers.

#### Issue 3: Inline Permission Checks (Lines 172-178, 293-299)

```python
# CURRENT - Inline permission check
if not group.has_member(request.user):
    return Response(
        {'error': 'You must be a member of this group'},
        status=status.HTTP_403_FORBIDDEN
    )
```

**Best Practice Violation:** Should use custom permission class.

#### Issue 4: Function-Based Views

Using `@api_view` decorators instead of class-based views. While not strictly wrong for simple endpoints, it limits reusability of permissions and serializers.

---

### 3. Services Layer Analysis

**File:** `apps/analytics/analytics.py` (616 lines)

#### What's Good:

1. **Separation:** All query logic is in `AnalyticsQueries` class
2. **Documentation:** Excellent docstrings on all methods
3. **Optimization:** Uses `select_related`, `prefetch_related`
4. **Type hints:** Present throughout
5. **Static methods:** Appropriate for stateless queries

#### Issue 1: Returns Django Objects (Lines 315-323)

```python
# CURRENT - Returns CoffeeBean objects
return [
    {
        'bean': bean,  # Django model object
        'score': float(bean.avg_rating),
        ...
    }
    for bean in beans
]
```

**Problem:** Service returns Django objects, requiring views to serialize them.

**Best Practice:** Services should return plain dictionaries or data classes.

#### Issue 2: No Domain Exceptions (Line 399)

```python
# CURRENT - Raises ValueError
else:
    raise ValueError(f"Invalid metric: {metric}")
```

**Best Practice:** Should raise domain-specific exception like `InvalidMetricError`.

#### Issue 3: N+1 Query in group_consumption (Lines 226-245)

```python
# CURRENT - Calls user_consumption for each member
for membership in memberships:
    user_data = AnalyticsQueries.user_consumption(
        membership.user_id,
        start_date,
        end_date
    )
```

This is documented as a known issue but should be fixed.

---

### 4. Serializers Analysis

**File:** `apps/analytics/views.py` (Lines 15-97)

#### What's Good:

- Response serializers exist for API documentation
- Cover all response types

#### What's Missing:

1. **No Input Serializers:** Query parameters validated manually in views
2. **No Output Serializers Used:** Views format responses manually

**Example of Missing Input Serializer:**

```python
# SHOULD EXIST but doesn't
class UserConsumptionQuerySerializer(serializers.Serializer):
    period = serializers.RegexField(
        regex=r'^\d{4}-\d{2}$',
        required=False,
        help_text='Month period (YYYY-MM)'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        # Validation logic here
        return attrs
```

---

### 5. Error Handling Analysis

#### Current State:

- No domain exceptions defined
- HTTP errors returned inline from views
- `ValueError` raised for invalid metric (caught nowhere)

**Current Error Handling:**
```python
# views.py - Inline HTTP error
return Response(
    {'error': 'Invalid period format. Use YYYY-MM'},
    status=status.HTTP_400_BAD_REQUEST
)
```

**Best Practice:**
```python
# Domain exception in exceptions.py
class AnalyticsServiceError(Exception):
    pass

class InvalidPeriodError(AnalyticsServiceError):
    pass

# Service raises domain exception
raise InvalidPeriodError("Invalid period format. Use YYYY-MM")

# View catches and maps to HTTP
except InvalidPeriodError as e:
    return Response({'error': str(e)}, status=400)
```

---

### 6. Permissions Analysis

#### Current State:

- Uses `@permission_classes([IsAuthenticated])` correctly
- Inline group membership checks

#### Issue: No Custom Permission Class for Group Membership

```python
# SHOULD EXIST
class IsGroupMember(BasePermission):
    """Permission check for group analytics access."""

    def has_permission(self, request, view):
        group_id = view.kwargs.get('group_id') or request.query_params.get('group_id')
        if not group_id:
            return True  # No group specified

        try:
            group = Group.objects.get(id=group_id)
            return group.has_member(request.user)
        except Group.DoesNotExist:
            return False
```

---

### 7. Testing Analysis

**Files:** `apps/analytics/tests/test_api.py`, `apps/analytics/tests/conftest.py`

#### What's Good:

- 70+ test cases covering all endpoints
- Service-level tests (`TestAnalyticsQueriesUserConsumption`, etc.)
- Edge cases tested (no data, invalid parameters)
- Permission tests (unauthenticated, non-member)

#### What's Missing:

- No tests for custom permission classes (they don't exist yet)
- No performance tests for N+1 queries
- Could add more edge cases for date filtering

---

## Issues Summary

| Issue | Severity | Location | Best Practice Violation |
|-------|----------|----------|------------------------|
| Response formatting in views | Medium | `views.py:242-268, 373-385` | Views should be thin |
| Input validation in views | Medium | `views.py:125-143` | Use input serializers |
| Inline permission checks | Low | `views.py:172-178, 293-299` | Use permission classes |
| No domain exceptions | Medium | `analytics.py` | Domain exceptions required |
| Service returns Django objects | Medium | `analytics.py:315-323` | Return plain dicts |
| N+1 query in group_consumption | Medium | `analytics.py:226-245` | Optimize queries |
| No input serializers | Medium | N/A | Missing entirely |
| Function-based views | Low | `views.py` | Consider ViewSets |

---

## What Doesn't Need Changing

Since this is a read-only app:

1. **Transaction management:** Not needed (no writes)
2. **Concurrency protection:** Not needed (no state changes)
3. **`select_for_update()`:** Not applicable
4. **Model business logic:** No models exist (correct)

---

## Metrics

### Current State

| Metric | Value | Target |
|--------|-------|--------|
| Views with business logic | 6/7 (86%) | 0% |
| Input serializers | 0 | 4+ |
| Domain exceptions | 0 | 5+ |
| Custom permission classes | 0 | 1+ |
| Service test coverage | ~90% | 90%+ |
| N+1 queries | 1 | 0 |

### After Refactoring (Target)

| Metric | Value |
|--------|-------|
| Views with business logic | 0% |
| Input serializers | 4+ |
| Domain exceptions | 5+ |
| Custom permission classes | 1 |
| N+1 queries | 0 |
