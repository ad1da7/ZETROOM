from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('rooms/', views.all_rooms, name='all_rooms'),
    path('rooms/counts/', views.rooms_counts_api, name='rooms_counts_api'),
    path('create/', views.create_room, name='create_room'),
    path('join/', views.join_room, name='join_room'),
    path('room/<uuid:room_uuid>/', views.room_detail, name='room_detail'),
    path('room/<uuid:room_uuid>/leave/', views.leave_room, name='leave_room'),
    path('room/<uuid:room_uuid>/delete/', views.delete_room, name='delete_room'),
    path('room/<uuid:room_uuid>/kick/<int:user_id>/', views.kick_user, name='kick_user'),
    path('room/<uuid:room_uuid>/sync/', views.room_sync_api, name='room_sync_api'),
    path('room/<uuid:room_uuid>/reviews/', views.room_reviews_api, name='room_reviews_api'),
]