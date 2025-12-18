# Purchases App Refactoring Checklist

> **Target Version:** 1.0.0
> **Estimated Effort:** 12-16 hours
> **Priority:** High
> **Status:** Ready to Start

---

## Overview

This checklist guides the systematic refactoring of the `purchases` app to align with DRF best practices. The refactoring is divided into **7 phases**, each building on the previous one.

**Current Score:** 75/100 (B+)
**Target Score:** 95/100 (A)

---

## Phase 1: Domain Exceptions

**Goal:** Create custom exception hierarchy for purchase domain

**Estimated Time:** 1-2 hours

### Tasks

1. Create `apps/purchases/exceptions.py`:

```python
"""
Domain exceptions for purchases app.

This module defines the exception hierarchy for purchase-related errors,
providing specific error types for better error handling and testing.
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
```

2. Update `services.py` to raise domain exceptions:

```python
# Replace ValueError with domain exceptions
# services.py:172-173
if not participants:
    raise NoParticipantsError("No participants found for split")

# services.py:283-286
if total_check != total_czk:
    raise InvalidSplitError(
        f"Split calculation error: {total_check} != {total_czk}"
    )

# services.py:332-333
if share.status == PaymentStatus.PAID:
    raise PaymentAlreadyPaidError("Share already marked as paid")
```

3. Update `models.py` to raise domain exceptions:

```python
# models.py - Add validation method
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

### Verification

- [ ] All domain exceptions defined
- [ ] Services raise domain exceptions instead of ValueError
- [ ] Models raise domain exceptions for invalid state transitions
- [ ] APIException subclasses have proper status codes
- [ ] All exceptions have docstrings

---

## Phase 2: Input Serializers

**Goal:** Create input serializers for query parameter validation

**Estimated Time:** 2-3 hours

### Tasks

1. Add input serializers to `serializers.py`:

```python
class PurchaseFilterSerializer(serializers.Serializer):
    """
    Validate query parameters for purchase filtering.

    Query Parameters:
        group (UUID): Filter by group ID
        user (UUID): Filter by user ID (bought or has share)
        date_from (date): Filter purchases from this date
        date_to (date): Filter purchases to this date
        is_fully_paid (bool): Filter by payment status
    """

    group = serializers.UUIDField(required=False)
    user = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    is_fully_paid = serializers.BooleanField(required=False)

    def validate(self, attrs):
        """Validate date range."""
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')

        if date_from and date_to:
            if date_from > date_to:
                raise serializers.ValidationError({
                    'date_to': 'End date must be after start date'
                })

        return attrs


class PaymentShareFilterSerializer(serializers.Serializer):
    """
    Validate query parameters for payment share filtering.

    Query Parameters:
        status (str): Filter by payment status
        purchase (UUID): Filter by purchase ID
    """

    status = serializers.ChoiceField(
        choices=PaymentStatus.choices,
        required=False
    )
    purchase = serializers.UUIDField(required=False)


class MarkPaidInputSerializer(serializers.Serializer):
    """
    Validate input for marking payment as paid.

    Fields:
        payment_reference (str): Optional payment reference to mark
        note (str): Optional note for the payment
    """

    payment_reference = serializers.CharField(max_length=64, required=False)
    note = serializers.CharField(max_length=500, required=False)
```

2. Update views to use input serializers (will be done in Phase 5)

### Verification

- [ ] `PurchaseFilterSerializer` validates all filter parameters
- [ ] `PaymentShareFilterSerializer` validates status choices
- [ ] Date range validation works correctly
- [ ] Boolean field parsing works (no more `.lower() == 'true'`)
- [ ] UUID validation works

---

## Phase 3: Custom Permission Classes

**Goal:** Create custom permission classes for access control

**Estimated Time:** 2-3 hours

### Tasks

1. Create `apps/purchases/permissions.py`:

```python
"""
Custom permission classes for purchases app.

This module defines permission classes for controlling access to
purchase records and payment shares.
"""
from rest_framework.permissions import BasePermission


class IsGroupMemberForPurchase(BasePermission):
    """
    Permission to check if user is a member of the purchase's group.

    Allows access if:
    - Purchase is personal (no group) and user is the buyer
    - Purchase is in a group and user is a member
    """

    message = 'You must be a member of this group to view this purchase.'

    def has_object_permission(self, request, view, obj):
        # Personal purchase - check if user is the buyer
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - check if user is a member
        return obj.group.has_member(request.user)


