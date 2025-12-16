# Beans App Refactoring Checklist

**Goal:** Refactor beans app to follow DRF best practices with proper service layer, transaction management, and concurrency protection.

**Estimated Time:** 1-2 days
**Difficulty:** Medium
**Risk Level:** Low-Medium (has existing data, needs careful migration)

---

## Current State Analysis

### ✅ What's Good
- ViewSets properly implemented
- Serializers are clean with no business logic
- Basic services.py exists with deduplication logic
- Soft delete pattern in place
- Good use of normalized fields for search

### ❌ What Needs Refactoring

**Service Layer Issues:**
- Services implemented as static class methods (should be functions)
- All services in single file (should be modular)
- Missing transaction safety in most operations
- No concurrency protection

**Business Logic Location:**
- Views contain filtering logic (should be in services)
- Models have business logic in save() (should be in services)
- `update_aggregate_rating()` on model (should be service)

**Missing Components:**
- MergeHistory model (referenced but not defined)
- Domain-specific exceptions
- Service tests
- Transaction wrappers on critical operations

**Concurrency Risks:**
- No select_for_update() on aggregate updates
- No locking on merge operations
- Rating calculations could have race conditions

---

## 📋 Phase 1: Fix Critical Bug & Setup (30 min)

### Task 1.1: Create Missing MergeHistory Model

**Issue:** `services.py` references `MergeHistory` model that doesn't exist

**File:** `apps/beans/models.py`

**Add:**
```python
class MergeHistory(models.Model):
    """Track bean merge operations for audit trail."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merged_from = models.UUIDField(help_text="ID of bean that was merged (deleted)")
    merged_into = models.ForeignKey(
        CoffeeBean,
        on_delete=models.CASCADE,
        related_name='merge_targets',
        help_text="Bean that absorbed the merged bean"
    )
    merged_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='bean_merges'
    )
    reason = models.TextField(blank=True)
    merged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bean_merge_history'
        ordering = ['-merged_at']
        indexes = [
            models.Index(fields=['merged_from']),
            models.Index(fields=['merged_at']),
        ]

    def __str__(self):
        return f"Merge {self.merged_from} → {self.merged_into_id}"
```

**Migration:**
```bash
python manage.py makemigrations beans
python manage.py migrate beans
```

---

### Task 1.2: Create Services Directory Structure

**Create files:**
```bash
apps/beans/services/
├── __init__.py
├── exceptions.py
├── bean_management.py          # CRUD operations
├── bean_search.py              # Search and filtering
├── bean_deduplication.py       # Duplicate detection
├── bean_merging.py             # Merge operations
├── variant_management.py       # Variant CRUD
└── rating_aggregation.py       # Rating calculations
```

**Command:**
```bash
mkdir -p apps/beans/services
touch apps/beans/services/__init__.py
touch apps/beans/services/exceptions.py
touch apps/beans/services/bean_management.py
touch apps/beans/services/bean_search.py
touch apps/beans/services/bean_deduplication.py
touch apps/beans/services/bean_merging.py
touch apps/beans/services/variant_management.py
touch apps/beans/services/rating_aggregation.py
```

---

### Task 1.3: Create Domain Exceptions

**File:** `apps/beans/services/exceptions.py`

```python
"""Domain-specific exceptions for beans services."""


class BeansServiceError(Exception):
    """Base exception for beans services."""
    pass


class BeanNotFoundError(BeansServiceError):
    """Raised when bean does not exist."""
    pass


class DuplicateBeanError(BeansServiceError):
    """Raised when attempting to create duplicate bean."""
    pass


class BeanMergeError(BeansServiceError):
    """Raised when bean merge operation fails."""
    pass


class InvalidMergeError(BeansServiceError):
    """Raised when merge parameters are invalid."""
    pass


class VariantNotFoundError(BeansServiceError):
    """Raised when variant does not exist."""
    pass


class DuplicateVariantError(BeansServiceError):
    """Raised when variant already exists for bean/weight combo."""
    pass
```

**Test:**
```bash
python manage.py shell -c "from apps.beans.services.exceptions import BeansServiceError"
```

---

### Task 1.4: Create Services __init__.py

**File:** `apps/beans/services/__init__.py`

