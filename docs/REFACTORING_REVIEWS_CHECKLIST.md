# Reviews App - Refactoring Checklist

> **Created:** 2025-12-17
> **App:** `apps/reviews`
> **Reference:** [REVIEWS_APP_ANALYSIS.md](./REVIEWS_APP_ANALYSIS.md)
> **Pattern:** Following groups app refactoring approach

---

## Overview

This checklist provides a **step-by-step plan** to refactor the reviews app following DRF best practices. The refactoring extracts business logic from views/serializers into a clean services layer with proper transaction safety and concurrency protection.

**Total Phases:** 10
**Estimated Time:** 14-16 hours
**Difficulty:** Medium (similar to groups app)

---

## Phase 1: Setup Services Directory Structure

**Time:** 30 minutes
**Goal:** Create foundation for services layer

### Tasks

1. Create services directory structure:
```bash
mkdir -p apps/reviews/services
touch apps/reviews/services/__init__.py
touch apps/reviews/services/review_management.py
touch apps/reviews/services/library_management.py
touch apps/reviews/services/tag_management.py
touch apps/reviews/services/statistics.py
touch apps/reviews/services/exceptions.py
```

2. Create domain exceptions in `exceptions.py`:

```python
"""Domain exceptions for reviews app."""


class ReviewsServiceError(Exception):
    """Base exception for all reviews service errors."""
    pass


class ReviewNotFoundError(ReviewsServiceError):
    """Review does not exist or is inaccessible."""
    pass


class DuplicateReviewError(ReviewsServiceError):
    """User already reviewed this coffee bean."""
    pass


class InvalidRatingError(ReviewsServiceError):
    """Rating must be between 1 and 5."""
    pass


class BeanNotFoundError(ReviewsServiceError):
    """Coffee bean does not exist or is inactive."""
    pass


class LibraryEntryNotFoundError(ReviewsServiceError):
    """Library entry does not exist or belongs to another user."""
    pass


class TagNotFoundError(ReviewsServiceError):
    """Tag does not exist."""
    pass


class UnauthorizedReviewActionError(ReviewsServiceError):
    """User cannot modify this review."""
    pass


class InvalidContextError(ReviewsServiceError):
    """Invalid review context or missing required fields."""
    pass


class GroupMembershipRequiredError(ReviewsServiceError):
    """User must be group member to create group review."""
    pass
```

3. Create stub files for service modules with docstrings

4. Create `__init__.py` to export all services:

```python
"""
Reviews services - Business logic layer.

This package contains all business operations for the reviews app:
- Review CRUD operations
- User library management
- Tag management
- Statistics and analytics
"""

# Will be uncommented as each phase is completed:

# from .review_management import (
#     create_review,
#     get_review_by_id,
#     update_review,
#     delete_review,
#     get_user_reviews,
# )

# from .library_management import (
#     add_to_library,
#     remove_from_library,
#     archive_library_entry,
#     get_user_library,
# )

# from .tag_management import (
#     create_tag,
#     get_popular_tags,
#     search_tags,
# )

# from .statistics import (
#     get_review_statistics,
#     get_bean_review_summary,
# )

# from .exceptions import (
#     ReviewsServiceError,
#     ReviewNotFoundError,
#     DuplicateReviewError,
#     InvalidRatingError,
#     BeanNotFoundError,
#     LibraryEntryNotFoundError,
#     TagNotFoundError,
#     UnauthorizedReviewActionError,
#     InvalidContextError,
#     GroupMembershipRequiredError,
# )

__all__ = [
    # Services (to be uncommented)
]
```

### Verification

- [ ] Directory structure created
- [ ] All exception classes defined
- [ ] Stub files created with docstrings
- [ ] `__init__.py` exports prepared
- [ ] No syntax errors

---

## Phase 2: Review Management Service

**Time:** 2 hours
**Goal:** Implement core review CRUD operations with transaction safety

### Tasks

Implement `apps/reviews/services/review_management.py`:

