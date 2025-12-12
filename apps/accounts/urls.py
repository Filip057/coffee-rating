from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    
    # User profile
    path('user/', views.get_current_user, name='current-user'),
    path('user/update/', views.update_profile, name='update-profile'),
    path('user/delete/', views.delete_account, name='delete-account'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # Email verification
    path('verify-email/', views.verify_email, name='verify-email'),
    
    # Password reset
    path('password-reset/', views.request_password_reset, name='password-reset'),
    path('password-reset/confirm/', views.confirm_password_reset, name='password-reset-confirm'),
]