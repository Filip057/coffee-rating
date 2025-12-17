# Beans App DRF Best Practices Analysis

**Date:** 2025-12-16
**Status:** Analysis Complete - Refactoring Recommended

---

## Executive Summary

The beans app has **partial** adherence to DRF best practices. While it includes a `services.py` file with deduplication logic, it requires significant refactoring to match the quality and architecture of the recently refactored accounts app.

**Recommendation:** ✅ **REFACTOR REQUIRED**

**Priority:** Medium (not urgent, but will improve maintainability and safety)

---

## Comparison: Accounts App vs Beans App

| Aspect | Accounts App (✅ Refactored) | Beans App (⚠️ Current State) |
|--------|------------------------------|------------------------------|
| **Service Layer** | Modular services/ directory with separate files | Single services.py file with static class methods |
| **Transaction Safety** | All mutations wrapped in @transaction.atomic | Only merge_beans() has transaction wrapper |
| **Concurrency Protection** | select_for_update() on critical operations | Only used in merge_beans() |
| **Domain Exceptions** | Complete exception hierarchy | Uses generic ValueError |
| **Business Logic Location** | 100% in services layer | Mixed: views (filtering), models (save), services (dedup) |
| **View Complexity** | Thin views, HTTP-only concerns | Fat views with filtering logic |
| **Model Methods** | No business logic | Has update_aggregate_rating() method |
| **Testability** | Services can be unit tested | Tightly coupled to Django ORM |

---

## Detailed Analysis

### ✅ Strengths

1. **Existing Services File**
   - Has `CoffeeBeanDeduplicationService` class
   - Implements fuzzy matching for duplicates
   - Has bean merging logic with @transaction.atomic

2. **ViewSets Implementation**
   - Uses DRF ViewSets (good REST practice)
   - Has proper pagination
   - Multiple serializers for different actions

3. **Data Model**
   - Good use of normalized fields for search
   - Soft delete pattern implemented
   - Proper indexes and unique constraints

4. **Serializers**
   - Clean, no business logic
   - Proper read_only_fields
   - Good separation (list, create, detail)

---

### ❌ Issues Requiring Refactoring

#### 1. **Service Layer Architecture** (High Priority)

**Current State:**
```python
# apps/beans/services.py (300 lines, single file)
class CoffeeBeanDeduplicationService:
    @staticmethod
    def normalize_text(text): ...

    @staticmethod
    def find_potential_duplicates(...): ...

    @staticmethod
    def merge_beans(...): ...
```

**Issues:**
- Static methods instead of functions (not Pythonic)
- Single monolithic file (violates Single Responsibility)
- Only handles deduplication (CRUD logic still in views)

**Should Be:**
```python
# apps/beans/services/
├── bean_management.py        # create_bean(), update_bean()
├── bean_search.py            # search_beans()
├── bean_deduplication.py     # find_potential_duplicates()
├── bean_merging.py           # merge_beans()
├── variant_management.py     # create_variant()
├── rating_aggregation.py     # update_bean_rating()
└── exceptions.py             # Domain exceptions
```

---

#### 2. **Business Logic in Views** (High Priority)

**Current State:**
```python
# apps/beans/views.py - CoffeeBeanViewSet
def get_queryset(self):
    queryset = super().get_queryset()

    search = self.request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(roastery_name__icontains=search) |
            # ... more filtering logic (30+ lines)
        )

    roastery = self.request.query_params.get('roastery')
    if roastery:
        queryset = queryset.filter(roastery_name__icontains=roastery)

    # ... 5 more filters

    return queryset.distinct()
```

**Issues:**
- Complex filtering logic in view (should be service)
- Hard to test independently
- Mixed HTTP and business concerns

**Should Be:**
```python
# apps/beans/views.py
from .services import search_beans

def get_queryset(self):
    return search_beans(
        search=self.request.query_params.get('search'),
        roastery=self.request.query_params.get('roastery'),
        origin=self.request.query_params.get('origin'),
        roast_profile=self.request.query_params.get('roast_profile'),
        processing=self.request.query_params.get('processing'),
        min_rating=self.request.query_params.get('min_rating'),
    )
```