```python
"""Review management service - CRUD operations for reviews."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet
from uuid import UUID
from typing import Optional

from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.groups.models import Group
from apps.reviews.models import Review, Tag
from .exceptions import (
    ReviewNotFoundError,
    DuplicateReviewError,
    InvalidRatingError,
    BeanNotFoundError,
    UnauthorizedReviewActionError,
    InvalidContextError,
    GroupMembershipRequiredError,
)


@transaction.atomic
def create_review(
    *,
    author: User,
    coffeebean_id: UUID,
    rating: int,
    aroma_score: Optional[int] = None,
    flavor_score: Optional[int] = None,
    acidity_score: Optional[int] = None,
    body_score: Optional[int] = None,
    aftertaste_score: Optional[int] = None,
    notes: str = '',
    brew_method: str = '',
    taste_tag_ids: Optional[list[UUID]] = None,
    context: str = 'personal',
    group_id: Optional[UUID] = None,
    would_buy_again: Optional[bool] = None
) -> Review:
    """
    Create a new review for a coffee bean.

    This operation:
    1. Validates rating range
    2. Validates context and group requirements
    3. Checks for duplicate review (author, coffeebean)
    4. Creates review with tags atomically
    5. Auto-creates library entry (handled by caller)

    Args:
        author: User creating the review
        coffeebean_id: UUID of coffee bean being reviewed
        rating: Overall rating (1-5, required)
        aroma_score: Aroma rating (1-5, optional)
        flavor_score: Flavor rating (1-5, optional)
        acidity_score: Acidity rating (1-5, optional)
        body_score: Body rating (1-5, optional)
        aftertaste_score: Aftertaste rating (1-5, optional)
        notes: Written review notes
        brew_method: Brewing method used
        taste_tag_ids: List of tag UUIDs to associate
        context: Review context (personal/group/public)
        group_id: Required if context='group'
        would_buy_again: Purchase intent

    Returns:
        Created Review instance

    Raises:
        InvalidRatingError: If rating not in 1-5 range
        BeanNotFoundError: If coffee bean doesn't exist or inactive
        DuplicateReviewError: If user already reviewed this bean
        InvalidContextError: If group context but no group_id
        GroupMembershipRequiredError: If not member of specified group
    """
    # Validate rating
    if not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    # Validate optional scores
    for score_name, score_value in [
        ('aroma', aroma_score),
        ('flavor', flavor_score),
        ('acidity', acidity_score),
        ('body', body_score),
        ('aftertaste', aftertaste_score),
    ]:
        if score_value is not None and not (1 <= score_value <= 5):
            raise InvalidRatingError(f"{score_name} score must be between 1 and 5")

    # Validate coffee bean exists and is active
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Validate group context
    group = None
    if context == 'group':
        if not group_id:
            raise InvalidContextError("Group ID required for group context reviews")

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            raise InvalidContextError("Group not found")

        # Check group membership
        if not group.has_member(author):
            raise GroupMembershipRequiredError(
                "You must be a member of this group to create a group review"
            )

    # Check for duplicate review (one per user per bean)
    existing = Review.objects.filter(author=author, coffeebean=coffeebean).exists()
    if existing:
        raise DuplicateReviewError(
            "You have already reviewed this coffee bean. Please update your existing review instead."
        )

    # Create review
    try:
        review = Review.objects.create(
            coffeebean=coffeebean,
            author=author,
            rating=rating,
            aroma_score=aroma_score,
            flavor_score=flavor_score,
            acidity_score=acidity_score,
            body_score=body_score,
            aftertaste_score=aftertaste_score,
            notes=notes,
            brew_method=brew_method,
            context=context,
            group=group,
            would_buy_again=would_buy_again,
        )
    except IntegrityError:
        # Database unique constraint caught duplicate
        raise DuplicateReviewError(
            "You have already reviewed this coffee bean"
        )

    # Associate taste tags
    if taste_tag_ids:
        tags = Tag.objects.filter(id__in=taste_tag_ids)
        review.taste_tags.set(tags)

    return review


def get_review_by_id(*, review_id: UUID) -> Review:
    """
    Retrieve a review by ID.

    Args:
        review_id: UUID of review

    Returns:
        Review instance

    Raises:
        ReviewNotFoundError: If review doesn't exist
    """
    try:
        review = Review.objects.select_related(
            'author',
            'coffeebean',
            'group'
        ).prefetch_related('taste_tags').get(id=review_id)
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    return review


@transaction.atomic
def update_review(
    *,
    review_id: UUID,
    user: User,
    rating: Optional[int] = None,
    aroma_score: Optional[int] = None,
    flavor_score: Optional[int] = None,
    acidity_score: Optional[int] = None,
    body_score: Optional[int] = None,
    aftertaste_score: Optional[int] = None,
    notes: Optional[str] = None,
    brew_method: Optional[str] = None,
    taste_tag_ids: Optional[list[UUID]] = None,
    would_buy_again: Optional[bool] = None
) -> Review:
    """
    Update an existing review.

    Only the review author can update their review.
    Coffeebean, author, context, and group cannot be changed.

    Args:
        review_id: UUID of review to update
        user: User making the update (must be author)
        rating: New overall rating (1-5)
        aroma_score: New aroma rating (1-5)
        flavor_score: New flavor rating (1-5)
        acidity_score: New acidity rating (1-5)
        body_score: New body rating (1-5)
        aftertaste_score: New aftertaste rating (1-5)
        notes: New review notes
        brew_method: New brew method
        taste_tag_ids: New list of tag UUIDs
        would_buy_again: New purchase intent

    Returns:
        Updated Review instance

    Raises:
        ReviewNotFoundError: If review doesn't exist
        UnauthorizedReviewActionError: If user is not the author
        InvalidRatingError: If rating not in 1-5 range
    """
    # Get review with row lock
    try:
        review = (
            Review.objects
            .select_for_update()
            .get(id=review_id)
        )
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    # Check authorization
    if review.author != user:
        raise UnauthorizedReviewActionError(
            "You can only update your own reviews"
        )

    # Validate ratings if provided
    if rating is not None and not (1 <= rating <= 5):
        raise InvalidRatingError("Rating must be between 1 and 5")

    for score_name, score_value in [
        ('aroma', aroma_score),
        ('flavor', flavor_score),
        ('acidity', acidity_score),
        ('body', body_score),
        ('aftertaste', aftertaste_score),
    ]:
        if score_value is not None and not (1 <= score_value <= 5):
            raise InvalidRatingError(f"{score_name} score must be between 1 and 5")

    # Update fields if provided
    if rating is not None:
        review.rating = rating
    if aroma_score is not None:
        review.aroma_score = aroma_score
    if flavor_score is not None:
        review.flavor_score = flavor_score
    if acidity_score is not None:
        review.acidity_score = acidity_score
    if body_score is not None:
        review.body_score = body_score
    if aftertaste_score is not None:
        review.aftertaste_score = aftertaste_score
    if notes is not None:
        review.notes = notes
    if brew_method is not None:
        review.brew_method = brew_method
    if would_buy_again is not None:
        review.would_buy_again = would_buy_again

    review.save()

    # Update tags if provided
    if taste_tag_ids is not None:
        tags = Tag.objects.filter(id__in=taste_tag_ids)
        review.taste_tags.set(tags)

    return review


@transaction.atomic
def delete_review(*, review_id: UUID, user: User) -> None:
    """
    Delete a review.

    Only the review author can delete their review.

    Args:
        review_id: UUID of review to delete
        user: User making the deletion (must be author)

    Raises:
        ReviewNotFoundError: If review doesn't exist
        UnauthorizedReviewActionError: If user is not the author
    """
    # Get review with row lock
    try:
        review = (
            Review.objects
            .select_for_update()
            .get(id=review_id)
        )
    except Review.DoesNotExist:
        raise ReviewNotFoundError("Review not found")

    # Check authorization
    if review.author != user:
        raise UnauthorizedReviewActionError(
            "You can only delete your own reviews"
        )

    # Delete review (CASCADE will handle tags M2M)
    review.delete()


def get_user_reviews(
    *,
    user: User,
    coffeebean_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
    rating: Optional[int] = None,
    min_rating: Optional[int] = None,
    context: Optional[str] = None
) -> QuerySet[Review]:
    """
    Get all reviews by a specific user with optional filters.

    Args:
        user: User whose reviews to retrieve
        coffeebean_id: Filter by specific coffee bean
        group_id: Filter by specific group
        rating: Filter by exact rating
        min_rating: Filter by minimum rating
        context: Filter by context (personal/group/public)

    Returns:
        QuerySet of Review instances
    """
    queryset = Review.objects.filter(author=user).select_related(
        'coffeebean',
        'group'
    ).prefetch_related('taste_tags')

    if coffeebean_id:
        queryset = queryset.filter(coffeebean_id=coffeebean_id)

    if group_id:
        queryset = queryset.filter(group_id=group_id)

    if rating:
        queryset = queryset.filter(rating=rating)

    if min_rating:
        queryset = queryset.filter(rating__gte=min_rating)

    if context:
        queryset = queryset.filter(context=context)

    return queryset.order_by('-created_at')
```

