# Purchases App Analysis - DRF Best Practices Review

> **Analysis Date:** 2025-12-18
> **Reviewer:** Claude AI Assistant
> **App Version:** Pre-1.0.0
> **Status:** Ready for Refactoring

---

## Executive Summary

The `purchases` app is a **well-structured Django/DRF application** with solid service layer patterns and good separation of concerns. It scores **75/100** against DRF best practices, with strengths in service design and transaction management, but opportunities for improvement in views, input validation, and permission handling.

**Overall Grade:** **B+ (75%)**

**Key Strengths:**
- ✅ **Excellent service layer** with `PurchaseSplitService` and `SPDPaymentGenerator`
- ✅ **Strong transaction management** with `transaction.atomic` decorators
- ✅ **Good domain modeling** with `PurchaseRecord` and `PaymentShare` models
- ✅ **Concurrency protection** with `select_for_update()`
- ✅ **Well-documented code** with comprehensive docstrings

**Areas for Improvement:**
- ❌ **Views have inline validation and query filtering logic**
- ❌ **Missing input serializers for query parameters**
- ❌ **Permission checks mixed with business logic in views**
- ❌ **Missing custom permission classes**
- ❌ **No domain-specific exceptions**
- ❌ **Missing comprehensive test suite**

---

## Detailed Analysis by Best Practice Category

### 1. Views – HTTP Layer (Score: 65/100)

**Current State:**

The app uses ViewSets (`PurchaseRecordViewSet`, `PaymentShareViewSet`) and a function-based view (`my_outstanding_payments`).

**Strengths:**
- ✅ Uses ViewSets for RESTful patterns
- ✅ Custom serializers for different actions (`get_serializer_class`)
- ✅ Delegates purchase creation to `PurchaseSplitService`
- ✅ Good use of `@action` decorators for custom endpoints
- ✅ Proper use of `@transaction.atomic` in `perform_create`

**Weaknesses:**
- ❌ **Inline query filtering logic** in `get_queryset()` (lines 59-107)
  ```python
  # views.py:74-106 - Too much logic in views
  group_id = self.request.query_params.get('group')
  if group_id:
      queryset = queryset.filter(group_id=group_id)
  # ... 30+ lines of filtering logic
  ```

- ❌ **Manual parameter parsing** in `get_queryset()`
  ```python
  # views.py:102-105
  is_fully_paid = self.request.query_params.get('is_fully_paid')
  if is_fully_paid is not None:
      is_paid = is_fully_paid.lower() == 'true'  # Manual boolean parsing
  ```

- ❌ **No input serializers** for query parameters
- ❌ **Complex error handling inline** (views.py:200-223)
  ```python
  # views.py:200-211 - Should use exception handling
  if payment_reference:
      try:
          share = PaymentShare.objects.get(...)
      except PaymentShare.DoesNotExist:
          return Response({'error': '...'}, status=404)
  ```

- ❌ **No custom permission classes** - relies on inline checks

**Recommendations:**
1. Create **input serializers** for query parameters (`PurchaseFilterSerializer`, `PaymentShareFilterSerializer`)
2. Move filtering logic to **service layer** or use **DRF filterset** classes
3. Create **custom permission classes** for group purchase access
4. Use **domain exceptions** instead of inline try/except with manual Response
5. Keep views thin (~10-20 lines per method)

**Example Refactor:**
```python
# Before (views.py:184-238) - 54 lines
@action(detail=True, methods=['post'])
def mark_paid(self, request, pk=None):
    purchase = self.get_object()
    serializer = MarkPaidSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    payment_reference = serializer.validated_data.get('payment_reference')

    if payment_reference:
        try:
            share = PaymentShare.objects.get(...)
        except PaymentShare.DoesNotExist:
            return Response({'error': '...'}, status=404)
    else:
        try:
            share = PaymentShare.objects.get(...)
        except PaymentShare.DoesNotExist:
            return Response({'error': '...'}, status=404)

    try:
        PurchaseSplitService.reconcile_payment(...)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    return Response(PaymentShareSerializer(share).data)

# After - Thin HTTP handler (~15 lines)
@action(detail=True, methods=['post'])
def mark_paid(self, request, pk=None):
    """Mark payment share as paid - thin HTTP handler."""
    purchase = self.get_object()
    serializer = MarkPaidSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        share = PurchaseSplitService.mark_purchase_paid(
            purchase_id=purchase.id,
            payment_reference=serializer.validated_data.get('payment_reference'),
            user=request.user
        )
    except (PaymentShareNotFoundError, PaymentAlreadyPaidError) as e:
        raise

    return Response(PaymentShareSerializer(share).data)
```

