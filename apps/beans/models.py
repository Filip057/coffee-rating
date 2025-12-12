# ==========================================
# apps/coffeebeans/models.py
# ==========================================

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
import re


class BrewMethod(models.TextChoices):
    ESPRESSO = 'espresso', 'Espresso'
    FILTER = 'filter', 'Filter/Pour Over'
    FRENCH_PRESS = 'french_press', 'French Press'
    AEROPRESS = 'aeropress', 'AeroPress'
    MOKA = 'moka', 'Moka Pot'
    COLD_BREW = 'cold_brew', 'Cold Brew'
    OTHER = 'other', 'Other'
    AUTOMAT = 'automat', 'Automat'


class RoastProfile(models.TextChoices):
    LIGHT = 'light', 'Light'
    MEDIUM_LIGHT = 'medium_light', 'Medium-Light'
    MEDIUM = 'medium', 'Medium'
    MEDIUM_DARK = 'medium_dark', 'Medium-Dark'
    DARK = 'dark', 'Dark'


class ProcessingMethod(models.TextChoices):
    WASHED = 'washed', 'Washed'
    NATURAL = 'natural', 'Natural/Dry'
    HONEY = 'honey', 'Honey'
    ANAEROBIC = 'anaerobic', 'Anaerobic'
    OTHER = 'other', 'Other'


class CoffeeBean(models.Model):
    """Canonical coffee product."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    roastery_name = models.CharField(max_length=200, db_index=True)
    name_normalized = models.CharField(max_length=200, db_index=True, editable=False)
    roastery_normalized = models.CharField(max_length=200, db_index=True, editable=False)
    origin_country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=200, blank=True)
    processing = models.CharField(max_length=50, choices=ProcessingMethod.choices, default=ProcessingMethod.WASHED)
    roast_profile = models.CharField(max_length=50, choices=RoastProfile.choices, default=RoastProfile.MEDIUM)
    roast_date = models.DateField(null=True, blank=True)
    brew_method = models.CharField(max_length=50, choices=BrewMethod.choices, default=BrewMethod.FILTER)
    description = models.TextField(blank=True)
    tasting_notes = models.CharField(max_length=500, blank=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    review_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_beans')
    
    class Meta:
        db_table = 'coffeebeans'
        unique_together = [['name_normalized', 'roastery_normalized']]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['roastery_name']),
            models.Index(fields=['name_normalized', 'roastery_normalized']),
            models.Index(fields=['avg_rating']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.roastery_name} - {self.name}"
    
    def save(self, *args, **kwargs):
        self.name_normalized = self._normalize_string(self.name)
        self.roastery_normalized = self._normalize_string(self.roastery_name)
        super().save(*args, **kwargs)
    
    @staticmethod
    def _normalize_string(text):
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s-]', '', text)
        return text
    
    def update_aggregate_rating(self):
        from django.db.models import Avg, Count
        aggregates = self.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        self.avg_rating = aggregates['avg'] or Decimal('0.00')
        self.review_count = aggregates['count']
        self.save(update_fields=['avg_rating', 'review_count', 'updated_at'])


class CoffeeBeanVariant(models.Model):
    """Package size and pricing."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coffeebean = models.ForeignKey(CoffeeBean, on_delete=models.CASCADE, related_name='variants')
    package_weight_grams = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_czk = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    price_per_gram = models.DecimalField(max_digits=10, decimal_places=4, editable=False)
    purchase_url = models.URLField(blank=True, max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'coffeebean_variants'
        unique_together = [['coffeebean', 'package_weight_grams']]
        indexes = [
            models.Index(fields=['coffeebean', 'is_active']),
            models.Index(fields=['price_per_gram']),
        ]
        ordering = ['package_weight_grams']
    
    def __str__(self):
        return f"{self.coffeebean.name} - {self.package_weight_grams}g"
    
    def save(self, *args, **kwargs):
        if self.price_czk and self.package_weight_grams:
            self.price_per_gram = self.price_czk / Decimal(self.package_weight_grams)
        super().save(*args, **kwargs)