### Update `__init__.py`

Uncomment the review_management imports.

### Verification

- [ ] All functions implemented with proper signatures
- [ ] Type hints throughout
- [ ] Keyword-only arguments (`*, param`)
- [ ] `@transaction.atomic` on state changes
- [ ] `select_for_update()` on updates/deletes
- [ ] Domain exceptions raised
- [ ] Comprehensive docstrings
- [ ] No syntax errors

---

## Phase 3: Library Management Service

**Time:** 2 hours
**Goal:** Implement user library operations with transaction safety

### Tasks

Implement `apps/reviews/services/library_management.py`:

```python
"""Library management service - User's personal coffee library operations."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet, Q
from uuid import UUID
from typing import Optional

from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.reviews.models import UserLibraryEntry
from .exceptions import (
    BeanNotFoundError,
    LibraryEntryNotFoundError,
)


@transaction.atomic
def add_to_library(
    *,
    user: User,
    coffeebean_id: UUID,
    added_by: str = 'manual'
) -> tuple[UserLibraryEntry, bool]:
    """
    Add a coffee bean to user's personal library.

    Uses get_or_create to handle duplicates gracefully.
    If bean already in library, returns existing entry.

    Args:
        user: User adding the bean
        coffeebean_id: UUID of coffee bean to add
        added_by: Source ('review', 'purchase', 'manual')

    Returns:
        Tuple of (UserLibraryEntry, created: bool)

    Raises:
        BeanNotFoundError: If coffee bean doesn't exist or inactive
    """
    # Validate coffee bean exists and is active
    try:
        coffeebean = CoffeeBean.objects.get(id=coffeebean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Get or create library entry
    try:
        entry, created = UserLibraryEntry.objects.get_or_create(
            user=user,
            coffeebean=coffeebean,
            defaults={'added_by': added_by}
        )
    except IntegrityError:
        # Rare race condition: entry created between get and create
        # Fetch the existing entry
        entry = UserLibraryEntry.objects.get(user=user, coffeebean=coffeebean)
        created = False

    return entry, created


@transaction.atomic
def remove_from_library(*, entry_id: UUID, user: User) -> None:
    """
    Remove a coffee bean from user's library.

    Args:
        entry_id: UUID of library entry to remove
        user: User removing the entry (must be owner)

    Raises:
        LibraryEntryNotFoundError: If entry doesn't exist or belongs to another user
    """
    # Get entry with row lock
    try:
        entry = (
            UserLibraryEntry.objects
            .select_for_update()
            .get(id=entry_id, user=user)
        )
    except UserLibraryEntry.DoesNotExist:
        raise LibraryEntryNotFoundError(
            "Library entry not found or does not belong to you"
        )

    entry.delete()


@transaction.atomic
def archive_library_entry(
    *,
    entry_id: UUID,
    user: User,
    is_archived: bool = True
) -> UserLibraryEntry:
    """
    Archive or unarchive a library entry.

    Archived entries are hidden from main library view but preserved.

    Args:
        entry_id: UUID of library entry
        user: User performing the action (must be owner)
        is_archived: True to archive, False to unarchive

    Returns:
        Updated UserLibraryEntry

    Raises:
        LibraryEntryNotFoundError: If entry doesn't exist or belongs to another user
    """
    # Get entry with row lock
    try:
        entry = (
            UserLibraryEntry.objects
            .select_for_update()
            .get(id=entry_id, user=user)
        )
    except UserLibraryEntry.DoesNotExist:
        raise LibraryEntryNotFoundError(
            "Library entry not found or does not belong to you"
        )

    entry.is_archived = is_archived
    entry.save(update_fields=['is_archived'])

    return entry


def get_user_library(
    *,
    user: User,
    is_archived: bool = False,
    search: Optional[str] = None
) -> QuerySet[UserLibraryEntry]:
    """
    Get user's coffee library with optional filtering.

    Args:
        user: User whose library to retrieve
        is_archived: Show archived (True) or active (False) entries
        search: Search in coffee bean name or roastery

    Returns:
        QuerySet of UserLibraryEntry instances
    """
    queryset = UserLibraryEntry.objects.filter(
        user=user,
        is_archived=is_archived
    ).select_related('coffeebean')

    if search:
        queryset = queryset.filter(
            Q(coffeebean__name__icontains=search) |
            Q(coffeebean__roastery_name__icontains=search)
        )

    return queryset.order_by('-added_at')
```