---

### 2. Services – Business Logic Layer (Score: 90/100)

**Current State:**

The app has **excellent service layer patterns** with two main service classes: `PurchaseSplitService` and `SPDPaymentGenerator`.

**Strengths:**
- ✅ **Pure static methods** - no stateful classes
- ✅ **Explicit arguments** - no implicit dependencies
- ✅ **Transaction management** with `@transaction.atomic`
- ✅ **Concurrency protection** with `select_for_update()`
- ✅ **Domain logic encapsulation** (haléř-precise splitting)
- ✅ **Excellent documentation** with comprehensive docstrings
- ✅ **Clear method signatures** with type hints
- ✅ **Single Responsibility Principle** - each service has one purpose

**Example of Good Service Design:**
```python
# services.py:76-206
@staticmethod
def create_group_purchase(
    group_id,
    bought_by_user,
    total_price_czk,
    date,
    coffeebean=None,
    variant=None,
    package_weight_grams=None,
    note='',
    split_members=None
):
    with transaction.atomic():
        # Validate group
        # Get participants
        # Create purchase
        # Calculate splits with haléř precision
        # Create payment shares
        return purchase, payment_shares
```

**Minor Weaknesses:**
- ⚠️ **No custom exceptions** - raises generic `ValueError`
  ```python
  # services.py:172-173
  if not participants:
      raise ValueError("No participants found for split")
  ```

- ⚠️ **Services return Django models** instead of plain dicts (acceptable for create operations)

**Recommendations:**
1. Create **domain exceptions** (`PurchaseServiceError`, `NoParticipantsError`, `InvalidSplitError`)
2. Add **exception handling** in views for domain exceptions
3. Consider returning **plain dicts** for query-only operations (not critical for create operations)

**Example Improvement:**
```python
# exceptions.py
class PurchaseServiceError(Exception):
    """Base exception for purchase service errors."""

class NoParticipantsError(PurchaseServiceError):
    """Raised when no participants found for split."""

class PaymentShareNotFoundError(PurchaseServiceError):
    """Raised when payment share not found."""

class PaymentAlreadyPaidError(PurchaseServiceError):
    """Raised when trying to mark already paid share."""

# services.py
if not participants:
    raise NoParticipantsError("No participants found for split")
```

**Grade Justification:**
- Loses 5 points for missing custom exceptions
- Loses 5 points for no plain dict return values (minor)
- **Overall: 90/100 - Excellent**

---

### 3. Models – Domain Layer (Score: 85/100)

**Current State:**

The app has **well-designed domain models** with good encapsulation and state management.

**Strengths:**
- ✅ **Clear domain entities** (`PurchaseRecord`, `PaymentShare`, `BankTransaction`)
- ✅ **Proper use of UUIDs** for primary keys
- ✅ **Good database constraints** (unique_together, indexes, validators)
- ✅ **Domain methods** (`update_collection_status()`, `mark_paid()`, `get_outstanding_balance()`)
- ✅ **State transitions encapsulated** in model methods
- ✅ **Proper use of Decimal** for monetary values
- ✅ **Good foreign key relationships** with proper cascading

**Example of Good Domain Design:**
```python
# models.py:95-109
def update_collection_status(self):
    """Recalculate collected amount and check if fully paid."""
    collected = self.payment_shares.filter(
        status=PaymentStatus.PAID
    ).aggregate(total=Sum('amount_czk'))['total'] or Decimal('0.00')

    self.total_collected_czk = collected
    self.is_fully_paid = (collected >= self.total_price_czk)
    self.save(update_fields=['total_collected_czk', 'is_fully_paid', 'updated_at'])

def get_outstanding_balance(self):
    """Return unpaid amount."""
    return max(Decimal('0.00'), self.total_price_czk - self.total_collected_czk)
```

