from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import CoffeeBean, CoffeeBeanVariant
from .serializers import (
    CoffeeBeanSerializer,
    CoffeeBeanCreateSerializer,
    CoffeeBeanListSerializer,
    CoffeeBeanVariantSerializer,
)
from .services import (
    create_bean,
    soft_delete_bean,
    search_beans,
    get_all_roasteries,
    get_all_origins,
    create_variant,
    soft_delete_variant,
    DuplicateBeanError,
    BeanNotFoundError,
    DuplicateVariantError,
    VariantNotFoundError,
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
        return search_beans(
            search=self.request.query_params.get('search'),
            roastery=self.request.query_params.get('roastery'),
            origin=self.request.query_params.get('origin'),
            roast_profile=self.request.query_params.get('roast_profile'),
            processing=self.request.query_params.get('processing'),
            min_rating=self.request.query_params.get('min_rating'),
        )
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return CoffeeBeanListSerializer
        elif self.action == 'create':
            return CoffeeBeanCreateSerializer
        return CoffeeBeanSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new coffee bean."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            bean = create_bean(
                created_by=request.user,
                **serializer.validated_data
            )
        except DuplicateBeanError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = CoffeeBeanSerializer(bean)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a bean."""
        bean_id = kwargs.get('pk')

        try:
            soft_delete_bean(bean_id=bean_id)
        except BeanNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def roasteries(self, request):
        """Get list of all roasteries."""
        roasteries = get_all_roasteries()
        return Response(roasteries)

    @action(detail=False, methods=['get'])
    def origins(self, request):
        """Get list of all origin countries."""
        origins = get_all_origins()
        return Response(origins)


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
    
    def create(self, request, *args, **kwargs):
        """Create a new variant."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            variant = create_variant(**serializer.validated_data)
        except (BeanNotFoundError, DuplicateVariantError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = CoffeeBeanVariantSerializer(variant)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete a variant."""
        variant_id = kwargs.get('pk')

        try:
            soft_delete_variant(variant_id=variant_id)
        except VariantNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(status=status.HTTP_204_NO_CONTENT)