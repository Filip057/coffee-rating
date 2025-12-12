import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from apps.beans.models import CoffeeBean, CoffeeBeanVariant


# =============================================================================
# CoffeeBean API Tests
# =============================================================================

@pytest.mark.django_db
class TestCoffeeBeanList:
    """Tests for GET /api/beans/"""

    def test_list_beans_unauthenticated(self, api_client, coffeebean):
        """Unauthenticated users can list beans."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == coffeebean.name

    def test_list_beans_excludes_inactive(self, api_client, coffeebean, coffeebean_inactive):
        """Inactive beans are not listed."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        names = [b['name'] for b in response.data['results']]
        assert coffeebean.name in names
        assert coffeebean_inactive.name not in names

    def test_list_beans_pagination(self, api_client, user, db):
        """Beans list is paginated."""
        # Create 25 beans (default page size is 20)
        for i in range(25):
            CoffeeBean.objects.create(
                name=f'Bean {i}',
                roastery_name=f'Roastery {i}',
                created_by=user,
            )

        url = reverse('beans:coffeebean-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 20
        assert response.data['count'] == 25
        assert response.data['next'] is not None


@pytest.mark.django_db
class TestCoffeeBeanFilters:
    """Tests for filtering coffee beans."""

    def test_filter_by_search(self, api_client, coffeebean, coffeebean_dark):
        """Search filter works across multiple fields."""
        url = reverse('beans:coffeebean-list')

        # Search by name
        response = api_client.get(url, {'search': 'Yirgacheffe'})
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == coffeebean.name

        # Search by roastery
        response = api_client.get(url, {'search': 'Dark Roasters'})
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == coffeebean_dark.name

    def test_filter_by_roastery(self, api_client, coffeebean, coffeebean_dark):
        """Filter by roastery name."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'roastery': 'Test Roastery'})

        assert len(response.data['results']) == 1
        assert response.data['results'][0]['roastery_name'] == 'Test Roastery'

    def test_filter_by_origin(self, api_client, coffeebean, coffeebean_dark):
        """Filter by origin country."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'origin': 'Ethiopia'})

        assert len(response.data['results']) == 1
        assert response.data['results'][0]['origin_country'] == 'Ethiopia'

    def test_filter_by_roast_profile(self, api_client, coffeebean, coffeebean_dark):
        """Filter by roast profile."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'roast_profile': 'dark'})

        assert len(response.data['results']) == 1
        assert response.data['results'][0]['roast_profile'] == 'dark'

    def test_filter_by_processing(self, api_client, coffeebean, coffeebean_dark):
        """Filter by processing method."""
        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'processing': 'natural'})

        assert len(response.data['results']) == 1
        # List serializer doesn't include processing, verify by name
        assert response.data['results'][0]['name'] == coffeebean_dark.name

    def test_filter_by_min_rating(self, api_client, coffeebean, coffeebean_dark, db):
        """Filter by minimum rating."""
        # Update rating for one bean
        coffeebean.avg_rating = Decimal('4.5')
        coffeebean.save()

        url = reverse('beans:coffeebean-list')
        response = api_client.get(url, {'min_rating': '4.0'})

        assert len(response.data['results']) == 1
        assert response.data['results'][0]['name'] == coffeebean.name


@pytest.mark.django_db
class TestCoffeeBeanCreate:
    """Tests for POST /api/beans/"""

    def test_create_bean_authenticated(self, authenticated_client, user):
        """Authenticated users can create beans."""
        url = reverse('beans:coffeebean-list')
        data = {
            'name': 'New Coffee',
            'roastery_name': 'New Roastery',
            'origin_country': 'Kenya',
            'roast_profile': 'medium',
            'processing': 'washed',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert CoffeeBean.objects.filter(name='New Coffee').exists()

        bean = CoffeeBean.objects.get(name='New Coffee')
        assert bean.created_by == user

    def test_create_bean_unauthenticated(self, api_client):
        """Unauthenticated users cannot create beans."""
        url = reverse('beans:coffeebean-list')
        data = {
            'name': 'New Coffee',
            'roastery_name': 'New Roastery',
        }
        response = api_client.post(url, data)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_create_bean_missing_required_fields(self, authenticated_client):
        """Creating bean without required fields fails."""
        url = reverse('beans:coffeebean-list')
        data = {'name': 'Only Name'}  # Missing roastery_name
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCoffeeBeanRetrieve:
    """Tests for GET /api/beans/{id}/"""

    def test_retrieve_bean(self, api_client, coffeebean):
        """Retrieve a single bean by ID."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == coffeebean.name
        assert response.data['roastery_name'] == coffeebean.roastery_name
        assert 'variants' in response.data

    def test_retrieve_inactive_bean(self, api_client, coffeebean_inactive):
        """Inactive beans cannot be retrieved."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean_inactive.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCoffeeBeanUpdate:
    """Tests for PUT/PATCH /api/beans/{id}/"""

    def test_partial_update_bean(self, authenticated_client, coffeebean):
        """Authenticated users can partially update beans."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
        data = {'description': 'Updated description'}
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        coffeebean.refresh_from_db()
        assert coffeebean.description == 'Updated description'

    def test_update_bean_unauthenticated(self, api_client, coffeebean):
        """Unauthenticated users cannot update beans."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
        data = {'description': 'Hacked'}
        response = api_client.patch(url, data)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestCoffeeBeanDelete:
    """Tests for DELETE /api/beans/{id}/"""

    def test_delete_bean_soft_deletes(self, authenticated_client, coffeebean):
        """Delete performs soft delete (sets is_active=False)."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        coffeebean.refresh_from_db()
        assert coffeebean.is_active is False
        # Bean still exists in DB
        assert CoffeeBean.objects.filter(id=coffeebean.id).exists()

    def test_delete_bean_unauthenticated(self, api_client, coffeebean):
        """Unauthenticated users cannot delete beans."""
        url = reverse('beans:coffeebean-detail', args=[coffeebean.id])
        response = api_client.delete(url)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestCoffeeBeanCustomActions:
    """Tests for custom actions on CoffeeBeanViewSet."""

    def test_roasteries_action(self, api_client, coffeebean, coffeebean_dark):
        """Get list of all roasteries."""
        url = reverse('beans:coffeebean-roasteries')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'Test Roastery' in response.data
        assert 'Dark Roasters' in response.data

    def test_origins_action(self, api_client, coffeebean, coffeebean_dark):
        """Get list of all origin countries."""
        url = reverse('beans:coffeebean-origins')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'Ethiopia' in response.data
        assert 'Brazil' in response.data

    def test_origins_excludes_empty(self, api_client, user, db):
        """Origins excludes beans with empty origin_country."""
        CoffeeBean.objects.create(
            name='No Origin',
            roastery_name='Mystery Roastery',
            origin_country='',
            created_by=user,
        )
        url = reverse('beans:coffeebean-origins')
        response = api_client.get(url)

        assert '' not in response.data


# =============================================================================
# CoffeeBeanVariant API Tests
# =============================================================================

@pytest.mark.django_db
class TestVariantList:
    """Tests for GET /api/beans/variants/"""

    def test_list_variants(self, api_client, variant, variant_large):
        """List all active variants."""
        url = reverse('beans:variant-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_list_variants_filter_by_coffeebean(self, api_client, coffeebean, coffeebean_dark, variant, db):
        """Filter variants by coffee bean ID."""
        # Create variant for dark bean
        CoffeeBeanVariant.objects.create(
            coffeebean=coffeebean_dark,
            package_weight_grams=500,
            price_czk=Decimal('450.00'),
        )

        url = reverse('beans:variant-list')
        response = api_client.get(url, {'coffeebean': str(coffeebean.id)})

        assert len(response.data) == 1
        assert str(response.data[0]['coffeebean']) == str(coffeebean.id)


@pytest.mark.django_db
class TestVariantCreate:
    """Tests for POST /api/beans/variants/"""

    def test_create_variant(self, authenticated_client, coffeebean):
        """Authenticated users can create variants."""
        url = reverse('beans:variant-list')
        data = {
            'coffeebean': str(coffeebean.id),
            'package_weight_grams': 500,
            'price_czk': '450.00',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert CoffeeBeanVariant.objects.filter(
            coffeebean=coffeebean,
            package_weight_grams=500
        ).exists()

    def test_create_variant_calculates_price_per_gram(self, authenticated_client, coffeebean):
        """Price per gram is calculated automatically."""
        url = reverse('beans:variant-list')
        data = {
            'coffeebean': str(coffeebean.id),
            'package_weight_grams': 250,
            'price_czk': '250.00',
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        # 250 CZK / 250g = 1.0 CZK/g
        assert Decimal(response.data['price_per_gram']) == Decimal('1.0000')

    def test_create_variant_unauthenticated(self, api_client, coffeebean):
        """Unauthenticated users cannot create variants."""
        url = reverse('beans:variant-list')
        data = {
            'coffeebean': str(coffeebean.id),
            'package_weight_grams': 500,
            'price_czk': '450.00',
        }
        response = api_client.post(url, data)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
class TestVariantRetrieve:
    """Tests for GET /api/beans/variants/{id}/"""

    def test_retrieve_variant(self, api_client, variant):
        """Retrieve a single variant by ID."""
        url = reverse('beans:variant-detail', args=[variant.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['package_weight_grams'] == variant.package_weight_grams
        assert Decimal(response.data['price_czk']) == variant.price_czk


@pytest.mark.django_db
class TestVariantUpdate:
    """Tests for PATCH /api/beans/variants/{id}/"""

    def test_update_variant(self, authenticated_client, variant):
        """Authenticated users can update variants."""
        url = reverse('beans:variant-detail', args=[variant.id])
        data = {'price_czk': '350.00'}
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        variant.refresh_from_db()
        assert variant.price_czk == Decimal('350.00')


@pytest.mark.django_db
class TestVariantDelete:
    """Tests for DELETE /api/beans/variants/{id}/"""

    def test_delete_variant_soft_deletes(self, authenticated_client, variant):
        """Delete performs soft delete."""
        url = reverse('beans:variant-detail', args=[variant.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        variant.refresh_from_db()
        assert variant.is_active is False
