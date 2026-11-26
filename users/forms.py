from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Электронная почта")
    age = forms.IntegerField(required=True, min_value=1, max_value=120, label="Ваш возраст")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "age")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email


class ProfileUpdateForm(forms.ModelForm):
    # Добавляем поле username из модели User
    username = forms.CharField(max_length=150, required=True, label="Никнейм")

    class Meta:
        model = Profile
        fields = ['avatar', 'background_image', 'tag', 'age', 'bio']
        widgets = {
            'tag': forms.TextInput(attrs={'placeholder': '@vash_tag'}),
            'age': forms.NumberInput(attrs={'min': 1, 'max': 120, 'placeholder': 'Ваш возраст'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Расскажите о себе...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Заполняем поле username текущим ником пользователя
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Проверяем, не занят ли ник кем-то другим (исключая текущего пользователя)
        if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
            raise forms.ValidationError("Этот никнейм уже занят. Выберите другой.")
        return username

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag and not tag.startswith('@'):
            tag = f"@{tag}"
        return tag