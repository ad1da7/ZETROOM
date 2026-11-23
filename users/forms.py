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
    class Meta:
        model = Profile
        fields = ['avatar', 'background_image', 'tag', 'age', 'bio']
        widgets = {
            'tag': forms.TextInput(attrs={'placeholder': '@vash_tag'}),
            'age': forms.NumberInput(attrs={'min': 1, 'max': 120, 'placeholder': 'Ваш возраст'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Расскажите о себе...'}),
        }

    def clean_tag(self):
        tag = self.cleaned_data.get('tag')
        if tag and not tag.startswith('@'):
            tag = f"@{tag}"
        return tag