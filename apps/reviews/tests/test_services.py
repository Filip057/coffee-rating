"""
Comprehensive service layer tests for reviews app.

Tests all service functions for:
- Review Management (create, get, update, delete)
- Library Management (add, remove, archive)
- Tag Management (create, get, search)
- Statistics (review stats, bean summaries)
- Concurrency protection (race conditions, lost updates)
"""

import pytest
import threading
from decimal import Decimal
from uuid import uuid4
from django.test import TransactionTestCase
from django.db import IntegrityError

from apps.reviews.services import (
    create_review,
    get_review_by_id,
    update_review,
    delete_review,
    get_user_reviews,
    add_to_library,
    remove_from_library,
    archive_library_entry,
    get_user_library,
    create_tag,
    get_tag_by_id,
    get_popular_tags,
    search_tags,
    get_review_statistics,
    get_bean_review_summary,
)
from apps.reviews.services.exceptions import (
    ReviewNotFoundError,
    DuplicateReviewError,
    InvalidRatingError,
    BeanNotFoundError,
    LibraryEntryNotFoundError,
    TagNotFoundError,
    UnauthorizedReviewActionError,
    InvalidContextError,
    GroupMembershipRequiredError,
)
from apps.reviews.models import Review, Tag, UserLibraryEntry


# ============================================================================
# REVIEW MANAGEMENT TESTS
# ============================================================================

