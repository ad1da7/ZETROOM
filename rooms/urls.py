from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # главная страница
    path('rooms/', views.all_rooms, name='all_rooms'),  # список всех активных комнат
    path('create/', views.create_room, name='create_room'),  # создание комнаты
    path('join/', views.join_room, name='join_room'),  # поиск и вход в комнату
    path('room/<uuid:room_uuid>/', views.room_detail, name='room_detail'),  # сама комната
]