**Weaknesses:**
- ⚠️ **State transition validation could be stricter**
  ```python
  # models.py:197-207 - mark_paid doesn't check if already paid
  def mark_paid(self, paid_by_user=None):
      from django.utils import timezone

      self.status = PaymentStatus.PAID  # No check if already paid
      self.paid_at = timezone.now()
      self.paid_by = paid_by_user
      self.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])
  ```

- ⚠️ **Missing domain validation methods** (e.g., `can_be_marked_paid()`)

**Recommendations:**
1. Add **validation methods** before state transitions
2. Raise **domain exceptions** for invalid state transitions
3. Make state transitions **idempotent** where possible

**Example Improvement:**
```python
# models.py - Improved mark_paid method
def can_be_marked_paid(self):
    """Check if payment share can be marked as paid."""
    return self.status in [PaymentStatus.UNPAID, PaymentStatus.FAILED]

def mark_paid(self, paid_by_user=None):
    """Mark share as paid with validation."""
    if not self.can_be_marked_paid():
        raise InvalidStateTransitionError(
            f"Cannot mark share as paid from status {self.status}"
        )

    from django.utils import timezone

    self.status = PaymentStatus.PAID
    self.paid_at = timezone.now()
    self.paid_by = paid_by_user
    self.save(update_fields=['status', 'paid_at', 'paid_by', 'updated_at'])
```

**Grade Justification:**
- Loses 10 points for missing state validation
- Loses 5 points for missing domain exception raising
- **Overall: 85/100 - Very Good**

---

### 4. Serializers – Validation & Transformation Layer (Score: 70/100)

**Current State:**

The app has **good output serializers** but is **missing input serializers** for query parameters.

**Strengths:**
- ✅ **Separate serializers for different actions** (Create, List, Detail)
- ✅ **Nested serializers** for related objects (UserMinimal, CoffeeBeanMinimal)
- ✅ **Read-only fields properly marked**
- ✅ **Custom validation** in `PurchaseRecordCreateSerializer.validate()`
- ✅ **Write-only fields** for input (`split_members`)

**Example of Good Serializer Design:**
```python
# serializers.py:101-142
class PurchaseRecordCreateSerializer(serializers.ModelSerializer):
    split_members = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    def validate(self, attrs):
        # Validate group membership
        if attrs.get('group'):
            request = self.context.get('request')
            if request and request.user:
                group = attrs.get('group')
                if not group.has_member(request.user):
                    raise serializers.ValidationError({
                        'group': 'You must be a member of this group'
                    })
        return attrs
```

**Weaknesses:**
- ❌ **Missing input serializers for query parameters**
  ```python
  # views.py:74-106 - No serializer, manual parsing
  group_id = self.request.query_params.get('group')
  date_from = self.request.query_params.get('date_from')
  is_fully_paid = self.request.query_params.get('is_fully_paid')
  # ... manual parsing and validation
  ```

- ❌ **No validation for filter parameters** (date formats, boolean values)
- ❌ **Inline permission validation in serializer** (should be in permission class)
  ```python
  # serializers.py:134-139 - Permission logic in serializer!
  if not group.has_member(request.user):
      raise serializers.ValidationError({
          'group': 'You must be a member of this group'
      })
  ```

**Recommendations:**
1. Create **input serializers** for query parameters:
   - `PurchaseFilterSerializer` (group, user, date_from, date_to, is_fully_paid)
   - `PaymentShareFilterSerializer` (status, purchase)
2. Move **permission logic to permission classes**
3. Add **validation for date ranges, boolean parsing**

**Example Improvement:**
```python
# serializers.py - New input serializers
class PurchaseFilterSerializer(serializers.Serializer):
    """Validate query parameters for purchase filtering."""

    group = serializers.UUIDField(required=False)
    user = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    is_fully_paid = serializers.BooleanField(required=False)

    def validate(self, attrs):
        """Validate date range."""
        if attrs.get('date_from') and attrs.get('date_to'):
            if attrs['date_from'] > attrs['date_to']:
                raise serializers.ValidationError({
                    'date_to': 'End date must be after start date'
                })
        return attrs

class PaymentShareFilterSerializer(serializers.Serializer):
    """Validate query parameters for payment share filtering."""

    status = serializers.ChoiceField(
        choices=PaymentStatus.choices,
        required=False
    )
    purchase = serializers.UUIDField(required=False)
```