@pytest.mark.django_db
class TestReviewManagement:
    """Test review CRUD operations."""

    def test_create_review_success(self, review_user, review_coffeebean):
        """Successfully create a review."""
        review = create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=5,
            aroma_score=4,
            flavor_score=5,
            notes="Excellent coffee!",
            brew_method="espresso",
        )

        assert review.id is not None
        assert review.author == review_user
        assert review.coffeebean == review_coffeebean
        assert review.rating == 5
        assert review.aroma_score == 4
        assert review.flavor_score == 5
        assert review.notes == "Excellent coffee!"
        assert review.brew_method == "espresso"

    def test_create_review_with_tags(self, review_user, review_coffeebean, tag_fruity, tag_chocolate):
        """Create review with taste tags."""
        review = create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=4,
            taste_tag_ids=[tag_fruity.id, tag_chocolate.id],
        )

        assert review.taste_tags.count() == 2
        assert tag_fruity in review.taste_tags.all()
        assert tag_chocolate in review.taste_tags.all()

    def test_create_review_duplicate_prevented(self, review_user, review_coffeebean):
        """Cannot create duplicate review for same bean."""
        # Create first review
        create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=5
        )

        # Try to create duplicate
        with pytest.raises(DuplicateReviewError) as exc:
            create_review(
                author=review_user,
                coffeebean_id=review_coffeebean.id,
                rating=4
            )

        assert "already reviewed" in str(exc.value)

    def test_create_review_invalid_rating_low(self, review_user, review_coffeebean):
        """Rating below 1 raises error."""
        with pytest.raises(InvalidRatingError) as exc:
            create_review(
                author=review_user,
                coffeebean_id=review_coffeebean.id,
                rating=0
            )

        assert "between 1 and 5" in str(exc.value)

    def test_create_review_invalid_rating_high(self, review_user, review_coffeebean):
        """Rating above 5 raises error."""
        with pytest.raises(InvalidRatingError):
            create_review(
                author=review_user,
                coffeebean_id=review_coffeebean.id,
                rating=6
            )

    def test_create_review_inactive_bean_rejected(self, review_user, review_coffeebean):
        """Inactive bean cannot be reviewed."""
        review_coffeebean.is_active = False
        review_coffeebean.save()

        with pytest.raises(BeanNotFoundError) as exc:
            create_review(
                author=review_user,
                coffeebean_id=review_coffeebean.id,
                rating=5
            )

        assert "not found or inactive" in str(exc.value)

    def test_create_review_nonexistent_bean(self, review_user):
        """Non-existent bean raises error."""
        fake_id = uuid4()

        with pytest.raises(BeanNotFoundError):
            create_review(
                author=review_user,
                coffeebean_id=fake_id,
                rating=5
            )

    def test_create_group_review_success(self, review_user, review_coffeebean, review_group):
        """Create review in group context."""
        review = create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=4,
            context='group',
            group_id=review_group.id
        )

        assert review.context == 'group'
        assert review.group == review_group

    def test_create_group_review_non_member_rejected(self, review_other_user, review_coffeebean, review_group):
        """Non-member cannot create group review."""
        with pytest.raises(GroupMembershipRequiredError) as exc:
            create_review(
                author=review_other_user,
                coffeebean_id=review_coffeebean.id,
                rating=4,
                context='group',
                group_id=review_group.id
            )

        assert "must be a member" in str(exc.value).lower()

    def test_create_group_review_missing_group_id(self, review_user, review_coffeebean):
        """Group context without group_id raises error."""
        with pytest.raises(InvalidContextError) as exc:
            create_review(
                author=review_user,
                coffeebean_id=review_coffeebean.id,
                rating=4,
                context='group',
                group_id=None
            )

        assert "required" in str(exc.value).lower()

    def test_get_review_by_id_success(self, review):
        """Successfully retrieve review by ID."""
        retrieved = get_review_by_id(review_id=review.id)

        assert retrieved.id == review.id
        assert retrieved.author == review.author
        assert retrieved.coffeebean == review.coffeebean

    def test_get_review_by_id_not_found(self):
        """Non-existent review raises error."""
        fake_id = uuid4()

        with pytest.raises(ReviewNotFoundError):
            get_review_by_id(review_id=fake_id)

    def test_update_review_success(self, review):
        """Successfully update review."""
        updated = update_review(
            review_id=review.id,
            user=review.author,
            rating=5,
            notes="Updated notes!",
            brew_method="aeropress"
        )

        assert updated.rating == 5
        assert updated.notes == "Updated notes!"
        assert updated.brew_method == "aeropress"

    def test_update_review_with_tags(self, review, tag_chocolate, tag_floral):
        """Update review tags."""
        updated = update_review(
            review_id=review.id,
            user=review.author,
            taste_tag_ids=[tag_chocolate.id, tag_floral.id]
        )

        assert updated.taste_tags.count() == 2
        assert tag_chocolate in updated.taste_tags.all()
        assert tag_floral in updated.taste_tags.all()

    def test_update_review_unauthorized(self, review, review_other_user):
        """Cannot update another user's review."""
        with pytest.raises(UnauthorizedReviewActionError) as exc:
            update_review(
                review_id=review.id,
                user=review_other_user,
                rating=1
            )

        assert "only update your own" in str(exc.value).lower()

    def test_update_review_invalid_rating(self, review):
        """Invalid rating in update raises error."""
        with pytest.raises(InvalidRatingError):
            update_review(
                review_id=review.id,
                user=review.author,
                rating=10
            )

    def test_delete_review_success(self, review):
        """Successfully delete review."""
        review_id = review.id

        delete_review(review_id=review_id, user=review.author)

        # Verify deleted
        with pytest.raises(ReviewNotFoundError):
            get_review_by_id(review_id=review_id)

    def test_delete_review_unauthorized(self, review, review_other_user):
        """Cannot delete another user's review."""
        with pytest.raises(UnauthorizedReviewActionError):
            delete_review(review_id=review.id, user=review_other_user)

    def test_delete_review_not_found(self, review_user):
        """Deleting non-existent review raises error."""
        fake_id = uuid4()

        with pytest.raises(ReviewNotFoundError):
            delete_review(review_id=fake_id, user=review_user)

    def test_get_user_reviews(self, review_user, review, review_another_coffeebean):
        """Get all reviews by user."""
        # Create another review
        create_review(
            author=review_user,
            coffeebean_id=review_another_coffeebean.id,
            rating=3
        )

        reviews = get_user_reviews(user=review_user)

        assert reviews.count() == 2
        assert review in reviews


# ============================================================================
# LIBRARY MANAGEMENT TESTS
# ============================================================================