class CanManagePurchase(BasePermission):
    """
    Permission to manage (update/delete) a purchase.

    Allows if:
    - Personal purchase: user is the buyer
    - Group purchase: user is the buyer OR group owner
    """

    message = 'You do not have permission to manage this purchase.'

    def has_object_permission(self, request, view, obj):
        # Personal purchase - must be buyer
        if not obj.group:
            return obj.bought_by == request.user

        # Group purchase - buyer or group owner
        return (
            obj.bought_by == request.user or
            obj.group.owner == request.user
        )


class CanMarkPaymentPaid(BasePermission):
    """
    Permission to mark a payment share as paid.

    Allows if:
    - User is marking their own payment
    - User is the purchase buyer (can mark any share)
    - User is the group owner (can mark any share)
    """

    message = 'You do not have permission to mark this payment as paid.'

    def has_object_permission(self, request, view, obj):
        # User marking their own payment
        if obj.user == request.user:
            return True

        # Purchase buyer can mark any payment
        if obj.purchase.bought_by == request.user:
            return True

        # Group owner can mark any payment in their group
        if obj.purchase.group and obj.purchase.group.owner == request.user:
            return True

        return False


class IsGroupMemberForShare(BasePermission):
    """
    Permission to view a payment share.

    Allows if:
    - User owns the payment share
    - User is a member of the purchase's group
    """

    message = 'You do not have permission to view this payment share.'

    def has_object_permission(self, request, view, obj):
        # User owns the share
        if obj.user == request.user:
            return True

        # User is member of the group
        if obj.purchase.group:
            return obj.purchase.group.has_member(request.user)

        # Personal purchase - only buyer can see
        return obj.purchase.bought_by == request.user
```

2. Remove permission logic from serializers:

```python
# serializers.py - Remove this validation
# DELETE lines 134-139:
if not group.has_member(request.user):
    raise serializers.ValidationError({
        'group': 'You must be a member of this group'
    })
```

### Verification

- [ ] `IsGroupMemberForPurchase` checks group membership
- [ ] `CanManagePurchase` restricts update/delete
- [ ] `CanMarkPaymentPaid` allows appropriate users
- [ ] `IsGroupMemberForShare` protects payment shares
- [ ] Permission logic removed from serializers
- [ ] All permissions have descriptive messages

---

## Phase 4: Service Layer Enhancement

**Goal:** Enhance service layer to work with domain exceptions

**Estimated Time:** 2 hours

### Tasks

1. Update `PurchaseSplitService` methods:

```python
# services.py - Update create_group_purchase
@staticmethod
def create_group_purchase(...):
    with transaction.atomic():
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            raise PurchaseNotFoundError(f"Group {group_id} not found")

        # ... rest of method
        if not participants:
            raise NoParticipantsError("No participants found for split")

        # ... continue

# services.py - Update reconcile_payment
@staticmethod
def reconcile_payment(share_id, paid_by_user, method='manual'):
    with transaction.atomic():
        try:
            share = PaymentShare.objects.select_for_update().get(id=share_id)
        except PaymentShare.DoesNotExist:
            raise PaymentShareNotFoundError(f"Share {share_id} not found")

        if share.status == PaymentStatus.PAID:
            raise PaymentAlreadyPaidError("Share already marked as paid")

        share.mark_paid(paid_by_user=paid_by_user)
        return share
```

2. Add new service method for marking payment by reference:

```python
# services.py - Add new method
@staticmethod
def mark_purchase_paid(purchase_id, payment_reference=None, user=None):
    """
    Mark a payment share as paid by reference or user.

    Args:
        purchase_id: Purchase ID
        payment_reference: Optional payment reference
        user: User to find share for (if no reference)

    Returns:
        Updated PaymentShare

    Raises:
        PaymentShareNotFoundError: If share not found
        PaymentAlreadyPaidError: If share already paid
    """
    with transaction.atomic():
        try:
            purchase = PurchaseRecord.objects.get(id=purchase_id)
        except PurchaseRecord.DoesNotExist:
            raise PurchaseNotFoundError(f"Purchase {purchase_id} not found")

        if payment_reference:
            try:
                share = PaymentShare.objects.get(
                    purchase=purchase,
                    payment_reference=payment_reference
                )
            except PaymentShare.DoesNotExist:
                raise PaymentShareNotFoundError(
                    f"Payment share with reference {payment_reference} not found"
                )
        elif user:
            try:
                share = PaymentShare.objects.get(
                    purchase=purchase,
                    user=user
                )
            except PaymentShare.DoesNotExist:
                raise PaymentShareNotFoundError(
                    f"You do not have a payment share in this purchase"
                )
        else:
            raise ValueError("Either payment_reference or user must be provided")

        return PurchaseSplitService.reconcile_payment(
            share_id=share.id,
            paid_by_user=user,
            method='manual'
        )
