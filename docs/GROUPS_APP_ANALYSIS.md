# Groups App - DRF Best Practices Analysis

**Date:** 2025-12-17
**App:** `apps/groups`
**Total Lines:** 821 Python lines
**Reference:** DRF_best_practices.md

---

## Executive Summary

The groups app requires **significant refactoring** to align with DRF best practices. While it has good URL structure and permissions classes, it suffers from:

1. **No services layer** - all business logic in views and models
2. **Extensive business logic in views** (~200 lines of business code)
3. **Missing transaction safety** - only 1 of 8 state-changing operations wrapped
4. **No concurrency protection** - no `select_for_update()` usage
5. **No domain exceptions** - using DRF exceptions directly
6. **Business logic in model `save()` methods**

**Severity:** 🔴 High - Multiple critical issues

**Estimated Refactoring Effort:** 1-2 days (8-12 hours)

---

## 1. Architecture Analysis

### Current Structure

```
apps/groups/
├── models.py           (117 lines) - Models + business methods
├── views.py            (378 lines) - ViewSets with extensive business logic
├── serializers.py      (147 lines) - Serializers with query logic
├── permissions.py      (31 lines)  - ✅ Good permission classes
├── urls.py             (35 lines)  - ✅ Clean routing
└── tests/
    ├── conftest.py     (fixtures)
    └── test_api.py     (API tests)
```

### Missing Components

```
❌ services/          - No services layer exists
❌ exceptions.py      - No domain-specific exceptions
```

---

## 2. Violation Analysis (by DRF Best Practice)

### 2.1 Core Architectural Principles ❌

**Issue:** No separation of concerns

```
Current architecture:
Views (HTTP + Business Logic)
↓
Models (Domain + More Business Logic)
↓
Database
```

**Expected architecture:**
```
Views (HTTP layer)
↓
Services (business layer)    ← MISSING
↓
Models (domain layer)
↓
Database
```

**Impact:** High - Makes testing, maintenance, and concurrency control difficult

---

### 2.2 Views – HTTP Layer ❌

**Best Practice:** "Views must not contain business rules, perform complex ORM logic, or manage transactions"

#### Violations in views.py:

**1. `perform_create()` (lines 70-82) - Business Logic in View**
```python
@transaction.atomic
def perform_create(self, serializer):
    """Create group and add creator as owner."""
    group = serializer.save(owner=self.request.user)

    # Business logic: Creating membership
    GroupMembership.objects.create(
        user=self.request.user,
        group=group,
        role=GroupRole.OWNER
    )
```

**Problem:** Group creation orchestration should be in a service
**Lines of business logic:** 8

---

**2. `join()` action (lines 104-143) - 40 Lines of Business Logic**
```python
def join(self, request, pk=None):
    group = self.get_object()
    serializer = JoinGroupSerializer(data=request.data)

    # Manual validation
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    invite_code = serializer.validated_data['invite_code']

    # Business rule: Verify invite code
    if group.invite_code != invite_code:
        return Response(
            {'error': 'Invalid invite code'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Business rule: Check if already a member
    if group.has_member(request.user):
        return Response(
            {'error': 'You are already a member of this group'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Database operation
    membership = GroupMembership.objects.create(
        user=request.user,
        group=group,
        role=GroupRole.MEMBER
    )

    return Response(...)
```

**Problems:**
- Business validation in view (invite code check, duplicate member check)
- Direct database operations in view
- ❌ **No transaction wrapper** - operation is not atomic
- ❌ **Race condition** - another request could join between the check and create

---

**3. `leave()` action (lines 145-173) - Business Logic**
```python
def leave(self, request, pk=None):
    group = self.get_object()

    # Business rule
    if group.owner == request.user:
        return Response(
            {'error': 'Group owner cannot leave...'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Database operations
    try:
        membership = GroupMembership.objects.get(user=request.user, group=group)
        membership.delete()
        return Response(...)
    except GroupMembership.DoesNotExist:
        return Response(...)
```