---

#### 3. **Business Logic in Models** (Medium Priority)

**Current State:**
```python
# apps/beans/models.py - CoffeeBean
def update_aggregate_rating(self):
    """Business logic in model method."""
    from django.db.models import Avg, Count
    aggregates = self.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    self.avg_rating = aggregates['avg'] or Decimal('0.00')
    self.review_count = aggregates['count']
    self.save(update_fields=['avg_rating', 'review_count', 'updated_at'])
```

**Issues:**
- Business logic on model (should be service)
- No transaction wrapper
- No select_for_update() (race condition risk)
- Called from reviews app (cross-app coupling)

**Should Be:**
```python
# apps/beans/services/rating_aggregation.py
@transaction.atomic
def update_bean_rating(*, bean_id: UUID) -> CoffeeBean:
    bean = CoffeeBean.objects.select_for_update().get(id=bean_id)

    aggregates = bean.reviews.aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    bean.avg_rating = aggregates['avg'] or Decimal('0.00')
    bean.review_count = aggregates['count']
    bean.save(update_fields=['avg_rating', 'review_count', 'updated_at'])

    return bean
```

---

#### 4. **Missing Transaction Safety** (High Priority)

**Operations Without Transaction Protection:**

| Operation | Risk | Current State |
|-----------|------|---------------|
| Bean creation | Medium | No @transaction.atomic |
| Bean update | Medium | No @transaction.atomic |
| Variant creation | Medium | No @transaction.atomic |
| Rating update | **HIGH** | **Race condition possible** |
| Soft delete | Low | No transaction needed |

**Critical Issue: Rating Updates**

When multiple reviews are created simultaneously:
```python
# Thread 1: Creates review, triggers rating update
bean.avg_rating = 4.5  # Reads current reviews

# Thread 2: Creates review, triggers rating update
bean.avg_rating = 4.3  # Reads current reviews (race!)

# Thread 1: Saves
bean.save()  # avg_rating = 4.5

# Thread 2: Saves
bean.save()  # avg_rating = 4.3 (WRONG - overwrites Thread 1)
```

**Solution:**
```python
@transaction.atomic
def update_bean_rating(*, bean_id: UUID):
    bean = CoffeeBean.objects.select_for_update().get(id=bean_id)
    # Now locked - no race condition
    # ... update rating
```

---

#### 5. **Missing Critical Model** (Critical Bug)

**Current State:**
```python
# apps/beans/services.py line 226
MergeHistory.objects.create(
    merged_from=source.id,
    merged_into=target,
    merged_by=merged_by_user,
    reason=reason
)
```

**Issue:** `MergeHistory` model **DOES NOT EXIST** in `models.py`

**Impact:**
- ❌ `merge_beans()` will fail with `NameError`
- ❌ No audit trail of merges
- ❌ Cannot track who merged what

**Must Fix:** Create `MergeHistory` model

---

#### 6. **No Domain Exceptions** (Medium Priority)

**Current State:**
```python
# apps/beans/services.py line 166
if source.id == target.id:
    raise ValueError("Cannot merge bean with itself")  # ❌ Generic exception
```

**Issues:**
- Uses generic `ValueError`
- Cannot catch domain-specific errors
- Poor error handling in views

**Should Be:**
```python
# apps/beans/services/exceptions.py
class InvalidMergeError(BeansServiceError):
    """Raised when merge parameters are invalid."""
    pass

# apps/beans/services/bean_merging.py
if source.id == target.id:
    raise InvalidMergeError("Cannot merge bean with itself")

# apps/beans/views.py
try:
    merge_beans(...)
except InvalidMergeError as e:
    return Response({'error': str(e)}, status=400)
```

---

## Refactoring Impact Assessment

### Code Changes Required

