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
        origin_country: Country of origin
        region: Specific region
        processing: Processing method
        roast_profile: Roast level
        roast_date: Date of roasting
        brew_method: Recommended brew method
        description: Detailed description
        tasting_notes: Flavor descriptors

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