**Problems:**
- Business rule validation in view
- ❌ **No transaction wrapper**
- ❌ **No concurrency protection**

---

**4. `regenerate_invite()` action (lines 175-194) - Business Logic**
```python
def regenerate_invite(self, request, pk=None):
    group = self.get_object()

    # Permission check in view (should use DRF permissions)
    if not group.is_admin(request.user):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Only admins can regenerate invite codes")

    # Business operation
    new_code = group.regenerate_invite_code()

    return Response({...})
```

**Problems:**
- Permission check in view method (should be in permission class)
- Business logic called on model directly
- ❌ **No transaction wrapper**
- ❌ **Potential race condition** on invite code uniqueness

---

**5. `update_member_role()` action (lines 196-245) - 50 Lines of Business Logic**
```python
def update_member_role(self, request, pk=None):
    group = self.get_object()

    # Permission check
    if not group.is_admin(request.user):
        raise PermissionDenied(...)

    user_id = request.data.get('user_id')
    new_role = request.data.get('role')

    # Validation
    if not user_id or not new_role:
        return Response({'error': '...'}, ...)

    # More validation
    serializer = UpdateMemberRoleSerializer(data={'role': new_role})
    if not serializer.is_valid():
        return Response(...)

    # Database query
    try:
        membership = GroupMembership.objects.get(group=group, user_id=user_id)
    except GroupMembership.DoesNotExist:
        return Response(...)

    # Business rule
    if membership.role == GroupRole.OWNER:
        return Response({'error': 'Cannot change owner role'}, ...)

    # Database update
    membership.role = new_role
    membership.save(update_fields=['role'])

    return Response(...)
```

**Problems:**
- Extensive validation and business logic in view
- Permission checks in view instead of permission class
- ❌ **No transaction wrapper**
- ❌ **No row-level locking** (`select_for_update()`) - race condition possible
- ❌ **Critical race condition:** Two admins could change roles simultaneously

---

**6. `remove_member()` action (lines 247-289) - Business Logic**
```python
def remove_member(self, request, pk=None):
    group = self.get_object()

    # Permission check in view
    if not group.is_admin(request.user):
        raise PermissionDenied(...)

    user_id = request.data.get('user_id')

    if not user_id:
        return Response(...)

    # Business rule
    if str(group.owner.id) == str(user_id):
        return Response({'error': 'Cannot remove group owner'}, ...)

    # Database operations
    try:
        membership = GroupMembership.objects.get(group=group, user_id=user_id)
        membership.delete()
        return Response(...)
    except GroupMembership.DoesNotExist:
        return Response(...)
```

**Problems:**
- Business validation in view
- ❌ **No transaction wrapper**
- ❌ **No concurrency protection**

---

**7. `add_to_library()` action (lines 312-361) - Business Logic**
```python
def add_to_library(self, request, pk=None):
    group = self.get_object()

    # Permission check
    if not group.has_member(request.user):
        raise PermissionDenied(...)

    coffeebean_id = request.data.get('coffeebean_id')
    notes = request.data.get('notes', '')

    if not coffeebean_id:
        return Response(...)

    # Database query
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        return Response(...)

    # Database operation with race condition handling
    entry, created = GroupLibraryEntry.objects.get_or_create(
        group=group,
        coffeebean=coffeebean,
        defaults={'added_by': request.user, 'notes': notes}
    )

    if not created:
        return Response({'error': 'Coffee bean already in group library'}, ...)

    return Response(...)
```

**Problems:**
- Permission check in view
- Business logic and validation in view
- ❌ **No transaction wrapper** - `get_or_create` is atomic, but the whole operation should be wrapped
- Slightly better than others (uses `get_or_create`)

---

**Summary: Views Issues**

| Metric | Value |
|--------|-------|
| Total view methods | 13 |
| Methods with business logic | 8 |
| Lines of business logic in views | ~200 |
| Methods with `@transaction.atomic` | 1 of 8 state-changing |
| Methods with `select_for_update()` | 0 |
| Permission checks in view code | 4 |

