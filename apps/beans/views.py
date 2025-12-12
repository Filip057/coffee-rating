from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from .models import CoffeeBean, CoffeeBeanVariant
from .serializers import (
    CoffeeBeanSerializer,
    CoffeeBeanCreateSerializer,
    CoffeeBeanListSerializer,
    CoffeeBeanVariantSerializer,
)


class BeanPagination(PageNumberPagination):
    """Custom pagination for beans."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CoffeeBeanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CoffeeBean CRUD operations.
    
    list: Get all coffee beans (with filters)
    create: Create a new coffee bean
    retrieve: Get a specific coffee bean
    update: Update a coffee bean
    partial_update: Partially update a coffee bean
    destroy: Delete/deactivate a coffee bean
    """
    
    queryset = CoffeeBean.objects.filter(is_active=True).select_related('created_by').prefetch_related('variants')
    serializer_class = CoffeeBeanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = BeanPagination
    
    def get_queryset(self):
        """
        Filter beans based on query parameters.
        
        Filters:
        - search: Search in name, roastery, origin, description
        - roastery: Filter by roastery name
        - origin: Filter by origin country
        - roast_profile: Filter by roast profile
        - processing: Filter by processing method
        - min_rating: Minimum average rating
        """
        queryset = super().get_queryset()
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(roastery_name__icontains=search) |
                Q(origin_country__icontains=search) |
                Q(description__icontains=search) |
                Q(tasting_notes__icontains=search)
            )
        
        # Filter by roastery
        roastery = self.request.query_params.get('roastery')
        if roastery:
            queryset = queryset.filter(roastery_name__icontains=roastery)
        
        # Filter by origin
        origin = self.request.query_params.get('origin')
        if origin:
            queryset = queryset.filter(origin_country__icontains=origin)
        
        # Filter by roast profile
        roast_profile = self.request.query_params.get('roast_profile')
        if roast_profile:
            queryset = queryset.filter(roast_profile=roast_profile)
        
        # Filter by processing
        processing = self.request.query_params.get('processing')
        if processing:
            queryset = queryset.filter(processing=processing)
        
        # Filter by minimum rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(avg_rating__gte=min_rating)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return CoffeeBeanListSerializer
        elif self.action == 'create':
            return CoffeeBeanCreateSerializer
        return CoffeeBeanSerializer
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete - set is_active to False instead of deleting."""
        instance.is_active = False
        instance.save(update_fields=['is_active'])
    
    @action(detail=False, methods=['get'])
    def roasteries(self, request):
        """Get list of all roasteries."""
        roasteries = CoffeeBean.objects.filter(
            is_active=True
        ).values_list('roastery_name', flat=True).distinct().order_by('roastery_name')
        
        return Response(list(roasteries))
    
    @action(detail=False, methods=['get'])
    def origins(self, request):
        """Get list of all origin countries."""
        origins = CoffeeBean.objects.filter(
            is_active=True,
            origin_country__isnull=False
        ).exclude(
            origin_country=''
        ).values_list('origin_country', flat=True).distinct().order_by('origin_country')
        
        return Response(list(origins))


class CoffeeBeanVariantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CoffeeBeanVariant CRUD operations.
    
    Manage package sizes and pricing for coffee beans.
    """
    
    queryset = CoffeeBeanVariant.objects.filter(is_active=True).select_related('coffeebean')
    serializer_class = CoffeeBeanVariantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter variants by coffee bean if specified."""
        queryset = super().get_queryset()
        
        coffeebean_id = self.request.query_params.get('coffeebean')
        if coffeebean_id:
            queryset = queryset.filter(coffeebean_id=coffeebean_id)
        
        return queryset
    
    def perform_destroy(self, instance):
        """Soft delete - set is_active to False."""
        instance.is_active = False
        instance.save(update_fields=['is_active'])