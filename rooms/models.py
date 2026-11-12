from django.db import models
import uuid  #это специальная библиотека для генерации айдишников
from django.contrib.auth.models import User  #это встроенная модель самого пользователя

class Room(models.Model):# это модель для самой  кинокомнаты
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)# Это уникальный хеш для ссылки (типа 550e8400-e29b...), чтобы ссылки были секретными
    name = models.CharField(max_length=100) #это для название самой комнаты
    host = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)# Хозяин комнаты (тот, кто её создал). Пока она пустая я потом туда запилю все
    created_at = models.DateTimeField(auto_now_add=True)# Дата и время создания, и она заполняется автоматом

    # Эта функция нужна, чтобы в админке мы видели название комнаты, а не "Room object (1)"
    def __str__(self):
        return self.name

class Message(models.Model):# Модель для сообщений в чате
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')  # Привязываем сообщение к конкретной комнате
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)    # Кто отправил сообщение
    text = models.TextField()# Сам текст сообщения
    created_at = models.DateTimeField(auto_now_add=True)# Когда отправлено

    def __str__(self):
        return f"Сообщение от {self.user}"

class Participant(models.Model):
    # Модель участника комнаты

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')  # Комната участника, каскадное удаление, доступ через room.participants
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Пользователь (может быть пустым)
    joined_at = models.DateTimeField(auto_now_add=True)  # Время присоединения (автозаполнение)

    def __str__(self):
        return f"{self.user} в {self.room.name}"  # Строковое представление: «пользователь в комнате»