@pytest.mark.django_db
class TestLibraryManagement:
    """Test user library operations."""

    def test_add_to_library_success(self, review_user, review_coffeebean):
        """Successfully add bean to library."""
        entry, created = add_to_library(
            user=review_user,
            coffeebean_id=review_coffeebean.id,
            added_by='manual'
        )

        assert created is True
        assert entry.user == review_user
        assert entry.coffeebean == review_coffeebean
        assert entry.added_by == 'manual'

    def test_add_to_library_duplicate_idempotent(self, review_user, review_coffeebean):
        """Adding duplicate bean is idempotent."""
        # Add first time
        entry1, created1 = add_to_library(
            user=review_user,
            coffeebean_id=review_coffeebean.id,
            added_by='manual'
        )

        assert created1 is True

        # Add again (should return existing)
        entry2, created2 = add_to_library(
            user=review_user,
            coffeebean_id=review_coffeebean.id,
            added_by='review'  # Different added_by should be ignored
        )

        assert created2 is False
        assert entry1.id == entry2.id
        assert entry2.added_by == 'manual'  # Original value preserved

    def test_add_to_library_inactive_bean_rejected(self, review_user, review_coffeebean):
        """Cannot add inactive bean to library."""
        review_coffeebean.is_active = False
        review_coffeebean.save()

        with pytest.raises(BeanNotFoundError):
            add_to_library(
                user=review_user,
                coffeebean_id=review_coffeebean.id
            )

    def test_remove_from_library_success(self, review_library_entry):
        """Successfully remove bean from library."""
        entry_id = review_library_entry.id
        user = review_library_entry.user

        remove_from_library(entry_id=entry_id, user=user)

        # Verify deleted
        assert not UserLibraryEntry.objects.filter(id=entry_id).exists()

    def test_remove_from_library_unauthorized(self, review_library_entry, review_other_user):
        """Cannot remove another user's library entry."""
        with pytest.raises(LibraryEntryNotFoundError) as exc:
            remove_from_library(
                entry_id=review_library_entry.id,
                user=review_other_user
            )

        assert "not found" in str(exc.value).lower()

    def test_remove_from_library_not_found(self, review_user):
        """Removing non-existent entry raises error."""
        fake_id = uuid4()

        with pytest.raises(LibraryEntryNotFoundError):
            remove_from_library(entry_id=fake_id, user=review_user)

    def test_archive_library_entry_success(self, review_library_entry):
        """Successfully archive library entry."""
        entry = archive_library_entry(
            entry_id=review_library_entry.id,
            user=review_library_entry.user,
            is_archived=True
        )

        assert entry.is_archived is True

    def test_unarchive_library_entry_success(self, review_archived_library_entry):
        """Successfully unarchive library entry."""
        entry = archive_library_entry(
            entry_id=review_archived_library_entry.id,
            user=review_archived_library_entry.user,
            is_archived=False
        )

        assert entry.is_archived is False

    def test_archive_library_entry_unauthorized(self, review_library_entry, review_other_user):
        """Cannot archive another user's entry."""
        with pytest.raises(LibraryEntryNotFoundError):
            archive_library_entry(
                entry_id=review_library_entry.id,
                user=review_other_user,
                is_archived=True
            )

    def test_get_user_library_active(self, review_user, review_library_entry, review_archived_library_entry):
        """Get user's active library entries."""
        library = get_user_library(
            user=review_user,
            is_archived=False
        )

        assert library.count() == 1
        assert review_library_entry in library
        assert review_archived_library_entry not in library

    def test_get_user_library_archived(self, review_user, review_library_entry, review_archived_library_entry):
        """Get user's archived library entries."""
        library = get_user_library(
            user=review_user,
            is_archived=True
        )

        assert library.count() == 1
        assert review_archived_library_entry in library
        assert review_library_entry not in library

    def test_get_user_library_search(self, review_user, review_coffeebean, review_another_coffeebean):
        """Search user's library."""
        add_to_library(user=review_user, coffeebean_id=review_coffeebean.id)
        add_to_library(user=review_user, coffeebean_id=review_another_coffeebean.id)

        # Search for "Ethiopia"
        library = get_user_library(user=review_user, search="Ethiopia")

        assert library.count() == 1
        assert library.first().coffeebean == review_coffeebean