### Update `__init__.py`

Uncomment the library_management imports.

### Verification

- [ ] All functions implemented
- [ ] Transaction safety with `@transaction.atomic`
- [ ] `select_for_update()` for updates/deletes
- [ ] get_or_create handles race conditions
- [ ] Domain exceptions raised
- [ ] Comprehensive docstrings

---

## Phase 4: Tag Management Service

**Time:** 1 hour
**Goal:** Implement tag CRUD operations

### Tasks

Implement `apps/reviews/services/tag_management.py`:

```python
"""Tag management service - Taste tags for coffee reviews."""

from django.db import transaction, IntegrityError
from django.db.models import QuerySet, Count

from apps.reviews.models import Tag
from .exceptions import TagNotFoundError


@transaction.atomic
def create_tag(*, name: str, category: str = '') -> Tag:
    """
    Create a new taste tag.

    Args:
        name: Tag name (must be unique)
        category: Optional category for grouping tags

    Returns:
        Created Tag instance

    Raises:
        IntegrityError: If tag with this name already exists
    """
    try:
        tag = Tag.objects.create(name=name, category=category)
    except IntegrityError:
        raise IntegrityError(f"Tag '{name}' already exists")

    return tag


def get_tag_by_id(*, tag_id: str) -> Tag:
    """
    Retrieve a tag by ID.

    Args:
        tag_id: UUID of tag

    Returns:
        Tag instance

    Raises:
        TagNotFoundError: If tag doesn't exist
    """
    try:
        tag = Tag.objects.get(id=tag_id)
    except Tag.DoesNotExist:
        raise TagNotFoundError("Tag not found")

    return tag


def get_popular_tags(*, limit: int = 20) -> QuerySet[Tag]:
    """
    Get most frequently used tags.

    Args:
        limit: Maximum number of tags to return

    Returns:
        QuerySet of Tag instances ordered by usage count
    """
    return (
        Tag.objects
        .annotate(usage_count=Count('reviews'))
        .filter(usage_count__gt=0)
        .order_by('-usage_count')[:limit]
    )


def search_tags(
    *,
    search: str = '',
    category: str = ''
) -> QuerySet[Tag]:
    """
    Search tags by name or category.

    Args:
        search: Search term for tag name (case-insensitive)
        category: Filter by specific category

    Returns:
        QuerySet of matching Tag instances
    """
    queryset = Tag.objects.all()

    if search:
        queryset = queryset.filter(name__icontains=search)

    if category:
        queryset = queryset.filter(category=category)

    return queryset.order_by('name')
```