| Component | Files Changed | Estimated LOC | Risk |
|-----------|---------------|---------------|------|
| Create services/ directory | +8 files | +600 | Low |
| Update views.py | 1 file | ~150 | Low |
| Create MergeHistory model | 1 file + migration | ~30 | Medium |
| Update models.py | 1 file | -15 | Low |
| Delete old services.py | -1 file | -300 | Low |
| Update tests | Multiple | ~200 | Medium |
| Update documentation | 1 file | +100 | Low |

**Total:** ~10-12 files, ~800 LOC changes

---

### Breaking Changes

✅ **NO BREAKING CHANGES** - All changes are internal

- Public API endpoints remain unchanged
- Serializers remain unchanged
- Database schema changes only add MergeHistory table
- Existing functionality preserved

---

### Benefits

**Immediate:**
1. ✅ Fixed critical bug (MergeHistory model missing)
2. ✅ Eliminated race conditions in rating updates
3. ✅ Better error messages with domain exceptions

**Long-term:**
1. ✅ Easier to test (unit test services independently)
2. ✅ Easier to maintain (clear separation of concerns)
3. ✅ Easier to extend (add features in services)
4. ✅ Consistent architecture across apps
5. ✅ Safer concurrent operations

---

## Recommendations

### Phase 1: Critical Fixes (Must Do)

1. **Create MergeHistory model** - Fixes production bug
2. **Add transaction safety to rating updates** - Prevents race conditions
3. **Add concurrency protection to merges** - Already has @transaction.atomic, add select_for_update()

**Estimated Time:** 2-3 hours
**Priority:** HIGH

---

### Phase 2: Service Layer Refactoring (Should Do)

1. **Restructure services into modules** - Better organization
2. **Move view logic to services** - Separation of concerns
3. **Create domain exceptions** - Better error handling
4. **Update views to use services** - Thin views

**Estimated Time:** 4-6 hours
**Priority:** MEDIUM

---

### Phase 3: Testing & Documentation (Should Do)

1. **Create service unit tests** - Improve coverage
2. **Update integration tests** - Test new services
3. **Update documentation** - Document architecture

**Estimated Time:** 2-3 hours
**Priority:** MEDIUM

---

## Implementation Plan

See detailed checklist: [`REFACTORING_BEANS_CHECKLIST.md`](./REFACTORING_BEANS_CHECKLIST.md)

**Total Estimated Time:** 8-12 hours (1-2 days)

**Recommended Approach:**
1. Start with Phase 1 (critical fixes)
2. Complete Phase 2 incrementally (one service file at a time)
3. Finish with Phase 3 (tests and docs)

---

## Comparison with Accounts App Refactoring

The accounts app refactoring serves as a **template** for the beans app:

### Accounts App Refactoring Results

✅ **Completed in ~6 hours**
✅ **Zero breaking changes**
✅ **All tests passing**
✅ **Improved code quality significantly**
✅ **Added comprehensive documentation**

### Lessons Learned

1. **Start with exceptions** - Create domain exceptions first
2. **One service at a time** - Don't refactor everything at once
3. **Test incrementally** - Run tests after each service
4. **Document as you go** - Update docs with each phase

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing functionality | Low | High | Comprehensive test suite |
| Database migration issues | Low | Medium | MergeHistory is additive only |
| Performance degradation | Very Low | Medium | select_for_update() is minimal overhead |
| Merge conflicts | Low | Low | Work on feature branch |

**Overall Risk:** **LOW**

---

## Conclusion

The beans app requires refactoring to match DRF best practices. While it has some good foundations (existing services, ViewSets), it needs:

1. ✅ **Critical fixes** (MergeHistory model, transaction safety)
2. ✅ **Service layer restructuring** (modular services)
3. ✅ **Business logic relocation** (from views/models to services)

**Next Steps:**
1. Review and approve this analysis
2. Create feature branch
3. Follow [`REFACTORING_BEANS_CHECKLIST.md`](./REFACTORING_BEANS_CHECKLIST.md)
4. Submit PR when complete

**Estimated Completion:** 1-2 days of focused work
