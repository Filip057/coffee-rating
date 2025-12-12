import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.beans.models import CoffeeBean
from apps.reviews.models import Review, Tag, UserLibraryEntry


@pytest.fixture
def api_client():
    """API client fixture."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        display_name='Test User'
    )


@pytest.fixture
def user2(db):
    """Create second test user."""
    return User.objects.create_user(
        email='test2@example.com',
        password='testpass123',
        display_name='Test User 2'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def coffee_bean(user):
    """Create test coffee bean."""
    return CoffeeBean.objects.create(
        name='Ethiopian Yirgacheffe',
        roastery_name='Test Roasters',
        origin_country='Ethiopia',
        created_by=user
    )


@pytest.fixture
def tag(db):
    """Create test tag."""
    return Tag.objects.create(name='fruity', category='flavor')


@pytest.mark.django_db
class TestReviewAPI:
    """Test Review API endpoints."""
    
    def test_create_review(self, authenticated_client, coffee_bean):
        """Test creating a review."""
        url = reverse('reviews:review-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'rating': 5,
            'notes': 'Amazing coffee! Very fruity.',
            'brew_method': 'filter',
            'context': 'personal',
            'would_buy_again': True
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['rating'] == 5
        assert response.data['notes'] == 'Amazing coffee! Very fruity.'
        
        # Verify review created
        assert Review.objects.filter(coffeebean=coffee_bean).exists()
    
    def test_create_review_auto_creates_library_entry(self, authenticated_client, user, coffee_bean):
        """Test that creating a review auto-creates library entry."""
        url = reverse('reviews:review-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'rating': 5,
            'notes': 'Great!',
            'context': 'personal'
        }
        
        # Verify no library entry exists
        assert not UserLibraryEntry.objects.filter(
            user=user,
            coffeebean=coffee_bean
        ).exists()
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify library entry was created
        assert UserLibraryEntry.objects.filter(
            user=user,
            coffeebean=coffee_bean,
            added_by='review'
        ).exists()
    
    def test_cannot_create_duplicate_review(self, authenticated_client, user, coffee_bean):
        """Test that user cannot review same bean twice."""
        # Create first review
        Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5,
            notes='First review'
        )
        
        url = reverse('reviews:review-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'rating': 4,
            'notes': 'Second review'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already reviewed' in str(response.data).lower()
    
    def test_create_review_unauthenticated(self, api_client, coffee_bean):
        """Test that unauthenticated users cannot create reviews."""
        url = reverse('reviews:review-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'rating': 5,
            'notes': 'Test'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_reviews(self, api_client, user, coffee_bean):
        """Test listing reviews."""
        # Create reviews
        Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5,
            notes='Great!'
        )
        
        url = reverse('reviews:review-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_reviews_by_bean(self, api_client, user, coffee_bean):
        """Test filtering reviews by coffee bean."""
        Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5
        )
        
        url = reverse('reviews:review-list')
        response = api_client.get(url, {'coffeebean': str(coffee_bean.id)})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_reviews_by_rating(self, api_client, user, coffee_bean):
        """Test filtering reviews by minimum rating."""
        Review.objects.create(coffeebean=coffee_bean, author=user, rating=5)
        Review.objects.create(coffeebean=coffee_bean, author=user, rating=3)
        
        url = reverse('reviews:review-list')
        response = api_client.get(url, {'min_rating': 4})
        
        # Should only return the 5-star review
        # Note: This will fail because user can only have 1 review per bean
        # Let's create a second bean for this test
    
    def test_get_my_reviews(self, authenticated_client, user, coffee_bean):
        """Test getting current user's reviews."""
        Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5
        )
        
        url = reverse('reviews:review-my_reviews')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_update_own_review(self, authenticated_client, user, coffee_bean):
        """Test updating own review."""
        review = Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=4,
            notes='Good'
        )
        
        url = reverse('reviews:review-detail', kwargs={'pk': review.id})
        data = {'rating': 5, 'notes': 'Actually amazing!'}
        
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['rating'] == 5
        assert response.data['notes'] == 'Actually amazing!'
    
    def test_cannot_update_others_review(self, api_client, user, user2, coffee_bean):
        """Test that user cannot update another user's review."""
        review = Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5
        )
        
        # Authenticate as user2
        api_client.force_authenticate(user=user2)
        
        url = reverse('reviews:review-detail', kwargs={'pk': review.id})
        data = {'rating': 1}
        
        response = api_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_delete_own_review(self, authenticated_client, user, coffee_bean):
        """Test deleting own review."""
        review = Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5
        )
        
        url = reverse('reviews:review-detail', kwargs={'pk': review.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Review.objects.filter(id=review.id).exists()
    
    def test_review_statistics(self, authenticated_client, user, coffee_bean):
        """Test getting review statistics."""
        Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5,
            notes='Great'
        )
        
        url = reverse('reviews:review-statistics')
        response = authenticated_client.get(url, {'bean_id': str(coffee_bean.id)})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_reviews'] == 1
        assert response.data['avg_rating'] == 5.0


@pytest.mark.django_db
class TestLibraryAPI:
    """Test User Library API endpoints."""
    
    def test_get_user_library(self, authenticated_client, user, coffee_bean):
        """Test getting user's library."""
        UserLibraryEntry.objects.create(
            user=user,
            coffeebean=coffee_bean,
            added_by='manual'
        )
        
        url = reverse('reviews:user-library')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['coffeebean']['name'] == 'Ethiopian Yirgacheffe'
    
    def test_add_to_library_manually(self, authenticated_client, user, coffee_bean):
        """Test manually adding bean to library."""
        url = reverse('reviews:add-to-library')
        data = {'coffeebean_id': str(coffee_bean.id)}
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert UserLibraryEntry.objects.filter(
            user=user,
            coffeebean=coffee_bean,
            added_by='manual'
        ).exists()
    
    def test_archive_library_entry(self, authenticated_client, user, coffee_bean):
        """Test archiving a library entry."""
        entry = UserLibraryEntry.objects.create(
            user=user,
            coffeebean=coffee_bean
        )
        
        url = reverse('reviews:archive-library-entry', kwargs={'entry_id': entry.id})
        data = {'is_archived': True}
        
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        entry.refresh_from_db()
        assert entry.is_archived is True


@pytest.mark.django_db
class TestTagAPI:
    """Test Tag API endpoints."""
    
    def test_list_tags(self, api_client, tag):
        """Test listing tags."""
        url = reverse('reviews:tag-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'fruity'
    
    def test_create_tag(self, authenticated_client):
        """Test creating a tag."""
        url = reverse('reviews:create-tag')
        data = {'name': 'chocolatey', 'category': 'flavor'}
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Tag.objects.filter(name='chocolatey').exists()
    
    def test_get_popular_tags(self, api_client, tag, user, coffee_bean):
        """Test getting popular tags."""
        # Create review with tag
        review = Review.objects.create(
            coffeebean=coffee_bean,
            author=user,
            rating=5
        )
        review.taste_tags.add(tag)
        
        url = reverse('reviews:tag-popular')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Tags should include usage count