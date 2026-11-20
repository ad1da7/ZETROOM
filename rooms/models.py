from django.db import models
import uuid
import random
import string
from django.contrib.auth.models import User


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Room(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    host = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True, default='')
    video_url = models.URLField(max_length=500, blank=True, default='')

    is_private = models.BooleanField(default=False)
    access_code = models.CharField(max_length=10, blank=True, default='')
    max_participants = models.PositiveIntegerField(default=10)
    is_18_plus = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_private and not self.access_code:
            self.access_code = generate_room_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Participant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} в {self.room.name}"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    user = models.CharField(max_length=100, default='Гость')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сообщение от {self.user}"