# ============================================================================
# TAG MANAGEMENT TESTS
# ============================================================================

@pytest.mark.django_db
class TestTagManagement:
    """Test tag operations."""

    def test_create_tag_success(self):
        """Successfully create a tag."""
        tag = create_tag(name="nutty", category="flavor")

        assert tag.id is not None
        assert tag.name == "nutty"
        assert tag.category == "flavor"

    def test_create_tag_duplicate_error(self, tag_fruity):
        """Duplicate tag name raises IntegrityError."""
        with pytest.raises(IntegrityError):
            create_tag(name="fruity", category="flavor")

    def test_get_tag_by_id_success(self, tag_fruity):
        """Successfully retrieve tag by ID."""
        tag = get_tag_by_id(tag_id=tag_fruity.id)

        assert tag.id == tag_fruity.id
        assert tag.name == tag_fruity.name

    def test_get_tag_by_id_not_found(self):
        """Non-existent tag raises error."""
        fake_id = uuid4()

        with pytest.raises(TagNotFoundError):
            get_tag_by_id(tag_id=fake_id)

    def test_get_popular_tags(self, review_user, review_coffeebean, review_another_coffeebean, tag_fruity, tag_chocolate, tag_floral):
        """Get most popular tags by usage count."""
        # Create reviews with tags
        review1 = create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=5,
            taste_tag_ids=[tag_fruity.id, tag_chocolate.id]
        )

        review2 = create_review(
            author=review_user,
            coffeebean_id=review_another_coffeebean.id,
            rating=4,
            taste_tag_ids=[tag_fruity.id]  # fruity used twice
        )

        tags = get_popular_tags(limit=3)

        # fruity should be first (used 2 times)
        assert tags.count() == 2  # Only 2 tags actually used
        assert tags[0].name == tag_fruity.name

    def test_search_tags_by_name(self, tag_fruity, tag_floral):
        """Search tags by name."""
        tags = search_tags(search="fru")

        assert tags.count() == 1
        assert tags.first() == tag_fruity

    def test_search_tags_by_category(self, tag_fruity, tag_chocolate, tag_floral):
        """Search tags by category."""
        tags = search_tags(category="flavor")

        assert tags.count() == 2
        assert tag_fruity in tags
        assert tag_chocolate in tags
        assert tag_floral not in tags

    def test_search_tags_combined(self, tag_fruity, tag_floral):
        """Search tags by name and category."""
        tags = search_tags(search="fl", category="aroma")

        assert tags.count() == 1
        assert tags.first() == tag_floral


# ============================================================================
# STATISTICS TESTS
# ============================================================================

