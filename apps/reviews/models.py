# ==========================================
# apps/reviews/models.py
# ==========================================

from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from apps.beans.models import CoffeeBean

class ReviewContext(models.TextChoices):
    PERSONAL = 'personal', 'Personal'
    GROUP = 'group', 'Group/Team'
    PUBLIC = 'public', 'Public'


class Tag(models.Model):
    """Taste tags."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tags'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Review(models.Model):
    """User review/rating."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coffeebean = models.ForeignKey('beans.CoffeeBean', on_delete=models.CASCADE, related_name='reviews')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    aroma_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    flavor_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    acidity_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    body_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    aftertaste_score = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    notes = models.TextField(blank=True)
    brew_method = models.CharField(max_length=50, blank=True)
    taste_tags = models.ManyToManyField(Tag, blank=True, related_name='reviews')
    context = models.CharField(max_length=20, choices=ReviewContext.choices, default=ReviewContext.PERSONAL)
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='reviews')
    would_buy_again = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reviews'
        unique_together = [['author', 'coffeebean']]
        indexes = [
            models.Index(fields=['coffeebean', 'rating']),
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['group', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author.get_display_name()} - {self.coffeebean.name} ({self.rating}★)"


class UserLibraryEntry(models.Model):
    """User's personal coffee library."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='library_entries')
    coffeebean = models.ForeignKey('beans.CoffeeBean', on_delete=models.CASCADE, related_name='user_libraries')
    added_by = models.CharField(max_length=20, choices=[('review', 'From Review'), ('purchase', 'From Purchase'), ('manual', 'Manual Add')], default='review')
    added_at = models.DateTimeField(auto_now_add=True)
    own_price_czk = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'user_library_entries'
        unique_together = [['user', 'coffeebean']]
        indexes = [
            models.Index(fields=['user', 'added_at']),
            models.Index(fields=['user', 'is_archived']),
        ]
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.get_display_name()} - {self.coffeebean.name}"

    @classmethod
    def ensure_entry(cls, user, coffeebean, added_by='manual'):
        """
        Get or create a library entry for user and coffeebean.

        Args:
            user: The user
            coffeebean: The coffee bean
            added_by: How the entry was added ('review', 'purchase', 'manual')

        Returns:
            Tuple of (entry, created) where created is True if new entry was created
        """
        return cls.objects.get_or_create(
            user=user,
            coffeebean=coffeebean,
            defaults={'added_by': added_by}
        )