**Grade Justification:**
- Loses 20 points for missing input serializers
- Loses 10 points for inline permission logic in serializer
- **Overall: 70/100 - Good**

---

### 5. Permissions – Access Control (Score: 60/100)

**Current State:**

The app uses `IsAuthenticated` but **lacks custom permission classes** for group-specific access control.

**Strengths:**
- ✅ **Basic authentication** with `IsAuthenticated`
- ✅ **Query filtering by user** in `get_queryset()`

**Weaknesses:**
- ❌ **No custom permission classes**
- ❌ **Permission logic in serializers** (serializers.py:134-139)
- ❌ **Permission logic in views** (implicit in get_queryset)
- ❌ **No group membership permission class**
- ❌ **No purchase ownership permission class**

**Current Permission Logic:**
```python
# serializers.py:134-139 - Permission in serializer!
if not group.has_member(request.user):
    raise serializers.ValidationError({
        'group': 'You must be a member of this group'
    })

# views.py:78-82 - Permission in query filtering
queryset = queryset.filter(
    models.Q(bought_by=user) |
    models.Q(payment_shares__user=user)
).distinct()
```

**Recommendations:**
1. Create **custom permission classes**:
   - `IsGroupMemberForPurchase` - Check if user is group member
   - `CanManagePurchase` - Check if user can edit/delete purchase
   - `CanMarkPaymentPaid` - Check if user can mark payment as paid
2. Move **permission logic from serializers to permission classes**
3. Use **declarative permissions** at view level with `@permission_classes`

**Example Improvement:**
```python
# permissions.py
class IsGroupMemberForPurchase(BasePermission):
    """
    Permission to check if user is a member of the purchase's group.
    Allows access if:
    - Purchase is personal (no group)
    - User is a member of the group
    """

    def has_object_permission(self, request, view, obj):
        # Personal purchase - check if user owns it
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - check membership
        return obj.group.has_member(request.user)

class CanManagePurchase(BasePermission):
    """
    Permission to manage (update/delete) a purchase.
    Only the purchaser or group admin can manage.
    """

    def has_object_permission(self, request, view, obj):
        # Personal purchase - must be buyer
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - must be buyer or group owner
        return (
            obj.bought_by == request.user or
            obj.group.owner == request.user
        )

# views.py
class PurchaseRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsGroupMemberForPurchase]
```

**Grade Justification:**
- Loses 30 points for no custom permission classes
- Loses 10 points for permission logic in wrong layers
- **Overall: 60/100 - Needs Improvement**

---

### 6. Exceptions – Error Handling (Score: 50/100)

**Current State:**

The app uses **generic Python exceptions** and **manual error responses** instead of custom domain exceptions.

**Strengths:**
- ✅ **Some exception handling** in services (`ValueError`)
- ✅ **Try/except blocks** in views

**Weaknesses:**
- ❌ **No custom exception hierarchy**
- ❌ **Generic ValueError/DoesNotExist exceptions**
- ❌ **Manual Response construction** for errors
  ```python
  # views.py:207-211
  except PaymentShare.DoesNotExist:
      return Response(
          {'error': 'Payment share not found'},
          status=status.HTTP_404_NOT_FOUND
      )
  ```

- ❌ **No exception handler integration**

**Recommendations:**
1. Create **domain exception hierarchy**:
   ```python
   # exceptions.py
   class PurchaseServiceError(Exception):
       """Base exception for purchase service."""

   class NoParticipantsError(PurchaseServiceError):
       """No participants for purchase split."""

   class PaymentShareNotFoundError(PurchaseServiceError):
       """Payment share not found."""

   class PaymentAlreadyPaidError(PurchaseServiceError):
       """Payment share already marked as paid."""

   class InvalidStateTransitionError(PurchaseServiceError):
       """Invalid payment state transition."""

   class InsufficientPermissionsError(PurchaseServiceError):
       """User doesn't have permission for operation."""
   ```

2. Use **DRF exception handling** with `APIException`
3. Register **custom exception handler** in settings
4. Raise **domain exceptions** from services/models
5. Let **DRF handle** exception-to-HTTP mapping

