from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # User analytics
    path('user/<uuid:user_id>/consumption/', views.user_consumption, name='user-consumption'),
    path('user/consumption/', views.user_consumption, name='my-consumption'),  # Current user
    path('user/<uuid:user_id>/taste-profile/', views.taste_profile, name='user-taste-profile'),
    path('user/taste-profile/', views.taste_profile, name='my-taste-profile'),  # Current user
    
    # Group analytics
    path('group/<uuid:group_id>/consumption/', views.group_consumption, name='group-consumption'),
    
    # Bean analytics
    path('beans/top/', views.top_beans, name='top-beans'),
    
    # Timeseries data
    path('timeseries/', views.consumption_timeseries, name='consumption-timeseries'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
]