**Severity:** 🔴 Critical

---

### 2.3 Services – Business Logic Layer ❌

**Best Practice:** "Services implement application use cases and represent the core business logic"

**Status:** ❌ **No services layer exists**

**Impact:** Critical - All business logic is scattered across views and models

**Required Services:**

```
apps/groups/services/
├── __init__.py
├── exceptions.py              # Domain exceptions
├── group_management.py        # create_group, update_group, delete_group
├── membership_management.py   # join_group, leave_group, remove_member
├── role_management.py         # update_member_role
├── invite_management.py       # regenerate_invite_code, validate_invite
└── library_management.py      # add_to_library, remove_from_library, pin_entry
```

---

### 2.4 Models – Domain Layer ⚠️

**Best Practice:** "Models enforce invariants and contain domain-level rules. Avoid cross-model orchestration."

#### Issues in models.py:

**1. Business Logic in `save()` Methods**

**Group.save() (lines 39-42):**
```python
def save(self, *args, **kwargs):
    if not self.invite_code:
        self.invite_code = secrets.token_urlsafe(12)[:16]
    super().save(*args, **kwargs)
```

**Problem:** Invite code generation should be in a service
**Impact:** Medium - Difficult to test, not reusable

---

**GroupMembership.save() (lines 84-87):**
```python
def save(self, *args, **kwargs):
    if self.group.owner_id == self.user_id:
        self.role = GroupRole.OWNER
    super().save(*args, **kwargs)
```

**Problem:**
- Business rule (owner auto-assignment) in `save()`
- ❌ **Queries in `save()`** - `self.group.owner_id` may trigger a query
- Should be enforced in service layer

---

**2. Business Methods on Models**

**Group.regenerate_invite_code() (lines 44-47):**
```python
def regenerate_invite_code(self):
    self.invite_code = secrets.token_urlsafe(12)[:16]
    self.save(update_fields=['invite_code', 'updated_at'])
    return self.invite_code
```

**Problem:**
- Business operation on model (better in service)
- ❌ **No transaction wrapper**
- ❌ **No uniqueness check** - could generate duplicate code (unlikely but possible)
- ❌ **Not concurrency-safe** - should use `select_for_update()`

---

**3. Query Methods on Models (Medium Severity)**

```python
def has_member(self, user):
    return self.memberships.filter(user=user).exists()

def get_user_role(self, user):
    try:
        return self.memberships.get(user=user).role
    except GroupMembership.DoesNotExist:
        return None

def is_admin(self, user):
    role = self.get_user_role(user)
    return role in [GroupRole.OWNER, GroupRole.ADMIN]
```

**Issues:**
- These are acceptable as domain methods
- ⚠️ But they cause N+1 queries when called in serializers
- Should be prefetched in services or querysets

---

### 2.5 Serializers – Validation & Transformation Layer ⚠️

**Best Practice:** "Serializers strictly for input validation and output formatting. Keep create()/update() minimal."

#### Issues in serializers.py:

**1. Query Logic in Serializers (N+1 Problem)**

**GroupSerializer (lines 55-64):**
```python
def get_member_count(self, obj):
    """Get number of members in the group."""
    return obj.memberships.count()  # ❌ Query in serializer

def get_user_role(self, obj):
    """Get current user's role in the group."""
    request = self.context.get('request')
    if request and request.user.is_authenticated:
        return obj.get_user_role(request.user)  # ❌ Query in serializer
    return None
```

**Problem:**
- Serializers perform database queries
- ⚠️ **N+1 problem** - When serializing 20 groups, makes 20+ extra queries
- Should use `annotate()` or `prefetch_related()` in view queryset

**Same issue in GroupListSerializer (line 94-95):**
```python
def get_member_count(self, obj):
    return obj.memberships.count()  # ❌ N+1 query
```

---