```

### Verification

- [ ] Services raise domain exceptions
- [ ] `mark_purchase_paid` method added
- [ ] All service methods use `select_for_update()`
- [ ] Transaction management unchanged
- [ ] Docstrings updated with exception documentation

---

## Phase 5: Refactor Views to Thin HTTP Handlers

**Goal:** Refactor views to be thin HTTP handlers using serializers and permissions

**Estimated Time:** 3-4 hours

### Tasks

1. Update `PurchaseRecordViewSet.get_queryset()`:

```python
# views.py - Refactor get_queryset
def get_queryset(self):
    """Filter purchases using input serializer."""
    queryset = super().get_queryset()

    # Validate query parameters
    filter_serializer = PurchaseFilterSerializer(data=self.request.query_params)
    filter_serializer.is_valid(raise_exception=True)
    params = filter_serializer.validated_data

    # Apply filters
    if 'group' in params:
        queryset = queryset.filter(group_id=params['group'])
    else:
        # Show purchases where user is involved
        queryset = queryset.filter(
            models.Q(bought_by=self.request.user) |
            models.Q(payment_shares__user=self.request.user)
        ).distinct()

    if 'user' in params:
        queryset = queryset.filter(
            models.Q(bought_by_id=params['user']) |
            models.Q(payment_shares__user_id=params['user'])
        ).distinct()

    if 'date_from' in params:
        queryset = queryset.filter(date__gte=params['date_from'])

    if 'date_to' in params:
        queryset = queryset.filter(date__lte=params['date_to'])

    if 'is_fully_paid' in params:
        queryset = queryset.filter(is_fully_paid=params['is_fully_paid'])

    return queryset
```

2. Refactor `mark_paid` action:

```python
# views.py - Refactor mark_paid (before: 54 lines)
@action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanMarkPaymentPaid])
def mark_paid(self, request, pk=None):
    """Mark a payment share as paid - thin HTTP handler."""
    purchase = self.get_object()

    # Validate input
    serializer = MarkPaidInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Mark payment paid using service
    share = PurchaseSplitService.mark_purchase_paid(
        purchase_id=purchase.id,
        payment_reference=serializer.validated_data.get('payment_reference'),
        user=request.user
    )

    return Response(PaymentShareSerializer(share).data)
```

3. Update permission classes:

```python
# views.py - Update viewset permissions
class PurchaseRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsGroupMemberForPurchase]

    def get_permissions(self):
        """Use different permissions for different actions."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManagePurchase()]
        elif self.action == 'mark_paid':
            return [IsAuthenticated(), CanMarkPaymentPaid()]
        return super().get_permissions()
```

4. Refactor `PaymentShareViewSet.get_queryset()`:

```python
# views.py - Refactor PaymentShareViewSet.get_queryset
def get_queryset(self):
    """Filter payment shares using input serializer."""
    # Validate query parameters
    filter_serializer = PaymentShareFilterSerializer(data=self.request.query_params)
    filter_serializer.is_valid(raise_exception=True)
    params = filter_serializer.validated_data

    # Base queryset - user's own shares or shares in their groups
    queryset = PaymentShare.objects.filter(
        models.Q(user=self.request.user) |
        models.Q(purchase__group__memberships__user=self.request.user)
    ).select_related('purchase', 'user', 'paid_by').distinct()

    # Apply filters
    if 'status' in params:
        queryset = queryset.filter(status=params['status'])

    if 'purchase' in params:
        queryset = queryset.filter(purchase_id=params['purchase'])

    return queryset
```

5. Update `my_outstanding_payments` view:

```python
# views.py - Simplify my_outstanding_payments (already simple)
@extend_schema(
    responses={200: OutstandingPaymentsResponseSerializer},
    description="Get all outstanding (unpaid) payment shares for the current user.",
    tags=['purchases'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_outstanding_payments(request):
    """Get all outstanding payments for current user - thin HTTP handler."""
    shares = PaymentShare.objects.filter(
        user=request.user,
        status=PaymentStatus.UNPAID
    ).select_related('purchase', 'purchase__coffeebean').order_by('created_at')

    total_outstanding = sum(share.amount_czk for share in shares)

    return Response({
        'total_outstanding': total_outstanding,
        'count': shares.count(),
        'shares': PaymentShareSerializer(shares, many=True).data
    })
```

### Verification

- [ ] All views use input serializers for query parameters
- [ ] Permission classes used at view level (not inline)
- [ ] `mark_paid` action is thin (~15 lines)
- [ ] No manual error Response construction
- [ ] Views only handle HTTP concerns
- [ ] Business logic delegated to services

---

## Phase 6: Comprehensive Test Suite

**Goal:** Create comprehensive test coverage

**Estimated Time:** 4-5 hours

### Tasks

1. Create `apps/purchases/tests/conftest.py`:

```python
"""
Pytest fixtures for purchases app tests.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group, GroupMembership, GroupRole
from apps.purchases.models import PurchaseRecord, PaymentShare, PaymentStatus


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