### Update `__init__.py`

Uncomment the tag_management imports.

### Verification

- [ ] All functions implemented
- [ ] `@transaction.atomic` on create
- [ ] get_popular_tags uses proper aggregation
- [ ] Search with proper filters
- [ ] Domain exceptions raised

---

## Phase 5: Statistics Service

**Time:** 2 hours
**Goal:** Extract complex statistics/analytics logic

### Tasks

Implement `apps/reviews/services/statistics.py`:

```python
"""Statistics service - Review analytics and aggregations."""

from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth
from uuid import UUID
from typing import Optional

from apps.reviews.models import Review, Tag
from apps.beans.models import CoffeeBean
from .exceptions import BeanNotFoundError


def get_review_statistics(
    *,
    user_id: Optional[UUID] = None,
    bean_id: Optional[UUID] = None
) -> dict:
    """
    Calculate comprehensive review statistics.

    Can be filtered by user or bean to get specific statistics.

    Args:
        user_id: Optional UUID to filter by specific user
        bean_id: Optional UUID to filter by specific bean

    Returns:
        Dictionary with statistics:
        - total_reviews: int
        - avg_rating: float
        - rating_distribution: dict {rating: count}
        - top_tags: list of {id, name, count}
        - reviews_by_month: dict {month: count}
    """
    queryset = Review.objects.all()

    # Apply filters
    if user_id:
        queryset = queryset.filter(author_id=user_id)

    if bean_id:
        queryset = queryset.filter(coffeebean_id=bean_id)

    # Calculate basic statistics
    total_reviews = queryset.count()
    avg_rating = queryset.aggregate(avg=Avg('rating'))['avg'] or 0

    # Rating distribution (1-5 stars)
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[str(i)] = queryset.filter(rating=i).count()

    # Top tags (most frequently used)
    top_tags = list(
        Tag.objects.filter(reviews__in=queryset)
        .annotate(count=Count('reviews'))
        .order_by('-count')
        .values('id', 'name', 'count')[:10]
    )

    # Reviews by month (last 12 months)
    reviews_by_month = list(
        queryset
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('-month')[:12]
    )

    return {
        'total_reviews': total_reviews,
        'avg_rating': round(float(avg_rating), 2),
        'rating_distribution': rating_dist,
        'top_tags': top_tags,
        'reviews_by_month': {
            str(item['month'].date()): item['count']
            for item in reviews_by_month
        }
    }


def get_bean_review_summary(*, bean_id: UUID) -> dict:
    """
    Get comprehensive review summary for a specific coffee bean.

    Args:
        bean_id: UUID of coffee bean

    Returns:
        Dictionary with:
        - bean_id: UUID
        - bean_name: str
        - total_reviews: int
        - avg_rating: float
        - rating_breakdown: dict {rating: count}
        - common_tags: list of {id, name, count}

    Raises:
        BeanNotFoundError: If bean doesn't exist or inactive
    """
    # Validate bean exists
    try:
        bean = CoffeeBean.objects.get(id=bean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError("Coffee bean not found or inactive")

    # Get all reviews for this bean
    reviews = Review.objects.filter(coffeebean=bean)

    # Rating breakdown
    rating_breakdown = {}
    for i in range(1, 6):
        rating_breakdown[str(i)] = reviews.filter(rating=i).count()

    # Common tags used in reviews
    common_tags = list(
        Tag.objects.filter(reviews__coffeebean=bean)
        .annotate(count=Count('reviews'))
        .order_by('-count')
        .values('id', 'name', 'count')[:10]
    )

    return {
        'bean_id': str(bean.id),
        'bean_name': f"{bean.roastery_name} - {bean.name}",
        'total_reviews': reviews.count(),
        'avg_rating': float(bean.avg_rating),
        'rating_breakdown': rating_breakdown,
        'common_tags': common_tags,
    }
```