```python
"""Services for beans business logic."""

from .exceptions import (
    BeansServiceError,
    BeanNotFoundError,
    DuplicateBeanError,
    BeanMergeError,
    InvalidMergeError,
    VariantNotFoundError,
    DuplicateVariantError,
)

__all__ = [
    # Exceptions
    'BeansServiceError',
    'BeanNotFoundError',
    'DuplicateBeanError',
    'BeanMergeError',
    'InvalidMergeError',
    'VariantNotFoundError',
    'DuplicateVariantError',
]
```

---

## 📋 Phase 2: Bean Management Service (45 min)

### Task 2.1: Create Bean Management Service

**File:** `apps/beans/services/bean_management.py`

**Content:**
```python
"""Bean CRUD operations service."""

from django.db import transaction
from django.contrib.auth import get_user_model
from uuid import UUID
from typing import Optional, Dict, Any

from ..models import CoffeeBean
from .exceptions import BeanNotFoundError, DuplicateBeanError

User = get_user_model()


@transaction.atomic
def create_bean(
    *,
    name: str,
    roastery_name: str,
    created_by: User,
    origin_country: str = '',
    region: str = '',
    processing: str = 'washed',
    roast_profile: str = 'medium',
    roast_date: Optional[str] = None,
    brew_method: str = 'filter',
    description: str = '',
    tasting_notes: str = '',
    check_duplicates: bool = True
) -> CoffeeBean:
    """
    Create a new coffee bean.

    Args:
        name: Coffee name
        roastery_name: Roaster/brand name
        created_by: User creating the bean
        check_duplicates: If True, checks for existing bean
        ... other fields

    Returns:
        Created CoffeeBean instance

    Raises:
        DuplicateBeanError: If bean already exists
    """
    # Check for duplicates
    if check_duplicates:
        normalized_name = CoffeeBean._normalize_string(name)
        normalized_roastery = CoffeeBean._normalize_string(roastery_name)

        existing = CoffeeBean.objects.filter(
            name_normalized=normalized_name,
            roastery_normalized=normalized_roastery,
            is_active=True
        ).first()

        if existing:
            raise DuplicateBeanError(
                f"Bean '{name}' from '{roastery_name}' already exists"
            )

    # Create bean
    bean = CoffeeBean.objects.create(
        name=name,
        roastery_name=roastery_name,
        origin_country=origin_country,
        region=region,
        processing=processing,
        roast_profile=roast_profile,
        roast_date=roast_date,
        brew_method=brew_method,
        description=description,
        tasting_notes=tasting_notes,
        created_by=created_by
    )

    return bean


@transaction.atomic
def update_bean(
    *,
    bean_id: UUID,
    data: Dict[str, Any]
) -> CoffeeBean:
    """
    Update an existing bean.

    Args:
        bean_id: Bean UUID
        data: Fields to update

    Returns:
        Updated CoffeeBean instance

    Raises:
        BeanNotFoundError: If bean doesn't exist
    """
    try:
        bean = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=bean_id, is_active=True)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")

    # Update allowed fields
    allowed_fields = [
        'name', 'roastery_name', 'origin_country', 'region',
        'processing', 'roast_profile', 'roast_date', 'brew_method',
        'description', 'tasting_notes'
    ]

    for field, value in data.items():
        if field in allowed_fields:
            setattr(bean, field, value)

    bean.save()
    return bean


@transaction.atomic
def soft_delete_bean(*, bean_id: UUID) -> None:
    """
    Soft delete a bean (set is_active=False).

    Args:
        bean_id: Bean UUID

    Raises:
        BeanNotFoundError: If bean doesn't exist
    """
    try:
        bean = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")

    bean.is_active = False
    bean.save(update_fields=['is_active', 'updated_at'])


def get_bean_by_id(*, bean_id: UUID, include_inactive: bool = False) -> CoffeeBean:
    """
    Get bean by ID.

    Args:
        bean_id: Bean UUID
        include_inactive: Whether to include soft-deleted beans

    Returns:
        CoffeeBean instance

    Raises:
        BeanNotFoundError: If bean doesn't exist
    """
    try:
        queryset = CoffeeBean.objects.select_related('created_by').prefetch_related('variants')

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset.get(id=bean_id)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")
```

**Export in services/__init__.py:**
```python
from .bean_management import (
    create_bean,
    update_bean,
    soft_delete_bean,
    get_bean_by_id,
)

__all__ = [
    # ... existing exports
    'create_bean',
    'update_bean',
    'soft_delete_bean',
    'get_bean_by_id',
]
```

