# Reviews App - Application Context

> **Last Updated:** 2025-12-14
> **Owner:** Filip Prudek
> **Status:** Development

---

## Purpose & Responsibility

Manages user reviews/ratings of coffee beans, taste tags, and personal coffee libraries. Automatically maintains user libraries and triggers aggregate rating updates on beans.

**Core Responsibility:**
- User reviews with 1-5 star ratings and detailed scores
- Taste tag system for flavor profiling
- User's personal coffee library management
- Auto-create library entry on first review
- Maintain aggregate ratings on CoffeeBean
- Review statistics and bean summaries

**NOT Responsible For:**
- Coffee bean catalog (that's `beans` app)
- Group libraries (that's `groups` app)
- Purchase tracking (that's `purchases` app)
- User authentication (that's `accounts` app)

---

## Models

### **Review**

**Purpose:** Captures user's opinion and rating of a specific coffee bean.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `coffeebean` | FK(CoffeeBean) | What's being reviewed | Required, CASCADE |
| `author` | FK(User) | Who wrote it | Required, CASCADE |
| `rating` | PositiveSmallInt | Overall score | 1-5, required |
| `aroma_score` | PositiveSmallInt | Aroma rating | 1-5, optional |
| `flavor_score` | PositiveSmallInt | Flavor rating | 1-5, optional |
| `acidity_score` | PositiveSmallInt | Acidity rating | 1-5, optional |
| `body_score` | PositiveSmallInt | Body rating | 1-5, optional |
| `aftertaste_score` | PositiveSmallInt | Aftertaste rating | 1-5, optional |
| `notes` | TextField | Written review | Optional |
| `brew_method` | CharField(50) | How coffee was brewed | Optional |
| `taste_tags` | M2M(Tag) | Flavor descriptors | Optional |
| `context` | CharField(20) | personal/group/public | Default: personal |
| `group` | FK(Group) | If group review | Required if context='group' |
| `would_buy_again` | BooleanField | Purchase intent | Optional |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |
| `updated_at` | DateTimeField | Last update | Auto-set |

**Enum Choices:**
```python
class ReviewContext(models.TextChoices):
    PERSONAL = 'personal', 'Personal'
    GROUP = 'group', 'Group/Team'
    PUBLIC = 'public', 'Public'
```

**Relationships:**
- **Belongs To:** CoffeeBean (many reviews -> one bean)
- **Belongs To:** User (many reviews -> one author)
- **Belongs To:** Group (optional, for group reviews)
- **Many-to-Many:** Tag (for taste profiling)

**Business Rules:**
1. **Unique Review:** One review per `(author, coffeebean)` - enforced by unique_together
2. **Group Validation:** If context='group', must provide group AND user must be member
3. **Rating Range:** Must be 1-5 (enforced by validators)
4. **Auto Library:** On create, calls `UserLibraryEntry.ensure_entry(user, bean, 'review')`
5. **Aggregate Update:** On create/update/delete, triggers `bean.update_aggregate_rating()` via `transaction.on_commit()`

**Indexes:**
- `(coffeebean, rating)` - For filtering by rating
- `(author, created_at)` - For user's review timeline
- `(group, created_at)` - For group feed
- `created_at` - For recent reviews

---

### **Tag**

**Purpose:** Taste descriptors for categorizing coffee flavors.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `name` | CharField(50) | Tag name | Required, unique |
| `category` | CharField(50) | Tag category | Optional |
| `created_at` | DateTimeField | Creation timestamp | Auto-set |

**Relationships:**
- **Many-to-Many:** Review (via `reviews`)

**Business Rules:**
1. **Unique Name:** Tag names must be unique

---

### **UserLibraryEntry**

**Purpose:** User's personal coffee library for tracking tried/saved beans.

**Fields:**
| Field | Type | Purpose | Business Rule |
|-------|------|---------|---------------|
| `id` | UUIDField (PK) | Unique identifier | Auto-generated |
| `user` | FK(User) | Library owner | Required, CASCADE |
| `coffeebean` | FK(CoffeeBean) | Coffee bean | Required, CASCADE |
| `added_by` | CharField(20) | How added | review/purchase/manual |
| `added_at` | DateTimeField | Add timestamp | Auto-set |
| `own_price_czk` | Decimal(10,2) | Custom price | Optional |
| `is_archived` | BooleanField | Archive flag | Default: False |

**Key Methods:**
```python
@classmethod
def ensure_entry(cls, user, coffeebean, added_by='review'):
    """Idempotent method to create or get library entry."""
    entry, created = cls.objects.get_or_create(
        user=user,
        coffeebean=coffeebean,
        defaults={'added_by': added_by}
    )
    return entry, created
```

**Business Rules:**
1. **Unique Entry:** One entry per `(user, coffeebean)`
2. **Idempotent Creation:** `ensure_entry()` uses get_or_create
3. **Archive vs Delete:** Users can archive entries instead of deleting

**Indexes:**
- `(user, added_at)` - For user's library timeline
- `(user, is_archived)` - For filtering archived entries

---

## API Endpoints

### Review CRUD

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/reviews/` | List reviews (filtered) | Optional | IsAuthenticatedOrReadOnly |
| POST | `/api/reviews/` | Create review | Required | IsAuthenticated |
| GET | `/api/reviews/{id}/` | Get review details | Optional | IsAuthenticatedOrReadOnly |
| PUT | `/api/reviews/{id}/` | Full update | Required | IsReviewAuthor |
| PATCH | `/api/reviews/{id}/` | Partial update | Required | IsReviewAuthor |
| DELETE | `/api/reviews/{id}/` | Delete review | Required | IsReviewAuthor |
| GET | `/api/reviews/my_reviews/` | Current user's reviews | Required | IsAuthenticated |
| GET | `/api/reviews/statistics/` | Review statistics | Optional | Public |
| GET | `/api/reviews/bean/{id}/summary/` | Bean review summary | Optional | Public |

**Query Parameters for List:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `coffeebean` | UUID | Filter by coffee bean |
| `author` | UUID | Filter by author |
| `group` | UUID | Filter by group |
| `rating` | int | Filter by exact rating |
| `min_rating` | int | Filter by minimum rating |
| `context` | string | Filter by context (personal/group/public) |
| `search` | string | Search in notes, bean name, roastery |
| `tag` | UUID | Filter by taste tag |

### User Library

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/reviews/library/` | Get user's library | Required | IsAuthenticated |
| POST | `/api/reviews/library/add/` | Add bean to library | Required | IsAuthenticated |
| PATCH | `/api/reviews/library/{id}/archive/` | Archive/unarchive | Required | IsLibraryOwner |
| DELETE | `/api/reviews/library/{id}/` | Remove from library | Required | IsLibraryOwner |

**Library Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `archived` | bool | Show archived entries (default: false) |
| `search` | string | Search in bean name or roastery |

### Tags

| Method | Endpoint | Purpose | Auth | Permissions |
|--------|----------|---------|------|-------------|
| GET | `/api/reviews/tags/` | List all tags | Optional | Public |
| GET | `/api/reviews/tags/{id}/` | Get tag details | Optional | Public |
| GET | `/api/reviews/tags/popular/` | Get popular tags | Optional | Public |
| POST | `/api/reviews/tags/create/` | Create new tag | Required | IsAuthenticated |

---

## Business Logic & Workflows

### **Workflow 1: Review Creation**

**Trigger:** POST to `/api/reviews/`

**Steps:**
1. Validate required fields (coffeebean, rating 1-5)
2. Check no existing review for `(user, bean)` - unique constraint
3. If context='group', validate user is member of group
4. **Transaction Start**
5. Create review with author = current user
6. Call `UserLibraryEntry.ensure_entry(user, bean, 'review')`
7. **Transaction Commit**
8. **On Commit:** Trigger `bean.update_aggregate_rating()`

**Code:**
```python
@transaction.atomic
def perform_create(self, serializer):
    review = serializer.save(author=self.request.user)

    # Auto-create library entry
    UserLibraryEntry.ensure_entry(
        user=self.request.user,
        coffeebean=review.coffeebean,
        added_by='review'
    )

    # Update aggregate rating (after commit)
    transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
```

**Edge Cases:**
- Duplicate review: Returns 400 (serializer validation)
- Non-member group review: Returns 400
- Invalid rating: Returns 400
- Library already exists: `ensure_entry()` is idempotent

### **Workflow 2: Review Update**

**Trigger:** PATCH/PUT to `/api/reviews/{id}/`

**Steps:**
1. Verify user is review author (permission check)
2. Validate updated fields
3. Save changes
4. **On Commit:** Trigger `bean.update_aggregate_rating()`

**Code:**
```python
@transaction.atomic
def perform_update(self, serializer):
    review = serializer.save()
    transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
```

### **Workflow 3: Review Deletion**

**Trigger:** DELETE to `/api/reviews/{id}/`

**Steps:**
1. Verify user is review author
2. Store reference to coffeebean
3. Delete review
4. **On Commit:** Trigger `bean.update_aggregate_rating()`

**Important:** Library entry is NOT deleted when review is deleted.

**Code:**
```python
@transaction.atomic
def perform_destroy(self, instance):
    coffeebean = instance.coffeebean
    instance.delete()
    transaction.on_commit(lambda: coffeebean.update_aggregate_rating())
```

### **Workflow 4: Add to Library (Manual)**

**Trigger:** POST to `/api/reviews/library/add/`

**Steps:**
1. Validate coffeebean_id exists and is active
2. Call `UserLibraryEntry.ensure_entry(user, bean, 'manual')`
3. Return 201 if created, 200 if already existed

---

## Permissions & Security

**Permission Classes:**
```python
class IsReviewAuthorOrReadOnly(BasePermission):
    """Only review author can edit/delete. Anyone can read."""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user

class IsLibraryOwner(BasePermission):
    """Only library entry owner can modify it."""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

**Access Rules:**
| Action | Who Can Do It |
|--------|---------------|
| View reviews | Everyone (public) |
| Create review | Authenticated users |
| Update review | Author only |
| Delete review | Author only |
| View library | Owner only |
| Modify library | Owner only |

**Security Considerations:**
- Library endpoints filter by current user (can't see others' libraries)
- Review author check in permission class
- Group membership validated in serializer for group reviews
- One review per bean per user enforced by unique constraint

---

## Testing Strategy

**What to Test:**
1. Review CRUD operations
2. Duplicate review prevention
3. Auto-library creation on review
4. Aggregate rating updates
5. Library operations (add, archive, remove)
6. Tag operations
7. Permission enforcement

**Test Coverage:** 50+ test cases in `apps/reviews/tests/test_api.py`

**Critical Test Cases:**
```python
def test_create_review_auto_creates_library_entry(self, review_auth_client, review_another_coffeebean, review_user):
    """Creating review auto-creates library entry."""
    data = {'coffeebean': str(review_another_coffeebean.id), 'rating': 4}
    response = review_auth_client.post(url, data)

    assert response.status_code == 201
    assert UserLibraryEntry.objects.filter(
        user=review_user,
        coffeebean=review_another_coffeebean
    ).exists()

def test_create_review_duplicate_forbidden(self, review_auth_client, review_coffeebean, review):
    """Cannot create duplicate review for same bean."""
    data = {'coffeebean': str(review_coffeebean.id), 'rating': 3}
    response = review_auth_client.post(url, data)

    assert response.status_code == 400
    assert 'already reviewed' in str(response.data).lower()

def test_delete_own_review(self, review_auth_client, review):
    """Author can delete their review."""
    response = review_auth_client.delete(url)

    assert response.status_code == 204
    assert not Review.objects.filter(id=review.id).exists()
```

---

## Dependencies & Relationships

**This App Uses:**
- `accounts.User` - For author reference
- `beans.CoffeeBean` - For review target, calls `update_aggregate_rating()`
- `groups.Group` - For group context reviews

**Used By:**
- `analytics` - Review data for statistics
- `purchases` - May trigger library entry creation

**External Services:**
- None

---

## Common Patterns

**Pattern 1: Transaction-Safe Aggregate Update**
```python
@transaction.atomic
def perform_create(self, serializer):
    review = serializer.save(author=self.request.user)

    # Library entry inside transaction
    UserLibraryEntry.ensure_entry(user, coffeebean, 'review')

    # Aggregate update AFTER commit
    transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
```

**When to Use:** All review create/update/delete operations

**Pattern 2: Idempotent Library Entry**
```python
entry, created = UserLibraryEntry.ensure_entry(user, coffeebean, added_by)
# Returns existing entry if already exists
```

**When to Use:** When adding to library from review, purchase, or manual add

**Pattern 3: Owner-Filtered QuerySet**
```python
# In library views - user can only see their own entries
entry = UserLibraryEntry.objects.get(id=entry_id, user=request.user)
```

**When to Use:** All library operations

---

## Gotchas & Known Issues

**Issue 1: Library Persists After Review Delete**
- **Symptom:** Deleting review doesn't remove library entry
- **Cause:** By design - library is independent of reviews
- **Workaround:** User can manually remove from library
- **Status:** By design

**Issue 2: Aggregate Rating Update Timing**
- **Symptom:** `avg_rating` may not reflect immediately in tests
- **Cause:** `transaction.on_commit()` doesn't execute in test transactions
- **Workaround:** Use `TransactionTestCase` or mock the callback
- **Status:** Known limitation of Django testing

**Issue 3: Tag Moderation**
- **Symptom:** Any authenticated user can create tags
- **Cause:** No approval workflow implemented
- **Workaround:** Admin can delete inappropriate tags
- **Status:** TODO - Consider tag approval or admin-only creation

---

## Future Enhancements

**Planned:**
- [ ] Review helpful/unhelpful voting
- [ ] Review comments/replies
- [ ] Photo attachments for reviews
- [ ] Review version history

**Ideas:**
- [ ] AI-suggested tags based on review text
- [ ] Review verification (verified purchase)
- [ ] Expert reviewer badges

**Won't Do (and Why):**
- Anonymous reviews - Accountability is important for quality
- Editing window limits - Trust users to update reviews fairly

---

## Services Layer Architecture

> **Refactored:** December 2024 - Business logic extracted from models, views, and serializers into dedicated services layer following DRF best practices.

### **Overview**

The reviews app implements a comprehensive services layer that centralizes all business logic, providing:

- **Transaction Safety**: All state-changing operations wrapped in `@transaction.atomic`
- **Concurrency Protection**: Row-level locking with `select_for_update()` for critical updates
- **Domain Exceptions**: Specific error types for clear error handling
- **Type Safety**: Full type hints throughout all service functions
- **Separation of Concerns**: Views are thin HTTP handlers, services contain business logic
- **DRY Principle**: Business logic centralized, not scattered across layers

### **Service Modules**

All services located in `apps/reviews/services/`:

| Module | Purpose | Key Functions | Lines |
|--------|---------|---------------|-------|
| `review_management.py` | Review CRUD operations | create_review, get_review_by_id, update_review, delete_review, get_user_reviews | 364 |
| `library_management.py` | User library operations | add_to_library, remove_from_library, archive_library_entry, get_user_library | 181 |
| `tag_management.py` | Tag operations | create_tag, get_tag_by_id, get_popular_tags, search_tags | 106 |
| `statistics.py` | Analytics & aggregations | get_review_statistics, get_bean_review_summary | 166 |
| `exceptions.py` | Domain exceptions | ReviewNotFoundError, DuplicateReviewError, etc. | 52 |

**Total:** 15 service functions, ~870 lines of clean, testable business logic.

### **Domain Exceptions**

```python
# Base exception
class ReviewsServiceError(Exception):
    """Base exception for all reviews service errors."""

# Specific exceptions
class ReviewNotFoundError(ReviewsServiceError)         # Review doesn't exist or inaccessible
class DuplicateReviewError(ReviewsServiceError)        # User already reviewed this bean
class InvalidRatingError(ReviewsServiceError)          # Rating not in 1-5 range
class BeanNotFoundError(ReviewsServiceError)           # Coffee bean not found or inactive
class LibraryEntryNotFoundError(ReviewsServiceError)   # Library entry doesn't exist
class TagNotFoundError(ReviewsServiceError)            # Tag doesn't exist
class UnauthorizedReviewActionError(ReviewsServiceError) # User cannot modify review
class InvalidContextError(ReviewsServiceError)          # Invalid review context
class GroupMembershipRequiredError(ReviewsServiceError) # Must be group member
```

### **Transaction Safety Patterns**

All state-changing operations use `@transaction.atomic` to ensure data consistency:

**Pattern 1: Atomic Review Creation**
```python
@transaction.atomic
def create_review(
    *,
    author: User,
    coffeebean_id: UUID,
    rating: int,
    # ... other fields
) -> Review:
    """Create a new review with validation and tag association."""
    # 1. Validate rating
    if not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    # 2. Validate coffee bean exists
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # 3. Check for duplicate review (one review per user-bean pair)
    existing = Review.objects.filter(author=author, coffeebean=coffeebean).exists()
    if existing:
        raise DuplicateReviewError("You have already reviewed this coffee bean")

    # 4. Create review
    try:
        review = Review.objects.create(
            coffeebean=coffeebean,
            author=author,
            rating=rating,
            # ... other fields
        )
    except IntegrityError:
        # Database unique constraint caught duplicate
        raise DuplicateReviewError("You have already reviewed this coffee bean")

    # 5. Associate taste tags atomically
    if taste_tag_ids:
        tags = Tag.objects.filter(id__in=taste_tag_ids)
        review.taste_tags.set(tags)

    return review
```

**Key Features:**
- All validation and creation in single transaction
- Either everything succeeds or everything rolls back
- IntegrityError provides safety net for race conditions
- Tags associated atomically with review

**Pattern 2: Atomic Library Addition (Idempotent)**
```python
@transaction.atomic
def add_to_library(
    *,
    user: User,
    coffeebean_id: UUID,
    added_by: str = 'manual'
) -> tuple[UserLibraryEntry, bool]:
    """Add coffee bean to user's library (idempotent)."""
    # Validate coffee bean
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Get or create library entry (idempotent)
    try:
        entry, created = UserLibraryEntry.objects.get_or_create(
            user=user,
            coffeebean=coffeebean,
            defaults={'added_by': added_by}
        )
    except IntegrityError:
        # Rare race condition: entry created between get and create
        entry = UserLibraryEntry.objects.get(user=user, coffeebean=coffeebean)
        created = False

    return entry, created
```

**Key Features:**
- Idempotent operation (safe to retry)
- IntegrityError handles race conditions gracefully
- Returns tuple indicating if entry was created or already existed

### **Concurrency Protection Strategies**

Critical operations use `select_for_update()` to prevent race conditions:

**Strategy 1: Preventing Lost Updates on Review Modifications**
```python
@transaction.atomic
def update_review(
    *,
    review_id: UUID,
    user: User,
    rating: Optional[int] = None,
    # ... other fields
) -> Review:
    """Update review with row-level locking."""
    # Get review with row lock
    try:
        review = (
            Review.objects
            .select_for_update()  # ← Row-level lock prevents lost updates
            .get(id=review_id)
        )
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    # Check authorization
    if review.author != user:
        raise UnauthorizedReviewActionError("You can only update your own reviews")

    # Validate rating if provided
    if rating is not None and not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    # Update fields
    if rating is not None:
        review.rating = rating
    # ... update other fields

    review.save()
    return review
```

**Why This Works:**
- `select_for_update()` locks the review row until transaction commits
- Concurrent updates will serialize (wait for lock to release)
- No lost updates - all changes are applied correctly
- Authorization checked within locked transaction

**Strategy 2: Preventing Duplicate Reviews (Race Condition)**
```python
# In create_review():
@transaction.atomic
def create_review(...):
    # 1. Check for existing review (defensive)
    existing = Review.objects.filter(author=author, coffeebean=coffeebean).exists()
    if existing:
        raise DuplicateReviewError(...)

    # 2. Create review with IntegrityError catch
    try:
        review = Review.objects.create(...)
    except IntegrityError:
        # Database unique constraint caught duplicate from race condition
        raise DuplicateReviewError(...)
```

**Why This Works:**
- Database unique constraint on `(author, coffeebean)` provides ultimate safety
- Early check prevents most duplicates (performance optimization)
- IntegrityError catch handles rare race conditions where two requests slip through
- No duplicate reviews possible

**Strategy 3: Concurrent Library Modifications**
```python
@transaction.atomic
def archive_library_entry(
    *,
    entry_id: UUID,
    user: User,
    is_archived: bool = True
) -> UserLibraryEntry:
    """Archive/unarchive library entry with locking."""
    # Get entry with row lock
    try:
        entry = (
            UserLibraryEntry.objects
            .select_for_update()  # ← Lock during modification
            .get(id=entry_id, user=user)
        )
    except UserLibraryEntry.DoesNotExist:
        raise LibraryEntryNotFoundError(
            "Library entry not found or does not belong to you"
        )

    entry.is_archived = is_archived
    entry.save(update_fields=['is_archived'])
    return entry
```

**Why This Works:**
- Row-level lock prevents concurrent archive/unarchive operations
- Ensures final state is deterministic
- Authorization check within locked transaction

### **Service Usage Examples**

**Example 1: Creating a Review (View Layer)**
```python
from apps.reviews.services import create_review, add_to_library
from apps.reviews.services.exceptions import (
    DuplicateReviewError,
    BeanNotFoundError,
    InvalidRatingError,
)

class ReviewViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        """Create review using service layer."""
        try:
            review = create_review(
                author=self.request.user,
                coffeebean_id=serializer.validated_data['coffeebean'].id,
                rating=serializer.validated_data['rating'],
                notes=serializer.validated_data.get('notes', ''),
                taste_tag_ids=[tag.id for tag in serializer.validated_data.get('taste_tags', [])]
            )

            # Auto-add to library
            add_to_library(
                user=self.request.user,
                coffeebean_id=review.coffeebean.id,
                added_by='review'
            )

            # Update aggregate rating (asynchronous)
            transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())

        except (DuplicateReviewError, BeanNotFoundError, InvalidRatingError) as e:
            raise ValidationError(str(e))

        serializer.instance = review
```

**Example 2: Getting Statistics (Action Method)**
```python
from apps.reviews.services import get_review_statistics

@action(detail=False, methods=['get'])
def statistics(self, request):
    """Get review statistics using service layer."""
    user_id = request.query_params.get('user_id')
    bean_id = request.query_params.get('bean_id')

    # Call service
    data = get_review_statistics(
        user_id=user_id,
        bean_id=bean_id
    )

    serializer = ReviewStatisticsSerializer(data)
    return Response(serializer.data)
```

**Example 3: Managing Library (Function-Based View)**
```python
from apps.reviews.services import add_to_library
from apps.reviews.services.exceptions import BeanNotFoundError

@api_view(['POST'])
def add_to_library_view(request):
    """Add coffee bean to user's library."""
    try:
        entry, created = add_to_library(
            user=request.user,
            coffeebean_id=request.data['coffeebean_id'],
            added_by='manual'
        )

        serializer = UserLibraryEntrySerializer(entry)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    except BeanNotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
```

### **Benefits of Services Layer**

**Before Refactoring:**
- Business logic scattered across views, serializers, and models
- 0% concurrency protection
- 42.8% transaction safety (3/7 operations)
- ~150 lines of business logic in views
- ~90 lines of business logic in serializers
- Race conditions possible (3 identified)
- ~485 lines of code in views.py with mixed concerns

**After Refactoring:**
- All business logic centralized in services (~870 lines)
- 100% concurrency protection for critical operations
- 100% transaction safety for state-changing operations
- Views reduced to 296 lines (39% reduction)
- Serializers reduced to 224 lines (28% reduction, 49 lines removed)
- Views are thin HTTP handlers only (parse request → call service → return response)
- Serializers are validation-only (no create/update methods)
- Models are clean domain objects (no orchestration logic)
- Zero race conditions possible
- Easier to test (services are pure functions)
- Better type safety with full type hints
- Clear error handling with domain exceptions

### **Testing Services**

**Unit Test Example:**
```python
from apps.reviews.services import create_review
from apps.reviews.services.exceptions import DuplicateReviewError

def test_cannot_review_bean_twice(user, coffeebean):
    """User cannot create duplicate review for same bean."""
    # Create first review
    review = create_review(
        author=user,
        coffeebean_id=coffeebean.id,
        rating=5
    )
    assert review.id is not None

    # Try to create duplicate
    with pytest.raises(DuplicateReviewError) as exc:
        create_review(
            author=user,
            coffeebean_id=coffeebean.id,
            rating=4
        )

    assert "already reviewed" in str(exc.value)
```

**Concurrency Test Example:**
```python
import threading
from django.test import TransactionTestCase
from apps.reviews.services import create_review
from apps.reviews.services.exceptions import DuplicateReviewError

class TestConcurrency(TransactionTestCase):
    def test_concurrent_review_creation_prevented(self):
        """Multiple concurrent reviews for same (user, bean) should fail."""
        results = []
        errors = []

        def create_in_thread():
            try:
                review = create_review(
                    author=self.user,
                    coffeebean_id=self.bean.id,
                    rating=5
                )
                results.append(review)
            except DuplicateReviewError:
                errors.append(True)

        # Spawn 5 threads trying to create review simultaneously
        threads = [
            threading.Thread(target=create_in_thread)
            for _ in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify: exactly one review created, four duplicates rejected
        assert len(results) == 1
        assert len(errors) == 4

        # Verify: only one review exists in database
        from apps.reviews.models import Review
        assert Review.objects.filter(
            author=self.user,
            coffeebean=self.bean
        ).count() == 1
```

**Statistics Test Example:**
```python
from apps.reviews.services import get_review_statistics

def test_review_statistics_calculation(user, coffeebeans):
    """Statistics service correctly aggregates review data."""
    # Create multiple reviews
    for i, bean in enumerate(coffeebeans[:3]):
        create_review(
            author=user,
            coffeebean_id=bean.id,
            rating=i + 3  # Ratings: 3, 4, 5
        )

    # Get statistics
    stats = get_review_statistics(user_id=user.id)

    # Verify
    assert stats['total_reviews'] == 3
    assert stats['avg_rating'] == 4.0
    assert stats['rating_distribution']['3'] == 1
    assert stats['rating_distribution']['4'] == 1
    assert stats['rating_distribution']['5'] == 1
```

---

## Related Documentation

- [API Reference](../API.md#reviews-endpoints)
- [Database Schema](../DATABASE.md)
- Other App Contexts: [accounts](./accounts.md), [beans](./beans.md), [groups](./groups.md)

---

## Notes for Developers

> **Why One Review Per Bean?**
> Users should update their existing review rather than create multiple reviews. This keeps the aggregate rating meaningful and the review history clean.

> **Why Library Persists After Review Delete?**
> Library represents "beans I've tried" which is independent of having a review. Users may want to track beans without reviewing them.

> **Why transaction.on_commit for Aggregates?**
> Prevents querying uncommitted data. The aggregate calculation needs to see the committed review data to be accurate.

---

## AI Assistant Context

**When modifying this app, ALWAYS remember:**

1. **NEVER delete UserLibraryEntry when deleting Review**
   - Library persists independently of reviews
   - Users might want to keep beans in library even without review

2. **ALWAYS use transaction.atomic for review operations**
   - Review creation involves multiple database operations
   - Must be atomic to prevent inconsistencies

3. **ALWAYS update aggregate rating on review changes**
   - Use `transaction.on_commit()` not direct call
   - Prevents querying uncommitted data

4. **ALWAYS validate group membership for group reviews**
   - Check in serializer: `group.has_member(user)`
   - Return 400 if not member

5. **ALWAYS check author permission for review modifications**
   - Use `IsReviewAuthorOrReadOnly` permission class
   - Returns 403 for non-authors

**Typical Prompts:**

```
"Add a field to track brew temperature"
-> Steps:
1. Add field to Review model
2. Add migration
3. Add field to ReviewSerializer
4. Add field to ReviewCreateSerializer
5. Update API docs
6. Add test case

"Fix N+1 queries on review list"
-> Solution:
queryset = Review.objects.select_related(
    'author', 'coffeebean', 'group'
).prefetch_related('taste_tags')

"Allow users to edit their reviews"
-> Already implemented! Check:
- IsReviewAuthorOrReadOnly permission
- perform_update triggers aggregate update
- Use PATCH for partial updates
```