# Users
@pytest.fixture
def purchase_user(db):
    """Create main test user."""
    return User.objects.create_user(
        email='buyer@example.com',
        password='TestPass123!',
        display_name='Buyer User',
        email_verified=True,
    )


@pytest.fixture
def purchase_member1(db):
    """Create group member 1."""
    return User.objects.create_user(
        email='member1@example.com',
        password='TestPass123!',
        display_name='Member 1',
        email_verified=True,
    )


@pytest.fixture
def purchase_member2(db):
    """Create group member 2."""
    return User.objects.create_user(
        email='member2@example.com',
        password='TestPass123!',
        display_name='Member 2',
        email_verified=True,
    )


@pytest.fixture
def purchase_outsider(db):
    """Create user outside group."""
    return User.objects.create_user(
        email='outsider@example.com',
        password='TestPass123!',
        display_name='Outsider',
        email_verified=True,
    )


# Groups
@pytest.fixture
def purchase_group(db, purchase_user, purchase_member1, purchase_member2):
    """Create test group with 3 members."""
    group = Group.objects.create(
        name='Coffee Buyers Group',
        description='Test group',
        is_private=True,
        owner=purchase_user,
    )
    GroupMembership.objects.create(user=purchase_user, group=group, role=GroupRole.OWNER)
    GroupMembership.objects.create(user=purchase_member1, group=group, role=GroupRole.MEMBER)
    GroupMembership.objects.create(user=purchase_member2, group=group, role=GroupRole.MEMBER)
    return group