---

### Task 2.2: Update CoffeeBeanViewSet to Use Service

**File:** `apps/beans/views.py`

**Before (perform_create):**
```python
def perform_create(self, serializer):
    """Set created_by to current user."""
    serializer.save(created_by=self.request.user)
```

**After:**
```python
from .services import create_bean, DuplicateBeanError

def create(self, request, *args, **kwargs):
    """Create a new coffee bean."""
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        bean = create_bean(
            created_by=request.user,
            **serializer.validated_data
        )
    except DuplicateBeanError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    output_serializer = CoffeeBeanSerializer(bean)
    return Response(
        output_serializer.data,
        status=status.HTTP_201_CREATED
    )
```

**Before (perform_destroy):**
```python
def perform_destroy(self, instance):
    """Soft delete - set is_active to False instead of deleting."""
    instance.is_active = False
    instance.save(update_fields=['is_active'])
```

**After:**
```python
from .services import soft_delete_bean

def destroy(self, request, *args, **kwargs):
    """Soft delete a bean."""
    bean_id = kwargs.get('pk')

    try:
        soft_delete_bean(bean_id=bean_id)
    except BeanNotFoundError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## 📋 Phase 3: Search Service (30 min)

### Task 3.1: Create Bean Search Service

**File:** `apps/beans/services/bean_search.py`

```python
"""Bean search and filtering service."""

from django.db.models import Q, QuerySet
from typing import Optional

from ..models import CoffeeBean


def search_beans(
    *,
    search: Optional[str] = None,
    roastery: Optional[str] = None,
    origin: Optional[str] = None,
    roast_profile: Optional[str] = None,
    processing: Optional[str] = None,
    min_rating: Optional[float] = None,
    only_active: bool = True
) -> QuerySet[CoffeeBean]:
    """
    Search and filter coffee beans.

    Args:
        search: Search term for name, roastery, origin, description
        roastery: Filter by roastery name
        origin: Filter by origin country
        roast_profile: Filter by roast profile
        processing: Filter by processing method
        min_rating: Minimum average rating
        only_active: Only return active beans

    Returns:
        Filtered QuerySet of CoffeeBean
    """
    queryset = CoffeeBean.objects.select_related('created_by').prefetch_related('variants')

    if only_active:
        queryset = queryset.filter(is_active=True)

    # Search across multiple fields
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(roastery_name__icontains=search) |
            Q(origin_country__icontains=search) |
            Q(description__icontains=search) |
            Q(tasting_notes__icontains=search)
        )

    # Specific filters
    if roastery:
        queryset = queryset.filter(roastery_name__icontains=roastery)

    if origin:
        queryset = queryset.filter(origin_country__icontains=origin)

    if roast_profile:
        queryset = queryset.filter(roast_profile=roast_profile)

    if processing:
        queryset = queryset.filter(processing=processing)

    if min_rating is not None:
        queryset = queryset.filter(avg_rating__gte=min_rating)

    return queryset.distinct()


def get_all_roasteries(*, only_active: bool = True) -> list[str]:
    """
    Get list of all unique roastery names.

    Args:
        only_active: Only include active beans

    Returns:
        Sorted list of roastery names
    """
    queryset = CoffeeBean.objects.all()

    if only_active:
        queryset = queryset.filter(is_active=True)

    roasteries = (
        queryset
        .values_list('roastery_name', flat=True)
        .distinct()
        .order_by('roastery_name')
    )

    return list(roasteries)


def get_all_origins(*, only_active: bool = True) -> list[str]:
    """
    Get list of all unique origin countries.

    Args:
        only_active: Only include active beans

    Returns:
        Sorted list of origin countries
    """
    queryset = CoffeeBean.objects.all()

    if only_active:
        queryset = queryset.filter(is_active=True)

    origins = (
        queryset
        .filter(origin_country__isnull=False)
        .exclude(origin_country='')
        .values_list('origin_country', flat=True)
        .distinct()
        .order_by('origin_country')
    )

    return list(origins)
```

**Export:**
```python
from .bean_search import search_beans, get_all_roasteries, get_all_origins
```

---

### Task 3.2: Update ViewSet to Use Search Service

**File:** `apps/beans/views.py`

**Before (get_queryset):**
```python
def get_queryset(self):
    queryset = super().get_queryset()

    search = self.request.query_params.get('search')
    if search:
        queryset = queryset.filter(...)

    # ... more filters

    return queryset.distinct()
