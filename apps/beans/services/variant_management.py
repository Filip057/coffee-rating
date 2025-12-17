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