**Example Improvement:**
```python
# exceptions.py
from rest_framework.exceptions import APIException

class PaymentShareNotFoundError(APIException):
    status_code = 404
    default_detail = 'Payment share not found.'
    default_code = 'payment_share_not_found'

class PaymentAlreadyPaidError(APIException):
    status_code = 400
    default_detail = 'Payment share already marked as paid.'
    default_code = 'payment_already_paid'

# views.py - No manual error handling needed!
@action(detail=True, methods=['post'])
def mark_paid(self, request, pk=None):
    """Mark payment share as paid."""
    # Let exceptions propagate to DRF exception handler
    share = PurchaseSplitService.mark_purchase_paid(...)
    return Response(PaymentShareSerializer(share).data)
```

**Grade Justification:**
- Loses 40 points for no custom exception hierarchy
- Loses 10 points for manual error responses
- **Overall: 50/100 - Needs Significant Improvement**

---

### 7. Concurrency & Transactions (Score: 95/100)

**Current State:**

The app has **excellent concurrency protection** with proper transaction management and locking.

**Strengths:**
- ✅ **transaction.atomic decorators** in services
- ✅ **select_for_update()** in critical sections
  ```python
  # services.py:329-330
  with transaction.atomic():
      share = PaymentShare.objects.select_for_update().get(id=share_id)
  ```

- ✅ **Atomic updates** for collection status
- ✅ **Database constraints** (unique_together, unique payment_reference)
- ✅ **Proper F() expressions** where needed

**Example of Good Concurrency Management:**
```python
# services.py:291-337
@staticmethod
def reconcile_payment(share_id, paid_by_user, method='manual'):
    with transaction.atomic():
        share = PaymentShare.objects.select_for_update().get(id=share_id)

        if share.status == PaymentStatus.PAID:
            raise ValueError("Share already marked as paid")

        share.mark_paid(paid_by_user=paid_by_user)

        return share
```

**Minor Weaknesses:**
- ⚠️ **Could use F() expressions** for `total_collected_czk` updates (currently recalculates)
  ```python
  # models.py:95-105 - Could be more atomic
  def update_collection_status(self):
      collected = self.payment_shares.filter(
          status=PaymentStatus.PAID
      ).aggregate(total=Sum('amount_czk'))['total'] or Decimal('0.00')

      self.total_collected_czk = collected  # Could use F() expression
      self.is_fully_paid = (collected >= self.total_price_czk)
      self.save()
  ```

**Recommendations:**
1. Consider using **F() expressions** for `total_collected_czk` updates (not critical due to select_for_update)
2. Add **database constraints** for state transitions (e.g., CHECK constraints)

**Grade Justification:**
- Loses 5 points for potential F() expression optimization
- **Overall: 95/100 - Excellent**

---

### 8. Testing (Score: N/A - No Tests Found)

**Current State:**

```python
# tests.py - Empty file
```

**Status:** ❌ **No comprehensive test suite found**

**Required Tests:**
1. **Service Layer Tests**
   - `test_create_group_purchase_splits_correctly`
   - `test_halere_precision_splitting`
   - `test_reconcile_payment_marks_paid`
   - `test_reconcile_payment_idempotency`
   - `test_spd_payment_generator`

2. **Model Tests**
   - `test_update_collection_status`
   - `test_mark_paid_transitions`
   - `test_outstanding_balance_calculation`

3. **API Tests**
   - `test_create_purchase_as_group_member`
   - `test_create_purchase_requires_group_membership`
   - `test_mark_paid_with_payment_reference`
   - `test_mark_paid_without_reference_uses_current_user`
   - `test_outstanding_payments_endpoint`

4. **Permission Tests**
   - `test_group_member_can_view_purchase`
   - `test_non_member_cannot_view_purchase`
   - `test_only_buyer_can_delete_personal_purchase`

5. **Concurrency Tests**
   - `test_concurrent_mark_paid_does_not_double_pay`
   - `test_concurrent_purchase_creation`

**Recommendations:**
1. Create **comprehensive test suite** with pytest
2. Add **test_services.py** for service layer tests
3. Add **test_api.py** for API endpoint tests
4. Add **test_permissions.py** for permission tests
5. Add **test_models.py** for model behavior tests
6. Target **80%+ code coverage**

---

## Overall Assessment

### Scoring Summary