```

**After:**
```python
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

**Before (roasteries action):**
```python
@action(detail=False, methods=['get'])
def roasteries(self, request):
    roasteries = CoffeeBean.objects.filter(...).values_list(...)
    return Response(list(roasteries))
```

**After:**
```python
from .services import get_all_roasteries

@action(detail=False, methods=['get'])
def roasteries(self, request):
    """Get list of all roasteries."""
    roasteries = get_all_roasteries()
    return Response(roasteries)
```

---

## 📋 Phase 4: Rating Aggregation Service (45 min)

### Task 4.1: Create Rating Aggregation Service

**File:** `apps/beans/services/rating_aggregation.py`

```python
"""Rating aggregation service with concurrency protection."""

from django.db import transaction
from django.db.models import Avg, Count
from decimal import Decimal
from uuid import UUID

from ..models import CoffeeBean
from .exceptions import BeanNotFoundError


@transaction.atomic
def update_bean_rating(*, bean_id: UUID) -> CoffeeBean:
    """
    Recalculate and update bean's aggregate rating.

    Uses select_for_update() to prevent race conditions
    when multiple reviews are created/updated simultaneously.

    Args:
        bean_id: Bean UUID

    Returns:
        Updated CoffeeBean instance

    Raises:
        BeanNotFoundError: If bean doesn't exist
    """
    try:
        # Lock the bean to prevent concurrent updates
        bean = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")

    # Calculate aggregates from reviews
    aggregates = bean.reviews.aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    # Update bean
    bean.avg_rating = aggregates['avg'] or Decimal('0.00')
    bean.review_count = aggregates['count']
    bean.save(update_fields=['avg_rating', 'review_count', 'updated_at'])

    return bean


def get_top_rated_beans(*, limit: int = 10, min_reviews: int = 3):
    """
    Get top-rated beans with minimum review count.

    Args:
        limit: Number of beans to return
        min_reviews: Minimum number of reviews required

    Returns:
        QuerySet of top-rated beans
    """
    return (
        CoffeeBean.objects
        .filter(is_active=True, review_count__gte=min_reviews)
        .order_by('-avg_rating', '-review_count')[:limit]
    )


def get_most_reviewed_beans(*, limit: int = 10):
    """
    Get beans with most reviews.

    Args:
        limit: Number of beans to return

    Returns:
        QuerySet of most-reviewed beans
    """
    return (
        CoffeeBean.objects
        .filter(is_active=True)
        .order_by('-review_count', '-avg_rating')[:limit]
    )
```

**Export:**
```python
from .rating_aggregation import (
    update_bean_rating,
    get_top_rated_beans,
    get_most_reviewed_beans,
)
```

---

### Task 4.2: Remove Business Logic from Model

**File:** `apps/beans/models.py`

**Before:**
```python
def update_aggregate_rating(self):
    from django.db.models import Avg, Count
    aggregates = self.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    self.avg_rating = aggregates['avg'] or Decimal('0.00')
    self.review_count = aggregates['count']
    self.save(update_fields=['avg_rating', 'review_count', 'updated_at'])
```

**After:**
```python
# REMOVE this method - now handled by rating_aggregation service
```

**Update reviews app to call service:**
Find where `bean.update_aggregate_rating()` is called and replace with:
```python
from apps.beans.services import update_bean_rating

# Instead of:
# bean.update_aggregate_rating()

# Use:
transaction.on_commit(lambda: update_bean_rating(bean_id=bean.id))
```

---

## 📋 Phase 5: Deduplication Service (60 min)

### Task 5.1: Refactor Deduplication Service

**File:** `apps/beans/services/bean_deduplication.py`

**Move and refactor from existing `services.py`:**

