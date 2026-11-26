from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.public_profile_view, name='public_profile'),
    path('friend/toggle/<str:username>/', views.toggle_friend_view, name='toggle_friend'),
    path('friends/api/', views.friends_api_view, name='friends_api'),
    path('friends/request/', views.friend_request_by_tag_view, name='friend_request_by_tag'),
    path('friends/requests/api/', views.friend_requests_api_view, name='friend_requests_api'),
    path('friends/requests/<int:request_id>/respond/', views.friend_request_response_view, name='friend_request_response'),
]