**2. SerializerMethodFields Performance**

**Impact:** When listing groups:
- 1 query for groups
- +N queries for member counts
- +N queries for user roles

**Solution:** Use queryset annotations:
```python
queryset = Group.objects.annotate(
    member_count=Count('memberships')
).select_related('owner')
```

---

### 2.6 Concurrency – Prevention and Handling ❌

**Best Practice:** "All critical concurrency guarantees must be enforced at the database level"

#### Major Concurrency Issues:

**1. Missing Transactions**

Only **1 of 8** state-changing operations has `@transaction.atomic`:

| Operation | Has Transaction? | Risk Level |
|-----------|------------------|------------|
| `perform_create()` | ✅ Yes | Low |
| `join()` | ❌ No | 🔴 High |
| `leave()` | ❌ No | 🟡 Medium |
| `regenerate_invite()` | ❌ No | 🟡 Medium |
| `update_member_role()` | ❌ No | 🔴 Critical |
| `remove_member()` | ❌ No | 🟡 Medium |
| `add_to_library()` | ❌ No | 🟡 Medium |
| Model `save()` methods | ❌ No | 🟡 Medium |

---

**2. Missing Row-Level Locking**

**Zero usage of `select_for_update()`** throughout the app.

**Critical Race Conditions:**

**A. Duplicate Membership (join action)**
```
Time    Request 1                       Request 2
----    ---------                       ---------
T1      Check: user not a member
T2                                      Check: user not a member
T3      Create membership
T4                                      Create membership ❌ DUPLICATE!
```

**Current code (views.py:126-138):**
```python
# Check if already a member
if group.has_member(request.user):  # ← Race condition here
    return Response({'error': 'You are already a member'}, ...)

# Add user as member
membership = GroupMembership.objects.create(...)  # ← Could create duplicate
```

**Why unique_together doesn't fully protect:**
- `IntegrityError` crashes the request instead of handling gracefully
- Service should use `select_for_update()` + explicit check

---

**B. Concurrent Role Changes**
```
Time    Admin 1                         Admin 2
----    -------                         -------
T1      Read: membership role = MEMBER
T2                                      Read: membership role = MEMBER
T3      Update: role = ADMIN
T4                                      Update: role = MEMBER  ❌ Lost update!
```

**Current code (views.py:226-243):**
```python
# Get membership (no locking)
membership = GroupMembership.objects.get(group=group, user_id=user_id)

# Check role
if membership.role == GroupRole.OWNER:
    return Response({'error': 'Cannot change owner role'}, ...)

# Update role (no transaction, no locking)
membership.role = new_role
membership.save(update_fields=['role'])  # ❌ Race condition
```

**Required fix:**
```python
@transaction.atomic
def update_member_role(...):
    membership = (
        GroupMembership.objects
        .select_for_update()  # ← Lock the row
        .get(group=group, user_id=user_id)
    )
    # ... rest of logic
```

---

**C. Invite Code Uniqueness Race**
```
Time    Request 1                       Request 2
----    ---------                       ---------
T1      Generate code: "abc123"
T2                                      Generate code: "abc123"  (unlikely but possible)
T3      Save group
T4                                      Save group  ❌ UNIQUE VIOLATION!
```

**Current code (models.py:44-47):**
```python
def regenerate_invite_code(self):
    self.invite_code = secrets.token_urlsafe(12)[:16]  # Not guaranteed unique
    self.save(update_fields=['invite_code', 'updated_at'])
    return self.invite_code
```

**Required fix:**
- Use `select_for_update()` to lock the group
- Handle `IntegrityError` and retry with new code

---

**3. Database Constraints**

**Good:** `unique_together` on GroupMembership prevents duplicate memberships at DB level

```python
class Meta:
    unique_together = [['user', 'group']]  # ✅ Good
```

**Missing:** No handling of `IntegrityError` when constraint is violated

---

### 2.7 Error Handling & Domain Exceptions ❌