```python
"""Bean deduplication service using fuzzy matching."""

from typing import List, Tuple, Optional
import re

from django.db.models import Q
from fuzzywuzzy import fuzz

from ..models import CoffeeBean


# Thresholds for fuzzy matching
EXACT_MATCH_THRESHOLD = 100
HIGH_SIMILARITY_THRESHOLD = 90
MEDIUM_SIMILARITY_THRESHOLD = 80


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    Args:
        text: Text to normalize

    Returns:
        Normalized lowercase text
    """
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s-]', '', text)
    return text


def find_potential_duplicates(
    *,
    name: str,
    roastery_name: str,
    threshold: int = MEDIUM_SIMILARITY_THRESHOLD
) -> List[Tuple[CoffeeBean, int, str]]:
    """
    Find potential duplicate beans using exact and fuzzy matching.

    Args:
        name: Bean name to check
        roastery_name: Roastery name to check
        threshold: Minimum similarity score (0-100)

    Returns:
        List of (bean, similarity_score, match_type) tuples
        match_type: 'exact', 'fuzzy_name', 'fuzzy_both'
    """
    name_norm = normalize_text(name)
    roastery_norm = normalize_text(roastery_name)

    candidates = []

    # Step 1: Check for exact normalized match
    exact_matches = CoffeeBean.objects.filter(
        name_normalized=name_norm,
        roastery_normalized=roastery_norm,
        is_active=True
    )

    for bean in exact_matches:
        candidates.append((bean, 100, 'exact'))

    # If exact match found, return immediately
    if candidates:
        return candidates

    # Step 2: Fuzzy matching on same roastery
    same_roastery = CoffeeBean.objects.filter(
        roastery_normalized=roastery_norm,
        is_active=True
    ).exclude(name_normalized=name_norm)

    for bean in same_roastery:
        name_similarity = fuzz.ratio(name_norm, bean.name_normalized)
        if name_similarity >= threshold:
            candidates.append((bean, name_similarity, 'fuzzy_name'))

    # Step 3: Fuzzy matching on both name and roastery
    all_beans = CoffeeBean.objects.filter(
        is_active=True
    ).exclude(
        roastery_normalized=roastery_norm
    )[:100]  # Limit for performance

    for bean in all_beans:
        name_similarity = fuzz.ratio(name_norm, bean.name_normalized)
        roastery_similarity = fuzz.ratio(roastery_norm, bean.roastery_normalized)

        # Combined score (weighted average: name 70%, roastery 30%)
        combined_score = int((name_similarity * 0.7) + (roastery_similarity * 0.3))

        if combined_score >= threshold:
            candidates.append((bean, combined_score, 'fuzzy_both'))

    # Sort by similarity score (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    return candidates[:10]  # Return top 10 matches


def batch_find_duplicates(
    *,
    threshold: int = HIGH_SIMILARITY_THRESHOLD
) -> List[dict]:
    """
    Scan entire database for potential duplicates.
    Used for admin cleanup tasks.

    Args:
        threshold: Minimum similarity score

    Returns:
        List of duplicate groups:
        [
            {
                'beans': [bean1, bean2],
                'similarity': int,
                'suggested_merge': (source_id, target_id)
            }
        ]
    """
    all_beans = CoffeeBean.objects.filter(is_active=True)

    # Group by normalized roastery first (performance optimization)
    from collections import defaultdict
    by_roastery = defaultdict(list)

    for bean in all_beans:
        by_roastery[bean.roastery_normalized].append(bean)

    duplicate_groups = []

    for roastery, beans in by_roastery.items():
        if len(beans) < 2:
            continue

        # Check each pair within same roastery
        checked = set()
        for i, bean1 in enumerate(beans):
            for bean2 in beans[i+1:]:
                pair_key = tuple(sorted([bean1.id, bean2.id]))
                if pair_key in checked:
                    continue
                checked.add(pair_key)

                similarity = fuzz.ratio(
                    bean1.name_normalized,
                    bean2.name_normalized
                )

                if similarity >= threshold:
                    # Suggest merging into bean with more reviews
                    if bean1.review_count >= bean2.review_count:
                        suggested = (bean2.id, bean1.id)  # (source, target)
                    else:
                        suggested = (bean1.id, bean2.id)

                    duplicate_groups.append({
                        'beans': [bean1, bean2],
                        'similarity': similarity,
                        'suggested_merge': suggested
                    })

    # Sort by similarity (highest first)
    duplicate_groups.sort(key=lambda x: x['similarity'], reverse=True)

    return duplicate_groups
```

**Export:**
```python
from .bean_deduplication import (
    find_potential_duplicates,
    batch_find_duplicates,
    normalize_text,
)
```

---

## 📋 Phase 6: Bean Merging Service (60 min)

### Task 6.1: Create Bean Merging Service

**File:** `apps/beans/services/bean_merging.py`