### Update `__init__.py`

Uncomment the statistics imports.

### Verification

- [ ] Statistics functions implemented
- [ ] Proper use of aggregation/annotation
- [ ] No N+1 queries
- [ ] Returns proper data structures
- [ ] Bean validation with proper exception

---

## Phase 6: Update Views to Use Services

**Time:** 2 hours
**Goal:** Refactor views to be thin HTTP handlers

### Tasks

Update `apps/reviews/views.py` to use services:

**Before (perform_create):**
```python
@transaction.atomic
def perform_create(self, serializer):
    review = serializer.save(author=self.request.user)
    UserLibraryEntry.ensure_entry(...)
    transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())
```

**After:**
```python
def perform_create(self, serializer):
    from apps.reviews.services import create_review, add_to_library
    from apps.reviews.services.exceptions import (
        DuplicateReviewError,
        BeanNotFoundError,
        InvalidRatingError,
        InvalidContextError,
        GroupMembershipRequiredError,
    )

    try:
        review = create_review(
            author=self.request.user,
            coffeebean_id=serializer.validated_data['coffeebean'].id,
            rating=serializer.validated_data['rating'],
            aroma_score=serializer.validated_data.get('aroma_score'),
            flavor_score=serializer.validated_data.get('flavor_score'),
            acidity_score=serializer.validated_data.get('acidity_score'),
            body_score=serializer.validated_data.get('body_score'),
            aftertaste_score=serializer.validated_data.get('aftertaste_score'),
            notes=serializer.validated_data.get('notes', ''),
            brew_method=serializer.validated_data.get('brew_method', ''),
            taste_tag_ids=serializer.validated_data.get('taste_tag_ids'),
            context=serializer.validated_data.get('context', 'personal'),
            group_id=serializer.validated_data.get('group').id if serializer.validated_data.get('group') else None,
            would_buy_again=serializer.validated_data.get('would_buy_again'),
        )

        # Auto-add to library
        add_to_library(
            user=self.request.user,
            coffeebean_id=review.coffeebean.id,
            added_by='review'
        )

        # Update aggregate rating (asynchronous)
        transaction.on_commit(lambda: review.coffeebean.update_aggregate_rating())

    except (DuplicateReviewError, BeanNotFoundError, InvalidRatingError,
            InvalidContextError, GroupMembershipRequiredError) as e:
        from rest_framework.exceptions import ValidationError
        raise ValidationError(str(e))

    serializer.instance = review
```

