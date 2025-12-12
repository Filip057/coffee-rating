import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.beans.models import CoffeeBean, CoffeeBeanVariant
from decimal import Decimal


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
        region='Yirgacheffe',
        processing='washed',
        roast_profile='light',
        created_by=user
    )


@pytest.mark.django_db
class TestBeanAPI:
    """Test CoffeeBean API endpoints."""
    
    def test_list_beans_unauthenticated(self, api_client, coffee_bean):
        """Test that unauthenticated users can list beans."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == 'Ethiopian Yirgacheffe'
    
    def test_create_bean_authenticated(self, authenticated_client):
        """Test creating a coffee bean."""
        url = reverse('beans:coffeebean-list')
        data = {
            'name': 'Colombian Supremo',
            'roastery_name': 'Coffee Co',
            'origin_country': 'Colombia',
            'region': 'Huila',
            'processing': 'washed',
            'roast_profile': 'medium',
            'brew_method': 'espresso',
            'description': 'Smooth and balanced',
            'tasting_notes': 'Chocolate, caramel, nuts'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Colombian Supremo'
        assert response.data['roastery_name'] == 'Coffee Co'
        
        # Verify in database
        assert CoffeeBean.objects.filter(name='Colombian Supremo').exists()
    
    def test_create_bean_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot create beans."""
        url = reverse('beans:coffeebean-list')
        data = {'name': 'Test Bean', 'roastery_name': 'Test'}
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_bean_detail(self, api_client, coffee_bean):
        """Test retrieving bean details."""
        url = reverse('beans:coffeebean-detail', kwargs={'pk': coffee_bean.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Ethiopian Yirgacheffe'
        assert response.data['roastery_name'] == 'Test Roasters'
    
    def test_update_bean(self, authenticated_client, coffee_bean):
        """Test updating a coffee bean."""
        url = reverse('beans:coffeebean-detail', kwargs={'pk': coffee_bean.id})
        data = {'description': 'Updated description'}
        
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['description'] == 'Updated description'
        
        coffee_bean.refresh_from_db()
        assert coffee_bean.description == 'Updated description'
    
    def test_delete_bean_soft_delete(self, authenticated_client, coffee_bean):
        """Test that deleting a bean sets is_active to False."""
        url = reverse('beans:coffeebean-detail', kwargs={'pk': coffee_bean.id})
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        coffee_bean.refresh_from_db()
        assert coffee_bean.is_active is False
    
    def test_search_beans(self, api_client, coffee_bean):
        """Test searching beans by name."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'search': 'Ethiopian'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_by_roastery(self, api_client, coffee_bean):
        """Test filtering beans by roastery."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'roastery': 'Test Roasters'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_by_origin(self, api_client, coffee_bean):
        """Test filtering beans by origin country."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'origin': 'Ethiopia'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_by_roast_profile(self, api_client, coffee_bean):
        """Test filtering beans by roast profile."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'roast_profile': 'light'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_get_roasteries_list(self, api_client, coffee_bean):
        """Test getting list of all roasteries."""
        url = reverse('beans:coffeebean-roasteries')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Test Roasters' in response.data
    
    def test_get_origins_list(self, api_client, coffee_bean):
        """Test getting list of all origin countries."""
        url = reverse('beans:coffeebean-origins')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Ethiopia' in response.data


@pytest.mark.django_db
class TestVariantAPI:
    """Test CoffeeBeanVariant API endpoints."""
    
    def test_create_variant(self, authenticated_client, coffee_bean):
        """Test creating a variant."""
        url = reverse('beans:variant-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'package_weight_grams': 250,
            'price_czk': '350.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['package_weight_grams'] == 250
        assert Decimal(response.data['price_czk']) == Decimal('350.00')
        
        # Check price_per_gram was calculated
        assert 'price_per_gram' in response.data
        assert Decimal(response.data['price_per_gram']) == Decimal('1.4000')
    
    def test_list_variants_for_bean(self, api_client, coffee_bean):
        """Test listing variants filtered by bean."""
        # Create variants
        CoffeeBeanVariant.objects.create(
            coffeebean=coffee_bean,
            package_weight_grams=250,
            price_czk=Decimal('350.00')
        )
        CoffeeBeanVariant.objects.create(
            coffeebean=coffee_bean,
            package_weight_grams=500,
            price_czk=Decimal('650.00')
        )
        
        url = reverse('beans:variant-list')
        response = api_client.get(url, {'coffeebean': str(coffee_bean.id)})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_variant_price_calculation(self, authenticated_client, coffee_bean):
        """Test that price per gram is calculated correctly."""
        url = reverse('beans:variant-list')
        data = {
            'coffeebean': str(coffee_bean.id),
            'package_weight_grams': 1000,
            'price_czk': '500.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        # 500 / 1000 = 0.5 per gram
        assert Decimal(response.data['price_per_gram']) == Decimal('0.5000')