```python
"""Bean merging service with full transaction safety."""

from django.db import transaction
from django.contrib.auth import get_user_model
from uuid import UUID

from ..models import CoffeeBean, CoffeeBeanVariant, MergeHistory
from .exceptions import InvalidMergeError, BeanNotFoundError
from .rating_aggregation import update_bean_rating

User = get_user_model()


@transaction.atomic
def merge_beans(
    *,
    source_bean_id: UUID,
    target_bean_id: UUID,
    merged_by: User,
    reason: str = ''
) -> CoffeeBean:
    """
    Merge source bean into target bean with full concurrency protection.

    Process:
    1. Lock both beans
    2. Move all variants from source to target
    3. Update all reviews to point to target
    4. Update all purchases to point to target
    5. Update all library entries (handle duplicates)
    6. Recalculate target's aggregate rating
    7. Create merge history record
    8. Soft delete source bean

    Args:
        source_bean_id: Bean to be merged (will be soft-deleted)
        target_bean_id: Bean to merge into (will be kept)
        merged_by: User performing the merge
        reason: Optional reason for merge

    Returns:
        Updated target bean

    Raises:
        BeanNotFoundError: If either bean doesn't exist
        InvalidMergeError: If merge parameters are invalid
    """
    # Validate inputs
    if source_bean_id == target_bean_id:
        raise InvalidMergeError("Cannot merge bean with itself")

    # Lock both beans to prevent concurrent modifications
    try:
        source = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=source_bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Source bean {source_bean_id} not found")

    try:
        target = (
            CoffeeBean.objects
            .select_for_update()
            .get(id=target_bean_id)
        )
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Target bean {target_bean_id} not found")

    # Step 1: Move variants (handle duplicates)
    source_variants = CoffeeBeanVariant.objects.filter(coffeebean=source)
    for variant in source_variants:
        # Check if target already has this weight
        existing = CoffeeBeanVariant.objects.filter(
            coffeebean=target,
            package_weight_grams=variant.package_weight_grams
        ).first()

        if existing:
            # Keep variant with lower price per gram
            if variant.price_per_gram < existing.price_per_gram:
                existing.delete()
                variant.coffeebean = target
                variant.save()
            else:
                variant.delete()
        else:
            variant.coffeebean = target
            variant.save()

    # Step 2: Update reviews
    from apps.reviews.models import Review
    Review.objects.filter(coffeebean=source).update(coffeebean=target)

    # Step 3: Update purchases
    from apps.purchases.models import PurchaseRecord
    PurchaseRecord.objects.filter(coffeebean=source).update(coffeebean=target)

    # Step 4: Update library entries
    from apps.reviews.models import UserLibraryEntry
    from apps.groups.models import GroupLibraryEntry

    # User libraries - handle duplicates
    user_libs = UserLibraryEntry.objects.filter(coffeebean=source)
    for lib in user_libs:
        target_lib = UserLibraryEntry.objects.filter(
            user=lib.user,
            coffeebean=target
        ).first()

        if target_lib:
            # Keep the older entry
            lib.delete()
        else:
            lib.coffeebean = target
            lib.save()

    # Group libraries - handle duplicates
    group_libs = GroupLibraryEntry.objects.filter(coffeebean=source)
    for lib in group_libs:
        target_lib = GroupLibraryEntry.objects.filter(
            group=lib.group,
            coffeebean=target
        ).first()

        if target_lib:
            # Merge notes if any
            if lib.notes and not target_lib.notes:
                target_lib.notes = lib.notes
                target_lib.save()
            lib.delete()
        else:
            lib.coffeebean = target
            lib.save()

    # Step 5: Recalculate target's aggregate rating
    update_bean_rating(bean_id=target.id)
    target.refresh_from_db()

    # Step 6: Create merge history
    MergeHistory.objects.create(
        merged_from=source.id,
        merged_into=target,
        merged_by=merged_by,
        reason=reason
    )

    # Step 7: Soft delete source
    source.is_active = False
    source.name = f"[MERGED] {source.name}"
    source.save(update_fields=['is_active', 'name', 'updated_at'])

    return target
```

**Export:**
```python
from .bean_merging import merge_beans
```

---

## 📋 Phase 7: Variant Management Service (30 min)

### Task 7.1: Create Variant Management Service

**File:** `apps/beans/services/variant_management.py`

