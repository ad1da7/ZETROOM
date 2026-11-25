from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tag = models.CharField("Уникальный тег", max_length=30, unique=True, blank=True, null=True)
    avatar = models.ImageField("Аватарка", upload_to='avatars/', blank=True, null=True)
    background_image = models.ImageField("Фон профиля", upload_to='backgrounds/', blank=True, null=True)
    age = models.PositiveIntegerField("Возраст", blank=True, null=True)
    bio = models.TextField("О себе", max_length=500, blank=True)
    is_email_verified = models.BooleanField("Почта подтверждена", default=False)

    def __str__(self):
        return f"Профиль {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        base_tag = f"@{instance.username}"[:30]
        tag = base_tag
        counter = 1
        while Profile.objects.filter(tag=tag).exists():
            suffix = str(counter)
            tag = f"{base_tag[:30 - len(suffix)]}{suffix}"
            counter += 1
        Profile.objects.create(user=instance, tag=tag)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(pre_social_login)
def auto_verify_social_email(sender, request, sociallogin, **kwargs):
    if sociallogin.user and sociallogin.user.pk:
        profile, _ = Profile.objects.get_or_create(user=sociallogin.user)
        if not profile.is_email_verified:
            profile.is_email_verified = True
            profile.save()