Update all views similarly:
- `perform_update()` → use `update_review()`
- `perform_destroy()` → use `delete_review()`
- `add_to_library()` → use service
- `archive_library_entry()` → use service
- `remove_from_library()` → use service
- `create_tag()` → use service
- `statistics()` → use service
- `bean_review_summary()` → use service

### Verification

- [ ] All views updated to use services
- [ ] Views are <20 lines per method
- [ ] No business logic in views
- [ ] Proper exception handling
- [ ] Services called with keyword arguments

---

## Phase 7: Update Serializers

**Time:** 1 hour
**Goal:** Simplify serializers to validation only

### Tasks

1. **Remove business logic from ReviewSerializer:**
   - Remove `create()` and `update()` methods
   - Keep validation only

2. **Simplify ReviewCreateSerializer:**
   - Remove duplicate review check (now in service)
   - Keep only input validation
   - Remove group membership check (now in service)

3. **Keep serializers for:**
   - Input validation (field types, required fields)
   - Output formatting
   - Nested serialization

**Example Simplified Serializer:**
```python
class ReviewCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for review creation."""

    taste_tag_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Review
        fields = [
            'coffeebean',
            'rating',
            'aroma_score',
            'flavor_score',
            'acidity_score',
            'body_score',
            'aftertaste_score',
            'notes',
            'brew_method',
            'taste_tag_ids',
            'context',
            'group',
            'would_buy_again',
        ]

    # Validation only - no business logic
```

### Verification

- [ ] No business logic in serializers
- [ ] No `create()`/`update()` methods
- [ ] Only input validation remains
- [ ] Output serializers unchanged

---

## Phase 8: Model Cleanup

**Time:** 30 minutes
**Goal:** Remove business logic from models

### Tasks

1. **Remove UserLibraryEntry.ensure_entry():**
   - This is now in `library_management.py`
   - Keep models as pure domain objects

**Before:**
```python
@classmethod
def ensure_entry(cls, user, coffeebean, added_by='review'):
    entry, created = cls.objects.get_or_create(...)
    return entry, created
```

**After:** Remove this method entirely.

2. **Keep domain query methods:**
   - Simple getters are OK
   - No orchestration logic

### Verification

- [ ] No business logic in models
- [ ] Only domain query methods remain
- [ ] Models are clean data structures

---

## Phase 9: Documentation