```python
"""Variant CRUD operations service."""

from django.db import transaction
from decimal import Decimal
from uuid import UUID
from typing import Optional

from ..models import CoffeeBeanVariant, CoffeeBean
from .exceptions import (
    VariantNotFoundError,
    DuplicateVariantError,
    BeanNotFoundError
)


@transaction.atomic
def create_variant(
    *,
    bean_id: UUID,
    package_weight_grams: int,
    price_czk: Decimal,
    purchase_url: str = ''
) -> CoffeeBeanVariant:
    """
    Create a new variant for a bean.

    Args:
        bean_id: Bean UUID
        package_weight_grams: Package size in grams
        price_czk: Price in CZK
        purchase_url: Optional purchase link

    Returns:
        Created variant

    Raises:
        BeanNotFoundError: If bean doesn't exist
        DuplicateVariantError: If variant already exists
    """
    # Check bean exists
    try:
        bean = CoffeeBean.objects.get(id=bean_id, is_active=True)
    except CoffeeBean.DoesNotExist:
        raise BeanNotFoundError(f"Bean {bean_id} not found")

    # Check for duplicate
    existing = CoffeeBeanVariant.objects.filter(
        coffeebean=bean,
        package_weight_grams=package_weight_grams,
        is_active=True
    ).first()

    if existing:
        raise DuplicateVariantError(
            f"Variant with {package_weight_grams}g already exists for this bean"
        )

    # Create variant
    variant = CoffeeBeanVariant.objects.create(
        coffeebean=bean,
        package_weight_grams=package_weight_grams,
        price_czk=price_czk,
        purchase_url=purchase_url
    )

    return variant


@transaction.atomic
def update_variant(
    *,
    variant_id: UUID,
    price_czk: Optional[Decimal] = None,
    purchase_url: Optional[str] = None
) -> CoffeeBeanVariant:
    """
    Update a variant.

    Args:
        variant_id: Variant UUID
        price_czk: New price (optional)
        purchase_url: New URL (optional)

    Returns:
        Updated variant

    Raises:
        VariantNotFoundError: If variant doesn't exist
    """
    try:
        variant = (
            CoffeeBeanVariant.objects
            .select_for_update()
            .get(id=variant_id, is_active=True)
        )
    except CoffeeBeanVariant.DoesNotExist:
        raise VariantNotFoundError(f"Variant {variant_id} not found")

    if price_czk is not None:
        variant.price_czk = price_czk

    if purchase_url is not None:
        variant.purchase_url = purchase_url

    variant.save()
    return variant


@transaction.atomic
def soft_delete_variant(*, variant_id: UUID) -> None:
    """
    Soft delete a variant.

    Args:
        variant_id: Variant UUID

    Raises:
        VariantNotFoundError: If variant doesn't exist
    """
    try:
        variant = (
            CoffeeBeanVariant.objects
            .select_for_update()
            .get(id=variant_id)
        )
    except CoffeeBeanVariant.DoesNotExist:
        raise VariantNotFoundError(f"Variant {variant_id} not found")

    variant.is_active = False
    variant.save(update_fields=['is_active', 'updated_at'])
```

**Export:**
```python
from .variant_management import (
    create_variant,
    update_variant,
    soft_delete_variant,
)
```

---

## 📋 Phase 8: Update Views & Tests (60 min)

### Task 8.1: Update CoffeeBeanVariantViewSet

**File:** `apps/beans/views.py`

Update variant viewset to use services:

```python
from .services import (
    create_variant,
    update_variant,
    soft_delete_variant,
    VariantNotFoundError,
    DuplicateVariantError,
)

class CoffeeBeanVariantViewSet(viewsets.ModelViewSet):
    # ... existing code ...

    def create(self, request, *args, **kwargs):
        """Create a new variant."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            variant = create_variant(**serializer.validated_data)
        except (BeanNotFoundError, DuplicateVariantError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = CoffeeBeanVariantSerializer(variant)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete a variant."""
        variant_id = kwargs.get('pk')

        try:
            soft_delete_variant(variant_id=variant_id)
        except VariantNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
```

---

### Task 8.2: Delete Old services.py

**Action:**
```bash
# Backup first
mv apps/beans/services.py apps/beans/services.py.old

# Verify new services work, then delete
rm apps/beans/services.py.old
```

---

### Task 8.3: Run Tests

```bash
pytest apps/beans/tests/ -v --tb=short
```

Fix any failing tests by updating them to use new services.

