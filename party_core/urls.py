from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('rooms.urls')),          # Подключаем маршруты из приложения rooms
    path('account/', include('users.urls')),  # Подключаем личный кабинет, вход и регистрацию
]

# Разрешаем отдавать загруженные аватарки в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)