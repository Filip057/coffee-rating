import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from apps.analytics.analytics import AnalyticsQueries
from apps.analytics.exceptions import InvalidMetricError, MissingParameterError
from apps.purchases.models import PaymentStatus


# =============================================================================
# User Consumption Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestUserConsumption:
    """Tests for GET /api/analytics/user/consumption/ and /user/{id}/consumption/"""

    def test_my_consumption(self, analytics_user_client, analytics_personal_purchase):
        """Get current user's consumption."""
        url = reverse('analytics:my-consumption')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total_kg' in response.data
        assert 'total_spent_czk' in response.data
        assert 'purchases_count' in response.data
        assert 'avg_price_per_kg' in response.data

    def test_my_consumption_shows_correct_values(
        self, analytics_user_client, analytics_personal_purchase
    ):
        """Verify consumption values are correct."""
        url = reverse('analytics:my-consumption')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # 500 CZK, 500g = 0.5kg
        assert Decimal(str(response.data['total_spent_czk'])) == Decimal('500.00')
        assert response.data['purchases_count'] >= 1

    def test_user_consumption_by_id(
        self, analytics_user_client, analytics_user, analytics_personal_purchase
    ):
        """Get specific user's consumption by ID."""
        url = reverse('analytics:user-consumption', args=[analytics_user.id])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total_spent_czk' in response.data

    def test_consumption_with_period_filter(
        self, analytics_user_client, analytics_personal_purchase
    ):
        """Filter consumption by period (YYYY-MM)."""
        url = reverse('analytics:my-consumption')
        period = date.today().strftime('%Y-%m')
        response = analytics_user_client.get(url, {'period': period})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['period_start'] is not None

    def test_consumption_with_date_range(
        self, analytics_user_client, analytics_personal_purchase
    ):
        """Filter consumption by date range."""
        url = reverse('analytics:my-consumption')
        start = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        end = date.today().strftime('%Y-%m-%d')
        response = analytics_user_client.get(url, {
            'start_date': start,
            'end_date': end,
        })

        assert response.status_code == status.HTTP_200_OK

    def test_consumption_invalid_period(self, analytics_user_client):
        """Invalid period format returns 400."""
        url = reverse('analytics:my-consumption')
        response = analytics_user_client.get(url, {'period': 'invalid'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Serializer validation returns field-specific errors
        assert 'period' in response.data

    def test_consumption_unauthenticated(self, api_client):
        """Unauthenticated users cannot access consumption."""
        url = reverse('analytics:my-consumption')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_consumption_nonexistent_user(self, analytics_user_client):
        """Non-existent user returns 404."""
        import uuid
        url = reverse('analytics:user-consumption', args=[uuid.uuid4()])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Group Consumption Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestGroupConsumption:
    """Tests for GET /api/analytics/group/{id}/consumption/"""

    def test_group_consumption(
        self, analytics_user_client, analytics_group, analytics_group_purchase
    ):
        """Get group consumption as member."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'total_kg' in response.data
        assert 'total_spent_czk' in response.data
        assert 'purchases_count' in response.data
        assert 'member_breakdown' in response.data

    def test_group_consumption_shows_correct_totals(
        self, analytics_user_client, analytics_group, analytics_group_purchase
    ):
        """Verify group consumption totals."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # 900 CZK, 1000g = 1kg
        assert Decimal(str(response.data['total_spent_czk'])) == Decimal('900.00')
        assert response.data['purchases_count'] == 1

    def test_group_consumption_member_breakdown(
        self, analytics_user_client, analytics_group, analytics_group_purchase
    ):
        """Verify member breakdown in group consumption."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['member_breakdown']) == 3  # 3 members

        # Each member should have serialized user data and share info
        for member in response.data['member_breakdown']:
            assert 'share_percentage' in member
            assert 'czk' in member  # Changed from 'total_spent_czk'
            assert 'kg' in member
            assert 'user' in member
            # User should be serialized as dict
            assert 'id' in member['user']
            assert 'display_name' in member['user']

    def test_group_consumption_non_member(
        self, analytics_outsider_client, analytics_group, analytics_group_purchase
    ):
        """Non-members cannot access group consumption."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        response = analytics_outsider_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Permission class returns 'detail' key
        assert 'detail' in response.data

    def test_group_consumption_with_date_range(
        self, analytics_user_client, analytics_group, analytics_group_purchase
    ):
        """Filter group consumption by date range."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        start = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        end = date.today().strftime('%Y-%m-%d')
        response = analytics_user_client.get(url, {
            'start_date': start,
            'end_date': end,
        })

        assert response.status_code == status.HTTP_200_OK

    def test_group_consumption_unauthenticated(self, api_client, analytics_group):
        """Unauthenticated users cannot access group consumption."""
        url = reverse('analytics:group-consumption', args=[analytics_group.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Top Beans Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestTopBeans:
    """Tests for GET /api/analytics/beans/top/"""

    def test_top_beans_default(
        self, api_client, analytics_bean1, analytics_bean2, analytics_bean3
    ):
        """Get top beans with default parameters (public endpoint)."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'metric' in response.data
        assert 'results' in response.data
        assert response.data['metric'] == 'rating'

    def test_top_beans_by_rating(
        self, api_client, analytics_bean1, analytics_bean2, analytics_bean3
    ):
        """Get top beans by rating metric."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'metric': 'rating'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['metric'] == 'rating'
        # Beans with min 3 reviews should be included
        for result in response.data['results']:
            assert 'avg_rating' in result or 'score' in result

    def test_top_beans_by_kg(
        self, api_client, analytics_personal_purchase, analytics_group_purchase
    ):
        """Get top beans by kilograms purchased."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'metric': 'kg'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['metric'] == 'kg'

    def test_top_beans_by_money(
        self, api_client, analytics_personal_purchase, analytics_group_purchase
    ):
        """Get top beans by money spent."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'metric': 'money'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['metric'] == 'money'

    def test_top_beans_by_reviews(
        self, api_client, analytics_bean1, analytics_bean2, analytics_bean3
    ):
        """Get top beans by review count."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'metric': 'reviews'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['metric'] == 'reviews'
        # Beans should be sorted by review count
        for result in response.data['results']:
            assert 'review_count' in result

    def test_top_beans_with_limit(self, api_client, analytics_bean1, analytics_bean2):
        """Limit number of results."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'limit': 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) <= 2

    def test_top_beans_with_period(self, api_client, analytics_personal_purchase):
        """Filter top beans by period."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'metric': 'kg', 'period': 30})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['period_days'] == 30

    def test_top_beans_invalid_params(self, api_client):
        """Invalid parameters return 400."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url, {'limit': 'invalid'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_top_beans_public_access(self, api_client):
        """Top beans is publicly accessible (no auth required)."""
        url = reverse('analytics:top-beans')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Consumption Timeseries Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestConsumptionTimeseries:
    """Tests for GET /api/analytics/timeseries/"""

    def test_user_timeseries(
        self, analytics_user_client, analytics_personal_purchase, analytics_old_purchase
    ):
        """Get user consumption timeseries."""
        url = reverse('analytics:consumption-timeseries')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'granularity' in response.data
        assert 'data' in response.data
        assert response.data['granularity'] == 'month'

    def test_timeseries_data_structure(
        self, analytics_user_client, analytics_personal_purchase
    ):
        """Verify timeseries data structure."""
        url = reverse('analytics:consumption-timeseries')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        if response.data['data']:
            item = response.data['data'][0]
            assert 'period' in item
            assert 'kg' in item
            assert 'czk' in item
            assert 'purchases_count' in item

    def test_group_timeseries(
        self, analytics_user_client, analytics_group, analytics_group_purchase
    ):
        """Get group consumption timeseries."""
        url = reverse('analytics:consumption-timeseries')
        response = analytics_user_client.get(url, {'group_id': str(analytics_group.id)})

        assert response.status_code == status.HTTP_200_OK
        assert 'data' in response.data

    def test_timeseries_non_member_group(
        self, analytics_outsider_client, analytics_group
    ):
        """Non-members cannot access group timeseries."""
        url = reverse('analytics:consumption-timeseries')
        response = analytics_outsider_client.get(url, {
            'group_id': str(analytics_group.id)
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_timeseries_unauthenticated(self, api_client):
        """Unauthenticated users cannot access timeseries."""
        url = reverse('analytics:consumption-timeseries')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Taste Profile Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestTasteProfile:
    """Tests for GET /api/analytics/user/taste-profile/"""

    def test_my_taste_profile(self, analytics_user_client, analytics_reviews):
        """Get current user's taste profile."""
        url = reverse('analytics:my-taste-profile')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'favorite_tags' in response.data
        assert 'avg_rating' in response.data
        assert 'preferred_roast' in response.data
        assert 'preferred_origin' in response.data
        assert 'review_count' in response.data

    def test_taste_profile_favorite_tags(self, analytics_user_client, analytics_reviews):
        """Verify favorite tags are returned correctly."""
        url = reverse('analytics:my-taste-profile')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should have tags from reviews
        assert len(response.data['favorite_tags']) > 0
        # Fruity should be most common (appears in 2 reviews)
        top_tag = response.data['favorite_tags'][0]
        assert 'tag' in top_tag
        assert 'count' in top_tag

    def test_taste_profile_by_user_id(
        self, analytics_user_client, analytics_user, analytics_reviews
    ):
        """Get specific user's taste profile."""
        url = reverse('analytics:user-taste-profile', args=[analytics_user.id])
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['review_count'] == 3

    def test_taste_profile_no_reviews(self, analytics_member1_client):
        """User with no reviews gets appropriate message."""
        url = reverse('analytics:my-taste-profile')
        response = analytics_member1_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['review_count'] == 0
        assert 'message' in response.data

    def test_taste_profile_preferred_roast(
        self, analytics_user_client, analytics_reviews
    ):
        """Verify preferred roast is calculated."""
        url = reverse('analytics:my-taste-profile')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Most reviews are for light roast (Ethiopia)
        assert response.data['preferred_roast'] == 'light'

    def test_taste_profile_unauthenticated(self, api_client):
        """Unauthenticated users cannot access taste profile."""
        url = reverse('analytics:my-taste-profile')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Dashboard Endpoint Tests
# =============================================================================

@pytest.mark.django_db
class TestDashboard:
    """Tests for GET /api/analytics/dashboard/"""

    def test_dashboard(self, analytics_user_client, analytics_all_data):
        """Get dashboard summary."""
        url = reverse('analytics:dashboard')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'consumption' in response.data
        assert 'taste_profile' in response.data
        assert 'top_beans' in response.data

    def test_dashboard_consumption_section(
        self, analytics_user_client, analytics_personal_purchase
    ):
        """Verify dashboard consumption section."""
        url = reverse('analytics:dashboard')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        consumption = response.data['consumption']
        assert 'total_kg' in consumption
        assert 'total_spent_czk' in consumption

    def test_dashboard_top_beans_section(
        self, analytics_user_client, analytics_bean1, analytics_bean2
    ):
        """Verify dashboard top beans section."""
        url = reverse('analytics:dashboard')
        response = analytics_user_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        top_beans = response.data['top_beans']
        assert isinstance(top_beans, list)
        if top_beans:
            bean = top_beans[0]
            # Service now returns plain dicts with 'bean_id', 'bean_name'
            assert 'bean_id' in bean
            assert 'bean_name' in bean
            assert 'roastery_name' in bean

    def test_dashboard_unauthenticated(self, api_client):
        """Unauthenticated users cannot access dashboard."""
        url = reverse('analytics:dashboard')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# AnalyticsQueries Service Tests
# =============================================================================

@pytest.mark.django_db
class TestAnalyticsQueriesUserConsumption:
    """Tests for AnalyticsQueries.user_consumption()"""

    def test_user_consumption_calculation(
        self, analytics_user, analytics_personal_purchase
    ):
        """Test basic consumption calculation."""
        result = AnalyticsQueries.user_consumption(analytics_user.id)

        assert result['total_spent_czk'] == Decimal('500.00')
        assert result['purchases_count'] >= 1
        # 500g = 0.5kg
        assert result['total_kg'] == Decimal('0.500')

    def test_user_consumption_with_multiple_purchases(
        self, analytics_user, analytics_personal_purchase, analytics_old_purchase
    ):
        """Test consumption with multiple purchases."""
        result = AnalyticsQueries.user_consumption(analytics_user.id)

        # 500 + 300 = 800 CZK
        assert result['total_spent_czk'] == Decimal('800.00')
        # 500g + 250g = 750g = 0.75kg
        assert result['total_kg'] == Decimal('0.750')

    def test_user_consumption_date_filter(
        self, analytics_user, analytics_personal_purchase, analytics_old_purchase
    ):
        """Test date filtering."""
        result = AnalyticsQueries.user_consumption(
            analytics_user.id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )

        # Only recent purchase (500 CZK)
        assert result['total_spent_czk'] == Decimal('500.00')

    def test_user_consumption_no_purchases(self, analytics_outsider):
        """Test user with no purchases."""
        result = AnalyticsQueries.user_consumption(analytics_outsider.id)

        assert result['total_spent_czk'] == Decimal('0.00')
        assert result['total_kg'] == Decimal('0.000')
        assert result['purchases_count'] == 0


@pytest.mark.django_db
class TestAnalyticsQueriesGroupConsumption:
    """Tests for AnalyticsQueries.group_consumption()"""

    def test_group_consumption_totals(
        self, analytics_group, analytics_group_purchase
    ):
        """Test group consumption totals."""
        result = AnalyticsQueries.group_consumption(analytics_group.id)

        assert result['total_spent_czk'] == Decimal('900.00')
        assert result['total_kg'] == Decimal('1.000')
        assert result['purchases_count'] == 1

    def test_group_consumption_member_breakdown(
        self, analytics_group, analytics_group_purchase
    ):
        """Test member breakdown calculation."""
        result = AnalyticsQueries.group_consumption(analytics_group.id)

        assert len(result['member_breakdown']) == 3
        # Each member should have roughly 33.33% share
        for member in result['member_breakdown']:
            assert member['share_percentage'] > 0

    def test_group_consumption_equal_shares(
        self, analytics_group, analytics_group_purchase
    ):
        """Test equal share distribution."""
        result = AnalyticsQueries.group_consumption(analytics_group.id)

        # Each member paid 300 CZK
        for member in result['member_breakdown']:
            if member['czk'] > 0:
                assert member['czk'] == Decimal('300.00')
            # Verify user is now a plain dict
            assert 'id' in member['user']
            assert 'email' in member['user']
            assert 'display_name' in member['user']


@pytest.mark.django_db
class TestAnalyticsQueriesTopBeans:
    """Tests for AnalyticsQueries.top_beans()"""

    def test_top_beans_by_rating(
        self, analytics_bean1, analytics_bean2, analytics_bean3
    ):
        """Test top beans by rating."""
        result = AnalyticsQueries.top_beans(metric='rating', limit=10)

        # Beans with min 3 reviews, sorted by avg_rating
        for item in result:
            assert item['review_count'] >= 3
            assert 'score' in item
            assert 'bean_id' in item
            assert 'bean_name' in item
            assert 'roastery_name' in item

    def test_top_beans_by_kg(self, analytics_personal_purchase, analytics_group_purchase):
        """Test top beans by kilograms."""
        result = AnalyticsQueries.top_beans(metric='kg', limit=10)

        for item in result:
            assert 'total_kg' in item
            assert item['total_kg'] >= 0

    def test_top_beans_by_money(
        self, analytics_personal_purchase, analytics_group_purchase
    ):
        """Test top beans by money spent."""
        result = AnalyticsQueries.top_beans(metric='money', limit=10)

        for item in result:
            assert 'total_spent_czk' in item

    def test_top_beans_by_reviews(
        self, analytics_bean1, analytics_bean2, analytics_bean3
    ):
        """Test top beans by review count."""
        result = AnalyticsQueries.top_beans(metric='reviews', limit=10)

        for item in result:
            assert 'review_count' in item

    def test_top_beans_limit(self, analytics_bean1, analytics_bean2, analytics_bean3):
        """Test result limit."""
        result = AnalyticsQueries.top_beans(metric='rating', limit=1)

        assert len(result) <= 1

    def test_top_beans_invalid_metric(self):
        """Test invalid metric raises domain exception."""
        with pytest.raises(InvalidMetricError):
            AnalyticsQueries.top_beans(metric='invalid')


@pytest.mark.django_db
class TestAnalyticsQueriesTimeseries:
    """Tests for AnalyticsQueries.consumption_timeseries()"""

    def test_user_timeseries(
        self, analytics_user, analytics_personal_purchase, analytics_old_purchase
    ):
        """Test user timeseries generation."""
        result = AnalyticsQueries.consumption_timeseries(user_id=analytics_user.id)

        assert len(result) >= 1
        for item in result:
            assert 'period' in item
            assert 'kg' in item
            assert 'czk' in item
            assert 'purchases_count' in item

    def test_group_timeseries(self, analytics_group, analytics_group_purchase):
        """Test group timeseries generation."""
        result = AnalyticsQueries.consumption_timeseries(group_id=analytics_group.id)

        assert len(result) >= 1
        for item in result:
            assert 'period' in item

    def test_timeseries_requires_user_or_group(self):
        """Test error when neither user nor group provided."""
        with pytest.raises(MissingParameterError):
            AnalyticsQueries.consumption_timeseries()


@pytest.mark.django_db
class TestAnalyticsQueriesTasteProfile:
    """Tests for AnalyticsQueries.user_taste_profile()"""

    def test_taste_profile_generation(self, analytics_user, analytics_reviews):
        """Test taste profile generation."""
        result = AnalyticsQueries.user_taste_profile(analytics_user.id)

        assert result is not None
        assert 'favorite_tags' in result
        assert 'avg_rating' in result
        assert 'preferred_roast' in result
        assert 'preferred_origin' in result
        assert 'review_count' in result

    def test_taste_profile_tag_ranking(self, analytics_user, analytics_reviews):
        """Test tag ranking is correct."""
        result = AnalyticsQueries.user_taste_profile(analytics_user.id)

        # Fruity appears in 2 reviews, should be first
        assert result['favorite_tags'][0]['tag'] == 'fruity'
        assert result['favorite_tags'][0]['count'] == 2

    def test_taste_profile_avg_rating(self, analytics_user, analytics_reviews):
        """Test average rating calculation."""
        result = AnalyticsQueries.user_taste_profile(analytics_user.id)

        # Ratings: 5, 4, 4 = avg 4.33
        assert result['avg_rating'] == 4.33

    def test_taste_profile_no_reviews(self, analytics_outsider):
        """Test user with no reviews returns None."""
        result = AnalyticsQueries.user_taste_profile(analytics_outsider.id)

        assert result is None

    def test_taste_profile_preferred_origin(self, analytics_user, analytics_reviews):
        """Test preferred origin calculation."""
        result = AnalyticsQueries.user_taste_profile(analytics_user.id)

        # 2 Ethiopia reviews, 1 Colombia
        assert result['preferred_origin'] == 'Ethiopia'