---

## 📋 Phase 9: Documentation (30 min)

### Task 9.1: Update Beans App Documentation

**File:** `docs/app-context/beans.md`

Add section after "Business Logic & Workflows":

```markdown
## Services Layer Architecture

**Purpose:** The beans app follows DRF best practices with a modular services layer.

### Service Structure

```
apps/beans/services/
├── __init__.py                   # Service exports
├── exceptions.py                 # Domain-specific exceptions
├── bean_management.py            # Bean CRUD operations
├── bean_search.py                # Search and filtering
├── bean_deduplication.py         # Duplicate detection
├── bean_merging.py               # Merge operations
├── variant_management.py         # Variant CRUD
└── rating_aggregation.py         # Rating calculations
```

### Service Files

**bean_management.py**
- `create_bean()` - Create with duplicate checking
- `update_bean()` - Update with concurrency protection
- `soft_delete_bean()` - Soft delete operation
- `get_bean_by_id()` - Retrieve with relations

**bean_search.py**
- `search_beans()` - Multi-field search and filtering
- `get_all_roasteries()` - List unique roasteries
- `get_all_origins()` - List unique origins

**bean_deduplication.py**
- `find_potential_duplicates()` - Fuzzy matching
- `batch_find_duplicates()` - Database-wide scan
- `normalize_text()` - Text normalization

**bean_merging.py**
- `merge_beans()` - Atomic merge with history

**variant_management.py**
- `create_variant()` - Create with duplicate checking
- `update_variant()` - Update with locking
- `soft_delete_variant()` - Soft delete

**rating_aggregation.py**
- `update_bean_rating()` - Recalculate with locking
- `get_top_rated_beans()` - Top beans by rating
- `get_most_reviewed_beans()` - Most reviewed beans

**exceptions.py**
- Domain exceptions: `BeanNotFoundError`, `DuplicateBeanError`
- Merge exceptions: `BeanMergeError`, `InvalidMergeError`
- Variant exceptions: `VariantNotFoundError`, `DuplicateVariantError`

### Transaction Safety

All state-changing operations use `@transaction.atomic`:
- Bean CRUD operations
- Variant CRUD operations
- Merge operations
- Rating updates

### Concurrency Protection

Critical operations use `select_for_update()`:
- Bean updates
- Variant updates
- Bean merging (locks both beans)
- Rating aggregation

### Architecture Benefits

1. **Modularity** - Each service file has single responsibility
2. **Testability** - Services can be unit tested independently
3. **Reusability** - Services used by views, tasks, admin
4. **Safety** - Transaction and concurrency protection
```

---

## ✅ Final Verification Checklist

Before considering refactoring complete:

- [ ] MergeHistory model created and migrated
- [ ] All service files created in services/ directory
- [ ] All services use @transaction.atomic where appropriate
- [ ] Critical operations use select_for_update()
- [ ] All views updated to use services
- [ ] Old services.py removed
- [ ] All tests updated and passing
- [ ] Documentation updated
- [ ] No business logic in views
- [ ] No business logic in model save() methods

---

## 📊 Success Metrics

**Code Quality:**
- ✅ Clear separation of concerns
- ✅ Modular service files (not monolithic)
- ✅ Views are thin (HTTP only)
- ✅ Models enforce domain rules only
- ✅ No business logic in serializers

**Safety:**
- ✅ Transaction protection on all mutations
- ✅ Concurrency protection on aggregates
- ✅ No race conditions in merges

**Testability:**
- ✅ Service unit tests
- ✅ API integration tests
- ✅ >80% coverage on services

---

## 🎉 Completion

Once all tasks are complete:

1. **Commit changes:**
```bash
git add apps/beans/
git commit -m "Refactor beans app to follow DRF best practices

- Restructure services into modular service layer
- Add transaction management with @transaction.atomic
- Add concurrency protection with select_for_update()
- Move business logic from views to services
- Move business logic from models to services
- Create MergeHistory model for audit trail
- Add domain-specific exceptions
- Update views to use services
- Add comprehensive documentation"
```

2. **Push to remote:**
```bash
git push origin claude/github-workflow-guide-ieUiF
```

---

**Total Estimated Time:** 6-8 hours

**Difficulty:** Medium

**Risk:** Low-Medium (existing deduplication logic needs careful migration)

**Benefit:** High (better architecture, safer merges, easier maintenance)
