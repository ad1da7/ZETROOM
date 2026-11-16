from django.db import models
import uuid  #библиотека чтобы  делать случайные айди
from django.contrib.auth.models import User  #встроенная модель пользователя

class Room(models.Model):#модель самой кинокомнаты
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)#уникальный код для ссылки на комнату
    name = models.CharField(max_length=100) #название комнаты
    host = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)#хозяин комнаты
    created_at = models.DateTimeField(auto_now_add=True)#дата создания комнаты

    def __str__(self):
        return self.name #чтобы в админке было название а не объект 1

class Participant(models.Model):#модель участника (кто зашел в комнату)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')  #в какую комнату зашел
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  #какой пользователь
    joined_at = models.DateTimeField(auto_now_add=True)  #время когда зашел

    def __str__(self):
        return f"{self.user} в {self.room.name}"  #показывает кто в какой комнате

class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    user = models.CharField(max_length=100, default='Гость')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)