# Coffee beans
@pytest.fixture
def purchase_bean(db, purchase_user):
    """Create test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopia Yirgacheffe',
        roastery_name='Top Roasters',
        origin_country='Ethiopia',
        roast_profile='light',
        created_by=purchase_user,
    )


# Purchases
@pytest.fixture
def personal_purchase(db, purchase_user, purchase_bean):
    """Create personal purchase."""
    return PurchaseRecord.objects.create(
        bought_by=purchase_user,
        coffeebean=purchase_bean,
        total_price_czk=Decimal('500.00'),
        package_weight_grams=500,
        date=date.today(),
        purchase_location='Coffee Shop',
    )


@pytest.fixture
def group_purchase_with_shares(db, purchase_group, purchase_user, purchase_bean):
    """Create group purchase with payment shares."""
    from apps.purchases.services import PurchaseSplitService

    purchase, shares = PurchaseSplitService.create_group_purchase(
        group_id=purchase_group.id,
        bought_by_user=purchase_user,
        total_price_czk=Decimal('900.00'),
        date=date.today(),
        coffeebean=purchase_bean,
        package_weight_grams=1000,
    )
    return purchase, shares
```

2. Create `apps/purchases/tests/test_services.py`:

```python
"""
Tests for purchase services.
"""
import pytest
from decimal import Decimal
from datetime import date
from apps.purchases.services import PurchaseSplitService
from apps.purchases.models import PaymentStatus
from apps.purchases.exceptions import (
    NoParticipantsError,
    InvalidSplitError,
    PaymentAlreadyPaidError,
)


@pytest.mark.django_db
class TestPurchaseSplitService:
    """Test PurchaseSplitService methods."""

    def test_create_group_purchase_splits_evenly(
        self, purchase_group, purchase_user, purchase_bean
    ):
        """Test that purchase splits evenly among members."""
        purchase, shares = PurchaseSplitService.create_group_purchase(
            group_id=purchase_group.id,
            bought_by_user=purchase_user,
            total_price_czk=Decimal('900.00'),
            date=date.today(),
            coffeebean=purchase_bean,
        )

        assert len(shares) == 3
        amounts = [share.amount_czk for share in shares]
        assert sum(amounts) == Decimal('900.00')
        assert all(amount == Decimal('300.00') for amount in amounts)

    def test_create_group_purchase_halere_precision(
        self, purchase_group, purchase_user
    ):
        """Test haléř precision with uneven split."""
        purchase, shares = PurchaseSplitService.create_group_purchase(
            group_id=purchase_group.id,
            bought_by_user=purchase_user,
            total_price_czk=Decimal('100.00'),
            date=date.today(),
        )

        amounts = sorted([share.amount_czk for share in shares])
        # 100.00 / 3 = 33.33, 33.33, 33.34
        assert amounts == [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')]
        assert sum(amounts) == Decimal('100.00')

    def test_reconcile_payment_marks_paid(self, group_purchase_with_shares):
        """Test marking payment as paid."""
        purchase, shares = group_purchase_with_shares
        share = shares[0]

        updated_share = PurchaseSplitService.reconcile_payment(
            share_id=share.id,
            paid_by_user=share.user,
        )

        assert updated_share.status == PaymentStatus.PAID
        assert updated_share.paid_at is not None
        assert updated_share.paid_by == share.user

    def test_reconcile_payment_raises_if_already_paid(self, group_purchase_with_shares):
        """Test that reconciling already-paid share raises error."""
        purchase, shares = group_purchase_with_shares
        share = shares[0]

        # Mark as paid
        PurchaseSplitService.reconcile_payment(share_id=share.id, paid_by_user=share.user)

        # Try to mark again
        with pytest.raises(PaymentAlreadyPaidError):
            PurchaseSplitService.reconcile_payment(share_id=share.id, paid_by_user=share.user)
```

3. Create `apps/purchases/tests/test_api.py`:

```python
"""
Tests for purchase API endpoints.
"""
import pytest
from decimal import Decimal
from datetime import date
from rest_framework import status
from apps.purchases.models import PaymentStatus


@pytest.mark.django_db
class TestPurchaseAPI:
    """Test purchase API endpoints."""

    def test_create_group_purchase(self, api_client, purchase_user, purchase_group, purchase_bean):
        """Test creating a group purchase."""
        api_client.force_authenticate(user=purchase_user)

        response = api_client.post('/api/purchases/', {
            'group': str(purchase_group.id),
            'coffeebean': str(purchase_bean.id),
            'total_price_czk': '900.00',
            'package_weight_grams': 1000,
            'date': date.today().isoformat(),
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['total_price_czk'] == '900.00'
        assert len(response.data['payment_shares']) == 3

    def test_non_member_cannot_create_group_purchase(
        self, api_client, purchase_outsider, purchase_group, purchase_bean
    ):
        """Test that non-member cannot create group purchase."""
        api_client.force_authenticate(user=purchase_outsider)

        response = api_client.post('/api/purchases/', {
            'group': str(purchase_group.id),
            'coffeebean': str(purchase_bean.id),
            'total_price_czk': '500.00',
            'date': date.today().isoformat(),
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_mark_payment_paid(self, api_client, purchase_user, group_purchase_with_shares):
        """Test marking payment as paid."""
        purchase, shares = group_purchase_with_shares
        share = shares[0]

        api_client.force_authenticate(user=share.user)

        response = api_client.post(
            f'/api/purchases/{purchase.id}/mark_paid/',
            {}  # No payment reference - uses current user
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == PaymentStatus.PAID

    def test_outstanding_payments(self, api_client, purchase_user, group_purchase_with_shares):
        """Test getting outstanding payments."""
        purchase, shares = group_purchase_with_shares

        api_client.force_authenticate(user=purchase_user)

        response = api_client.get('/api/purchases/my-outstanding-payments/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert Decimal(response.data['total_outstanding']) == Decimal('300.00')
```

4. Create `apps/purchases/tests/test_permissions.py`:

```python
"""
Tests for purchase permission classes.
"""
import pytest
from unittest.mock import Mock
from apps.purchases.permissions import (
    IsGroupMemberForPurchase,
    CanManagePurchase,
    CanMarkPaymentPaid,
)


@pytest.mark.django_db
class TestIsGroupMemberForPurchase:
    """Test IsGroupMemberForPurchase permission."""

    def test_personal_purchase_owner_allowed(self, personal_purchase, purchase_user):
        """Test that personal purchase owner can access."""
        permission = IsGroupMemberForPurchase()
        request = Mock(user=purchase_user)

        assert permission.has_object_permission(request, None, personal_purchase) is True

    def test_personal_purchase_other_user_denied(self, personal_purchase, purchase_outsider):
        """Test that other user cannot access personal purchase."""
        permission = IsGroupMemberForPurchase()
        request = Mock(user=purchase_outsider)

        assert permission.has_object_permission(request, None, personal_purchase) is False

    def test_group_member_allowed(self, group_purchase_with_shares, purchase_member1):
        """Test that group member can access group purchase."""
        purchase, shares = group_purchase_with_shares
        permission = IsGroupMemberForPurchase()
        request = Mock(user=purchase_member1)

        assert permission.has_object_permission(request, None, purchase) is True

    def test_non_member_denied(self, group_purchase_with_shares, purchase_outsider):
        """Test that non-member cannot access group purchase."""
        purchase, shares = group_purchase_with_shares
        permission = IsGroupMemberForPurchase()
        request = Mock(user=purchase_outsider)

        assert permission.has_object_permission(request, None, purchase) is False
```

5. Create `apps/purchases/tests/test_serializers.py`:

```python
"""
Tests for purchase serializers.
"""
import pytest
from datetime import date
from apps.purchases.serializers import (
    PurchaseFilterSerializer,
    PaymentShareFilterSerializer,
)
from apps.purchases.models import PaymentStatus


class TestPurchaseFilterSerializer:
    """Test PurchaseFilterSerializer validation."""

    def test_valid_filters(self):
        """Test valid filter parameters."""
        serializer = PurchaseFilterSerializer(data={
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'is_fully_paid': 'true',
        })

        assert serializer.is_valid()
        assert serializer.validated_data['is_fully_paid'] is True

    def test_invalid_date_range(self):
        """Test that end date before start date fails."""
        serializer = PurchaseFilterSerializer(data={
            'date_from': '2025-12-31',
            'date_to': '2025-01-01',
        })

        assert not serializer.is_valid()
        assert 'date_to' in serializer.errors


class TestPaymentShareFilterSerializer:
    """Test PaymentShareFilterSerializer validation."""

    def test_valid_status(self):
        """Test valid status filter."""
        serializer = PaymentShareFilterSerializer(data={
            'status': PaymentStatus.PAID,
        })

        assert serializer.is_valid()
        assert serializer.validated_data['status'] == PaymentStatus.PAID

    def test_invalid_status(self):
        """Test invalid status value."""
        serializer = PaymentShareFilterSerializer(data={
            'status': 'invalid_status',
        })

        assert not serializer.is_valid()
        assert 'status' in serializer.errors
```

### Verification

- [ ] `test_services.py` created with service layer tests
- [ ] `test_api.py` created with API endpoint tests
- [ ] `test_permissions.py` created with permission tests
- [ ] `test_serializers.py` created with serializer tests
- [ ] `conftest.py` has comprehensive fixtures
- [ ] Tests cover happy paths and error cases
- [ ] All tests pass

---

## Phase 7: Documentation & Version 1.0.0

**Goal:** Update documentation and prepare for 1.0.0 release

**Estimated Time:** 1-2 hours

### Tasks

1. Update `docs/app-context/purchases.md`:

```markdown
# Add "Recent Refactoring" section
## Recent Refactoring (December 2025)

**Status:** Completed Phases 1-7 of DRF best practices refactoring

### Refactoring Summary

- ✅ Domain Exceptions: Custom exception hierarchy for purchase errors
- ✅ Input Serializers: Query parameter validation
- ✅ Custom Permissions: Access control for purchases and payment shares
- ✅ Enhanced Services: Domain exception handling
- ✅ Thin Views: Refactored to ~15-20 lines per action
- ✅ Comprehensive Tests: 80%+ test coverage
- ✅ Documentation: Updated with refactoring details

### Architecture After Refactoring

```
apps/purchases/
├── exceptions.py          # Domain exceptions (Phase 1)
├── serializers.py         # Input + Output serializers (Phase 2)
├── permissions.py         # Custom permission classes (Phase 3)
├── services.py           # Service layer (enhanced in Phase 4)
├── views.py              # Thin HTTP handlers (refactored in Phase 5)
├── models.py             # Domain models (state validation added)
├── tests/
│   ├── conftest.py       # Test fixtures
│   ├── test_services.py  # Service layer tests
│   ├── test_api.py       # API endpoint tests
│   ├── test_permissions.py  # Permission tests
│   └── test_serializers.py  # Serializer tests
```

### Key Improvements

1. **Views reduced** from 327 to ~200 lines (39% reduction)
2. **Test coverage** increased from 0% to 80%+
3. **Custom exceptions** for better error handling
4. **Permission classes** for declarative access control
5. **Input serializers** for robust validation
6. **DRF best practices** score: 75 → 95 (A grade)
```

2. Create version tag:

```bash
# Commit all changes
git add apps/purchases/
git commit -m "Purchases app refactoring complete - v1.0.0

- Added domain exception hierarchy
- Created input serializers for query parameters
- Implemented custom permission classes
- Enhanced service layer with exception handling
- Refactored views to thin HTTP handlers
- Added comprehensive test suite (80%+ coverage)
- Updated documentation

DRF best practices score: 95/100 (A)"

# Tag version 1.0.0
git tag -a purchases-v1.0.0 -m "Purchases app v1.0.0 - Production ready

- Full DRF best practices compliance
- Comprehensive test coverage
- Domain-driven design
- Clean architecture"

# Push
git push origin claude/github-workflow-guide-ieUiF --tags
```

3. Update `__init__.py` with version:

```python
# apps/purchases/__init__.py
"""
Purchases App - Coffee Purchase Management