**Best Practice:** "Define domain-specific exceptions. Never raise HTTP exceptions from services."

**Status:** ❌ **No domain exceptions exist**

**Current approach:**
- Using DRF's `PermissionDenied` directly in views
- Returning `Response(...)` with error messages inline
- No consistent error handling strategy

**Required exceptions:**
```python
# apps/groups/services/exceptions.py

class GroupsServiceError(Exception):
    """Base exception for groups services."""
    pass

class GroupNotFoundError(GroupsServiceError):
    pass

class InvalidInviteCodeError(GroupsServiceError):
    pass

class AlreadyMemberError(GroupsServiceError):
    pass

class NotMemberError(GroupsServiceError):
    pass

class OwnerCannotLeaveError(GroupsServiceError):
    pass

class CannotChangeOwnerRoleError(GroupsServiceError):
    pass

class CannotRemoveOwnerError(GroupsServiceError):
    pass

class DuplicateLibraryEntryError(GroupsServiceError):
    pass

class InsufficientPermissionsError(GroupsServiceError):
    pass
```

**Example of required refactor:**

**Current (views.py:155-159):**
```python
if group.owner == request.user:
    return Response(
        {'error': 'Group owner cannot leave...'},
        status=status.HTTP_400_BAD_REQUEST
    )
```

**Refactored:**
```python
# In service:
if group.owner == user:
    raise OwnerCannotLeaveError("Group owner cannot leave their group")

# In view:
try:
    leave_group(group_id=pk, user=request.user)
except OwnerCannotLeaveError as e:
    return Response({'error': str(e)}, status=400)
```

---

### 2.8 Permissions & Authorization ⚠️

**Best Practice:** "Use DRF permissions for access control. Keep permission logic declarative and reusable."

#### Issues:

**1. Permission Checks in View Methods ❌**

Found **4 instances** of permission checks inside view methods:

**Example 1 (views.py:183-187):**
```python
def regenerate_invite(self, request, pk=None):
    group = self.get_object()

    # ❌ Permission check in view method
    if not group.is_admin(request.user):
        raise PermissionDenied("Only admins can regenerate invite codes")
```

**Should be:**
```python
@action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupAdmin])
def regenerate_invite(self, request, pk=None):
    regenerate_group_invite(group_id=pk)
    # ...
```

---

**Example 2 (views.py:206-209):**
```python
def update_member_role(self, request, pk=None):
    # ❌ Permission check in view method
    if not group.is_admin(request.user):
        raise PermissionDenied("Only admins can update member roles")
```

---

**2. Good: Permission Classes Exist ✅**

The app **does have** good permission classes in `permissions.py`:

```python
class IsGroupAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.is_admin(request.user)

class IsGroupMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_member(request.user)

class IsGroupOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

**Problem:** These classes exist but are **not used consistently**. Only used in `get_permissions()` method for update/destroy, not for custom actions.

---

**3. Inconsistent Permission Enforcement**

| Action | Permission Enforcement | Correct? |
|--------|------------------------|----------|
| `update/partial_update` | ✅ `IsGroupAdmin` (in `get_permissions`) | ✅ |
| `destroy` | ✅ `IsGroupAdmin` (in `get_permissions`) | ✅ |
| `regenerate_invite` | ❌ Manual check in method | ❌ |
| `update_member_role` | ❌ Manual check in method | ❌ |
| `remove_member` | ❌ Manual check in method | ❌ |
| `library` | ❌ Manual check in method | ❌ |
| `add_to_library` | ❌ Manual check in method | ❌ |

---

### 2.9 Testing Strategy ⚠️

**Status:** Basic tests exist, but likely insufficient for concurrency

**Files:**
- `tests/conftest.py` - 4694 bytes (fixtures)
- `tests/test_api.py` - 20203 bytes (API tests)

**Likely gaps:**
- ❌ No concurrency tests (race condition scenarios)
- ❌ No service-level unit tests (since services don't exist)
- ⚠️ Probably only API integration tests

**Required additions after refactoring:**
- Unit tests for each service function
- Concurrency tests for critical operations
- Test for invite code uniqueness
- Test for duplicate membership handling

---

## 3. Summary of Issues

### Critical (Must Fix) 🔴

| Issue | Location | Impact | Best Practice Violated |
|-------|----------|--------|------------------------|
| No services layer | Entire app | Critical | §3 Services Layer |
| Business logic in views | views.py (~200 lines) | High | §2 Views - HTTP Layer |
| No domain exceptions | Entire app | High | §7 Error Handling |
| Missing transactions | 7 of 8 operations | Critical | §6.1 Transaction Management |
| No row-level locking | All state changes | Critical | §6.2 Row-Level Locking |
| Race condition: duplicate membership | views.py:104-143 | High | §6 Concurrency |
| Race condition: role updates | views.py:196-245 | Critical | §6 Concurrency |

### Important (Should Fix) 🟡

| Issue | Location | Impact | Best Practice Violated |
|-------|----------|--------|------------------------|
| Business logic in model save() | models.py:39-42, 84-87 | Medium | §4 Models |
| Permission checks in views | 4 locations | Medium | §8 Permissions |
| Query logic in serializers | serializers.py | Medium | §5 Serializers |
| N+1 query problem | GroupSerializer | Medium | Performance |
| Inconsistent permission usage | Custom actions | Medium | §8 Permissions |

### Minor (Nice to Have) 🟢

| Issue | Location | Impact | Best Practice Violated |
|-------|----------|--------|------------------------|
| Missing concurrency tests | tests/ | Low | §9 Testing |
| No service-level tests | tests/ | Low | §9 Testing |

---

## 4. Comparison with Refactored Apps

### vs. Accounts App (Refactored) ✅

| Aspect | Groups App | Accounts App | Gap |
|--------|------------|--------------|-----|
| Services layer | ❌ None | ✅ Modular services | Critical |
| Transaction safety | ❌ 12.5% wrapped | ✅ 100% wrapped | Critical |
| Concurrency protection | ❌ 0% | ✅ 100% where needed | Critical |
| Domain exceptions | ❌ None | ✅ Complete hierarchy | High |
| Views thickness | ❌ ~200 lines business logic | ✅ Thin (5-10 lines) | High |
| Permission enforcement | ⚠️ Inconsistent | ✅ Consistent | Medium |

### vs. Beans App (Refactored) ✅

| Aspect | Groups App | Beans App | Gap |
|--------|------------|-----------|-----|
| Services layer | ❌ None | ✅ 6 service modules | Critical |
| Transaction safety | ❌ 12.5% | ✅ 100% | Critical |
| Row-level locking | ❌ 0% | ✅ On critical ops | Critical |
| Domain exceptions | ❌ None | ✅ 6 exception types | High |
| Business logic separation | ❌ Scattered | ✅ Centralized | High |

**Conclusion:** Groups app is in **pre-refactored state**, similar to where accounts and beans were before refactoring.

---

## 5. Required Refactoring

### 5.1 Service Layer Structure

```
apps/groups/services/
├── __init__.py                   # Service exports
├── exceptions.py                 # 9 domain exceptions
├── group_management.py           # create, update, delete group
├── membership_management.py      # join, leave, remove member
├── role_management.py            # update member role
├── invite_management.py          # regenerate invite, validate
└── library_management.py         # add to library, pin entries
```

### 5.2 Transaction Safety Plan

**Operations requiring `@transaction.atomic` + `select_for_update()`:**

1. ✅ `create_group()` - Already has transaction
2. ❌ `join_group()` - Add transaction + lock group
3. ❌ `leave_group()` - Add transaction + lock membership
4. ❌ `remove_member()` - Add transaction + lock membership
5. ❌ `update_member_role()` - Add transaction + lock membership
6. ❌ `regenerate_invite_code()` - Add transaction + lock group
7. ❌ `add_to_library()` - Add transaction
8. ❌ Model `save()` refactor - Remove business logic

### 5.3 Views Refactoring

**Each view method should follow this pattern:**

```python
def action_name(self, request, pk=None):
    """Thin HTTP handler."""
    serializer = InputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = service_function(
            param=serializer.validated_data['param'],
            user=request.user
        )
    except DomainError as e:
        return Response({'error': str(e)}, status=400)

    output = OutputSerializer(result)
    return Response(output.data, status=201)