**Time:** 1 hour
**Goal:** Document the services layer architecture

### Tasks

1. **Update `docs/app-context/reviews.md`:**
   - Add "Services Layer Architecture" section
   - Document all service modules
   - Include usage examples
   - Document transaction safety
   - Document concurrency protection

2. **Follow groups app documentation pattern:**
   - Overview
   - Service modules table
   - Domain exceptions list
   - Transaction safety patterns
   - Concurrency protection strategies
   - Service usage examples
   - Before/after comparison
   - Testing strategies

### Verification

- [ ] Services layer documented
- [ ] Usage examples included
- [ ] Transaction safety explained
- [ ] Concurrency protection documented

---

## Phase 10: Service Tests

**Time:** 3 hours
**Goal:** Comprehensive service-level tests

### Tasks

Create `apps/reviews/tests/test_services.py`:

**Test Categories:**

1. **Review Management Tests:**
   - Create review success
   - Create review with tags
   - Duplicate review prevention
   - Invalid rating error
   - Group context validation
   - Update review success
   - Update unauthorized
   - Delete review success
   - Delete unauthorized

2. **Library Management Tests:**
   - Add to library success
   - Add duplicate (idempotent)
   - Remove from library
   - Archive/unarchive
   - Inactive bean rejection

3. **Tag Management Tests:**
   - Create tag success
   - Duplicate tag error
   - Get popular tags
   - Search tags

4. **Statistics Tests:**
   - Review statistics calculation
   - Bean review summary
   - Empty statistics

5. **Concurrency Tests:**
   - Concurrent review creation (same user/bean)
   - Concurrent library additions
   - Concurrent review updates

**Example Concurrency Test:**
```python
class TestConcurrency(TransactionTestCase):
    def test_concurrent_review_creation_prevented(self):
        """Multiple concurrent reviews for same (user, bean) should fail."""
        from apps.reviews.services import create_review
        from apps.reviews.services.exceptions import DuplicateReviewError

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

        # Spawn 5 threads trying to create simultaneously
        threads = [threading.Thread(target=create_in_thread) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Only 1 should succeed, 4 should get DuplicateReviewError
        assert len(results) == 1
        assert len(errors) == 4
```

### Verification

- [ ] All service functions tested
- [ ] Concurrency tests included
- [ ] Edge cases covered
- [ ] Test coverage >80%

---

## Summary Checklist

### Must Complete (Essential)

- [ ] Phase 1: Services directory structure
- [ ] Phase 2: Review management service
- [ ] Phase 3: Library management service
- [ ] Phase 4: Tag management service
- [ ] Phase 5: Statistics service
- [ ] Phase 6: Update views to use services
- [ ] Phase 7: Update serializers
- [ ] Phase 8: Model cleanup

### Should Complete (Important)

- [ ] Phase 9: Documentation
- [ ] Phase 10: Service tests

### Final Verification

- [ ] All views are thin HTTP handlers
- [ ] No business logic in views/serializers/models
- [ ] All state changes use `@transaction.atomic`
- [ ] Critical operations use `select_for_update()`
- [ ] Domain exceptions for all errors
- [ ] Service tests with concurrency scenarios
- [ ] Documentation updated

---

## Success Metrics

### Before Refactoring
- ❌ 0 service functions
- ❌ 0% concurrency protection
- ⚠️ 42.8% transaction safety
- ❌ ~150 lines business logic in views

### After Refactoring
- ✅ ~15 service functions
- ✅ 100% concurrency protection
- ✅ 100% transaction safety
- ✅ Views <100 lines, thin HTTP handlers
- ✅ 80%+ service test coverage
- ✅ Zero race conditions

---

## Estimated Timeline

- **Phase 1:** 30 minutes
- **Phase 2:** 2 hours
- **Phase 3:** 2 hours
- **Phase 4:** 1 hour
- **Phase 5:** 2 hours
- **Phase 6:** 2 hours
- **Phase 7:** 1 hour
- **Phase 8:** 30 minutes
- **Phase 9:** 1 hour
- **Phase 10:** 3 hours

**Total:** 14-16 hours

Good luck with the refactoring! 🚀