@pytest.mark.django_db
class TestStatistics:
    """Test analytics and statistics."""

    def test_get_review_statistics_all(self, review_user, review_coffeebean, review_another_coffeebean):
        """Calculate statistics for all reviews."""
        # Create reviews with different ratings
        create_review(author=review_user, coffeebean_id=review_coffeebean.id, rating=5)
        create_review(author=review_user, coffeebean_id=review_another_coffeebean.id, rating=3)

        stats = get_review_statistics()

        assert stats['total_reviews'] == 2
        assert stats['avg_rating'] == 4.0  # (5 + 3) / 2
        assert stats['rating_distribution']['5'] == 1
        assert stats['rating_distribution']['3'] == 1

    def test_get_review_statistics_by_user(self, review_user, review_other_user, review_coffeebean, review_another_coffeebean):
        """Calculate statistics filtered by user."""
        create_review(author=review_user, coffeebean_id=review_coffeebean.id, rating=5)
        create_review(author=review_other_user, coffeebean_id=review_another_coffeebean.id, rating=3)

        stats = get_review_statistics(user_id=review_user.id)

        assert stats['total_reviews'] == 1
        assert stats['avg_rating'] == 5.0

    def test_get_review_statistics_by_bean(self, review_user, review_other_user, review_coffeebean):
        """Calculate statistics filtered by bean."""
        create_review(author=review_user, coffeebean_id=review_coffeebean.id, rating=5)
        create_review(author=review_other_user, coffeebean_id=review_coffeebean.id, rating=4)

        stats = get_review_statistics(bean_id=review_coffeebean.id)

        assert stats['total_reviews'] == 2
        assert stats['avg_rating'] == 4.5  # (5 + 4) / 2

    def test_get_review_statistics_empty(self):
        """Statistics with no reviews returns zeros."""
        stats = get_review_statistics()

        assert stats['total_reviews'] == 0
        assert stats['avg_rating'] == 0.0

    def test_get_bean_review_summary_success(self, review_user, review_coffeebean, tag_fruity):
        """Get comprehensive review summary for bean."""
        create_review(
            author=review_user,
            coffeebean_id=review_coffeebean.id,
            rating=5,
            taste_tag_ids=[tag_fruity.id]
        )

        summary = get_bean_review_summary(bean_id=review_coffeebean.id)

        assert summary['bean_id'] == str(review_coffeebean.id)
        assert "Ethiopia" in summary['bean_name']
        assert summary['total_reviews'] == 1
        assert float(summary['avg_rating']) > 0
        assert summary['rating_breakdown']['5'] == 1

    def test_get_bean_review_summary_inactive_bean(self, review_coffeebean):
        """Inactive bean raises error."""
        review_coffeebean.is_active = False
        review_coffeebean.save()

        with pytest.raises(BeanNotFoundError):
            get_bean_review_summary(bean_id=review_coffeebean.id)

    def test_get_bean_review_summary_not_found(self):
        """Non-existent bean raises error."""
        fake_id = uuid4()

        with pytest.raises(BeanNotFoundError):
            get_bean_review_summary(bean_id=fake_id)


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

class TestConcurrency(TransactionTestCase):
    """Test concurrency protection with real database transactions."""

    def setUp(self):
        """Set up test data for concurrency tests."""
        from apps.accounts.models import User
        from apps.beans.models import CoffeeBean

        self.user = User.objects.create_user(
            email='concurrent@example.com',
            password='TestPass123!',
            email_verified=True
        )

        self.bean = CoffeeBean.objects.create(
            name='Concurrent Test Bean',
            roastery_name='Test Roastery',
            origin_country='Colombia',
            roast_profile='medium',
            created_by=self.user
        )

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
        assert Review.objects.filter(
            author=self.user,
            coffeebean=self.bean
        ).count() == 1

    def test_concurrent_library_additions_idempotent(self):
        """Multiple concurrent library additions handled gracefully."""
        results = []

        def add_in_thread():
            entry, created = add_to_library(
                user=self.user,
                coffeebean_id=self.bean.id,
                added_by='concurrent'
            )
            results.append((entry, created))

        # Spawn 5 threads trying to add same bean
        threads = [
            threading.Thread(target=add_in_thread)
            for _ in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should complete successfully
        assert len(results) == 5

        # Exactly one should have created=True
        created_count = sum(1 for _, created in results if created)
        assert created_count == 1

        # All should return same entry
        entry_ids = {entry.id for entry, _ in results}
        assert len(entry_ids) == 1

        # Only one entry exists in database
        assert UserLibraryEntry.objects.filter(
            user=self.user,
            coffeebean=self.bean
        ).count() == 1

    def test_concurrent_review_updates_no_lost_updates(self):
        """Concurrent review updates serialize correctly."""
        # Create review
        review = create_review(
            author=self.user,
            coffeebean_id=self.bean.id,
            rating=3
        )

        results = []

        def update_in_thread(new_rating):
            updated = update_review(
                review_id=review.id,
                user=self.user,
                rating=new_rating
            )
            results.append(updated.rating)

        # Spawn threads updating to different ratings
        threads = [
            threading.Thread(target=update_in_thread, args=(i,))
            for i in [4, 5, 5, 4, 5]
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All updates should complete
        assert len(results) == 5

        # Final rating should be one of the update values
        review.refresh_from_db()
        assert review.rating in [4, 5]

        # No updates lost (all 5 results recorded)
        assert len(results) == 5
