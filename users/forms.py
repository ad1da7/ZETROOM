from django import forms
from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'tag', 'age', 'bio']
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