```

**Expected reduction:** ~200 lines → ~80 lines in views

---

## 6. Refactoring Priority

### Phase 1: Foundation (2-3 hours)
1. Create services directory structure
2. Define domain exceptions
3. Create group_management.py service
4. Refactor group creation with transactions

### Phase 2: Membership Operations (2-3 hours)
1. Create membership_management.py
2. Implement join_group with concurrency protection
3. Implement leave_group, remove_member
4. Add IntegrityError handling

### Phase 3: Role & Invite Management (1-2 hours)
1. Create role_management.py
2. Implement update_member_role with row locking
3. Create invite_management.py
4. Implement regenerate_invite with uniqueness handling

### Phase 4: Library Management (1 hour)
1. Create library_management.py
2. Implement add_to_library, remove_from_library
3. Implement pin/unpin functionality

### Phase 5: View Refactoring (2-3 hours)
1. Update all view methods to use services
2. Remove business logic from views
3. Ensure consistent permission usage
4. Add domain exception handlers

### Phase 6: Model Cleanup (1 hour)
1. Remove business logic from save() methods
2. Keep domain query methods (has_member, etc.)
3. Ensure models are pure domain objects

### Phase 7: Documentation & Testing (1-2 hours)
1. Document services layer in app context
2. Add concurrency tests
3. Add service unit tests

**Total Estimated Time:** 10-15 hours (1.5-2 days)

---

## 7. Risk Assessment

### High Risk Areas

1. **Membership race conditions** - Could create duplicate memberships
2. **Role change race conditions** - Could lose updates or apply incorrect roles
3. **Invite code uniqueness** - Low probability but possible collision
4. **No transaction rollback** - Partial operations could leave inconsistent state

### Migration Risk

- ✅ **Low schema changes** - Models are already well-designed
- ✅ **No data migration needed** - Refactoring is code-only
- ⚠️ **API contract may change slightly** - Error responses will be more consistent

---

## 8. Benefits of Refactoring

### Code Quality
- 📉 **Views: 378 lines → ~150 lines** (60% reduction in business logic)
- 📈 **Testability:** Services can be unit tested independently
- 📈 **Reusability:** Services can be called from management commands, tasks, etc.

### Safety
- ✅ **Transaction safety:** All operations atomic
- ✅ **Concurrency protection:** No race conditions
- ✅ **Consistent error handling:** Clear, predictable errors

### Maintainability
- ✅ **Clear separation of concerns:** Each layer has one responsibility
- ✅ **Easier debugging:** Business logic isolated in services
- ✅ **Better code review:** Smaller, focused functions

### Performance
- ✅ **Eliminate N+1 queries:** Proper prefetching in services
- ✅ **Reduced deadlock risk:** Explicit locking strategy

---

## 9. Conclusion

The groups app requires **comprehensive refactoring** to align with DRF best practices. While the current code is functional, it has critical issues with:

- ❌ Architecture (no services layer)
- ❌ Transaction safety (87.5% of operations unprotected)
- ❌ Concurrency (multiple race conditions)
- ❌ Separation of concerns (business logic in views)

**Recommendation:** Proceed with refactoring using the 7-phase plan outlined above.

**Priority:** 🔴 High - The lack of transaction safety and concurrency protection could lead to data corruption in production under load.

---

**Next Steps:**
1. Review this analysis with the team
2. Approve the refactoring plan
3. Begin with Phase 1 (Foundation)
4. Test thoroughly after each phase