| Category | Score | Weight | Weighted Score |
|----------|-------|--------|----------------|
| Views | 65/100 | 20% | 13.0 |
| Services | 90/100 | 25% | 22.5 |
| Models | 85/100 | 15% | 12.75 |
| Serializers | 70/100 | 15% | 10.5 |
| Permissions | 60/100 | 10% | 6.0 |
| Exceptions | 50/100 | 5% | 2.5 |
| Concurrency | 95/100 | 10% | 9.5 |
| **Total** | | **100%** | **76.75/100** |

**Adjusted Score (without tests):** **75/100 (B+)**

---

## Critical Issues (Must Fix for 1.0.0)

1. ❌ **No custom permission classes** - Inline permission logic in serializers/views
2. ❌ **No domain exception hierarchy** - Using generic exceptions
3. ❌ **Missing input serializers** - Manual query parameter parsing
4. ❌ **No comprehensive test suite** - Critical for production readiness

---

## Recommendations for 1.0.0

### High Priority (Must Have)
1. ✅ Create **custom permission classes** (`permissions.py`)
2. ✅ Create **domain exception hierarchy** (`exceptions.py`)
3. ✅ Create **input serializers** for query parameters
4. ✅ Add **comprehensive test suite** (80%+ coverage)
5. ✅ Refactor views to be **thin HTTP handlers**

### Medium Priority (Should Have)
6. ✅ Move **filtering logic** to service layer or use DRF filters
7. ✅ Add **state validation** methods to models
8. ✅ Use **DRF exception handling** instead of manual responses
9. ✅ Document **API with OpenAPI/Spectacular** schemas

### Low Priority (Nice to Have)
10. Consider **read-only querysets** for list views
11. Add **soft delete** functionality for purchases
12. Implement **purchase audit log** for compliance
13. Add **webhook support** for payment confirmation

---

## Comparison with Analytics App Refactoring

The **purchases app** is in a similar position to where the **analytics app** was before refactoring:

| Aspect | Purchases App | Analytics App (Before) | Analytics App (After) |
|--------|---------------|------------------------|----------------------|
| **Service Layer** | ✅ Excellent | ❌ Poor | ✅ Excellent |
| **Input Serializers** | ❌ Missing | ❌ Missing | ✅ Complete |
| **Permission Classes** | ❌ Missing | ❌ Missing | ✅ Complete |
| **Domain Exceptions** | ❌ Missing | ❌ Missing | ✅ Complete |
| **Thin Views** | ⚠️ Needs Work | ❌ Fat Views | ✅ Thin (15-25 lines) |
| **Test Coverage** | ❌ None | ⚠️ Some | ✅ Comprehensive |

**Key Difference:** Purchases app already has **excellent service layer**, so refactoring will focus on **HTTP layer improvements** (views, permissions, serializers, exceptions).

---

## Next Steps

1. **Read the refactoring checklist** (`REFACTORING_PURCHASES_CHECKLIST.md`)
2. **Review each phase** with the team
3. **Start with Phase 1** (Domain Exceptions)
4. **Complete all 7 phases** systematically
5. **Run full test suite** after each phase
6. **Tag version 1.0.0** when complete

---

## Appendix: Files Overview

### Current Structure
```
apps/purchases/
├── models.py (253 lines) - Good domain models
├── serializers.py (189 lines) - Good output, missing input serializers
├── services.py (642 lines) - Excellent service layer
├── views.py (327 lines) - Needs refactoring (too fat)
├── tests/ - ❌ Empty
└── urls.py (60 lines) - Standard routing
```

### Target Structure (After Refactoring)
```
apps/purchases/
├── models.py - Domain models (minimal changes)
├── serializers.py - Output + Input serializers
├── services.py - Service layer (minimal changes)
├── views.py - Thin HTTP handlers (refactored)
├── permissions.py - NEW: Custom permission classes
├── exceptions.py - NEW: Domain exception hierarchy
├── filters.py - NEW: DRF filter classes (optional)
├── tests/
│   ├── __init__.py
│   ├── conftest.py - Test fixtures
│   ├── test_models.py - NEW: Model tests
│   ├── test_services.py - NEW: Service tests
│   ├── test_api.py - NEW: API endpoint tests
│   ├── test_permissions.py - NEW: Permission tests
│   └── test_serializers.py - NEW: Serializer tests
└── urls.py - Standard routing
```

---

**End of Analysis**