Version: 1.0.0
Status: Production Ready
DRF Best Practices Score: 95/100 (A)
"""

__version__ = '1.0.0'
```

### Verification

- [ ] `docs/app-context/purchases.md` updated
- [ ] Refactoring section added to documentation
- [ ] Architecture diagram updated
- [ ] Version 1.0.0 tagged in git
- [ ] `__init__.py` has version number
- [ ] All changes committed and pushed

---

## Summary Checklist

### Must Complete (Essential)

- [ ] Phase 1: Domain exceptions
- [ ] Phase 2: Input serializers
- [ ] Phase 3: Custom permission classes
- [ ] Phase 4: Service layer enhancement
- [ ] Phase 5: Refactor views

### Should Complete (Important)

- [ ] Phase 6: Comprehensive test suite
- [ ] Phase 7: Documentation & v1.0.0

### Final Verification

- [ ] All views are thin HTTP handlers (< 25 lines)
- [ ] No business logic in views
- [ ] Input validation via serializers
- [ ] Domain exceptions used throughout
- [ ] Permission classes for access control
- [ ] Services use transactions and locking
- [ ] Test coverage ≥ 80%
- [ ] Documentation updated
- [ ] Version 1.0.0 tagged

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Domain Exceptions | 1-2 hours | None |
| Phase 2: Input Serializers | 2-3 hours | Phase 1 |
| Phase 3: Custom Permissions | 2-3 hours | None |
| Phase 4: Service Enhancement | 2 hours | Phase 1 |
| Phase 5: Refactor Views | 3-4 hours | Phases 1-4 |
| Phase 6: Test Suite | 4-5 hours | Phases 1-5 |
| Phase 7: Documentation | 1-2 hours | Phases 1-6 |
| **Total** | **15-21 hours** | |

**Recommended Approach:**
1. Complete Phases 1-3 in parallel (they're independent)
2. Complete Phase 4 (uses Phase 1)
3. Complete Phase 5 (uses Phases 1-4)
4. Complete Phase 6 (uses Phases 1-5)
5. Complete Phase 7 (final documentation)

---

**End of Checklist**
