from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from .models import Profile


class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Электронная почта")

    # ДАТА РОЖДЕНИЯ С ОГРАНИЧЕНИЯМИ
    birth_date = forms.DateField(
        required=True,
        label="Дата рождения",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'min': '1900-01-01',  # Самая ранняя возможная дата
            'max': '2010-12-31',  # Ограничение: не младше 14-16 лет (настрой под себя)
        }),
        error_messages={
            'required': 'Обязательно укажите вашу дату рождения.',
            'invalid': 'Введите корректную дату.',
        }
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "birth_date")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = timezone.now().date()
            if birth_date > today:
                raise forms.ValidationError("Дата рождения не может быть в будущем.")
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 6:
                raise forms.ValidationError("Ваш возраст не может быть меньше 6 лет.")
            if age > 100:
                raise forms.ValidationError("Укажите корректный год рождения (до 100 лет).")
        return birth_date


class ProfileUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Никнейм")

    class Meta:
        model = Profile
        fields = ['avatar', 'background_image', 'tag', 'bio', 'birth_date']
        widgets = {
            'tag': forms.TextInput(attrs={'placeholder': '@vash_tag'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Расскажите о себе...'}),
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'min': '1900-01-01',
                'max': '2010-12-31',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
            raise forms.ValidationError("Этот никнейм уже занят. Выберите другой.")
        return username

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag and not tag.startswith('@'):
            tag = f"@{tag}"
        return tag

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = timezone.now().date()
            if birth_date > today:
                raise forms.ValidationError("Дата рождения не может быть в будущем.")
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 6:
                raise forms.ValidationError("Ваш возраст не может быть меньше 6 лет.")
            if age > 100:
                raise forms.ValidationError("Укажите корректный год рождения (до 100 лет).")
        return birth_date