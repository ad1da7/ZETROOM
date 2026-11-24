from django.db import models
import uuid
import random
import string
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Room(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    host = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    description = models.TextField(blank=True, default='')
    video_url = models.URLField(max_length=500, blank=True, default='')
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')

    is_private = models.BooleanField(default=False)
    access_code = models.CharField(max_length=10, blank=True, default='')
    max_participants = models.PositiveIntegerField(default=10)
    is_18_plus = models.BooleanField(default=False)
    banned_users = models.ManyToManyField(User, related_name='banned_rooms', blank=True)

    # Тип контента (Фильм, Сериал и т.д.)
    CONTENT_CHOICES = [
        ('movie', 'Фильм'),
        ('series', 'Сериал'),
        ('cartoon', 'Мультик'),
        ('cartoon_series', 'Мультсериал'),
    ]
    content_type = models.CharField(max_length=20, choices=CONTENT_CHOICES, default='movie')

    # Синхронизация
    is_playing = models.BooleanField(default=False)
    current_time = models.FloatField(default=0.0)
    voice_state = models.JSONField(default=dict, blank=True)
    webrtc_signals = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        if self.is_private and not self.access_code:
            self.access_code = generate_room_code()
        super().save(*args, **kwargs)

    def cleanup_stale_participants(self, timeout_seconds=12):
        cutoff = timezone.now() - timedelta(seconds=timeout_seconds)
        self.participants.filter(last_seen__lt=cutoff).exclude(user=self.host).delete()

    def __str__(self):
        return self.name


class Participant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} в {self.room.name}"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    user = models.CharField(max_length=100, default='Гость')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сообщение от {self.user}"