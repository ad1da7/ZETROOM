from django.db import models
from django.utils import timezone
from datetime import timedelta
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
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')

    is_private = models.BooleanField(default=False)
    access_code = models.CharField(max_length=10, blank=True, default='')
    max_participants = models.PositiveIntegerField(default=10)
    is_18_plus = models.BooleanField(default=False)

    CONTENT_CHOICES = [
        ('movie', 'Фильм'),
        ('series', 'Сериал'),
        ('cartoon', 'Мультик'),
        ('cartoon_series', 'Мультсериал'),
        ('video', 'Видео'),
        ('stream', 'Стрим'),
    ]
    content_type = models.CharField(max_length=20, choices=CONTENT_CHOICES, default='movie')

    banned_users = models.ManyToManyField(User, related_name='banned_rooms', blank=True)

    # Состояние общего плеера и голосовой комнаты.
    is_playing = models.BooleanField(default=False)
    current_time = models.FloatField(default=0)
    voice_state = models.JSONField(default=dict, blank=True)
    webrtc_signals = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        if self.is_private and not self.access_code:
            self.access_code = generate_room_code()
        elif not self.is_private:
            self.access_code = ''
        super().save(*args, **kwargs)

    def cleanup_stale_participants(self, timeout_seconds=45):
        threshold = timezone.now() - timedelta(seconds=timeout_seconds)
        self.participants.filter(last_seen__lt=threshold).delete()

        # Удаляем устаревшие записи голосового состояния.
        now_ts = timezone.now().timestamp()
        self.voice_state = {
            key: value for key, value in (self.voice_state or {}).items()
            if now_ts - float(value.get('updated_at', 0)) < 12
        }
        self.webrtc_signals = [
            signal for signal in (self.webrtc_signals or [])
            if now_ts - float(signal.get('ts', 0)) < 15
        ]

    def __str__(self):
        return self.name


class Participant(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['room', 'user'], name='unique_room_participant')
        ]

    def __str__(self):
        return f"{self.user} в {self.room.name}"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    user = models.CharField(max_length=100, default='Гость')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Сообщение от {self.user}"


class MovieReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_reviews')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    video_url = models.URLField(max_length=500, blank=True, default='', db_index=True)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(max_length=1500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв {self.user.username} ({self.rating}/5)"