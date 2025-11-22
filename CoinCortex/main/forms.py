from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class CustomUserCreationForm(UserCreationForm):
    """Расширенная форма регистрации"""
    first_name = forms.CharField(max_length=100, required=False, label='Имя')
    last_name = forms.CharField(max_length=100, required=False, label='Фамилия')
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        max_length=500,
        required=False,
        label='Описание профиля'
    )
    birth_date = forms.DateField(
        required=False,
        label='Дата рождения',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'first_name', 'last_name', 'bio', 'birth_date')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Обновляем профиль
            profile = user.profile
            profile.first_name = self.cleaned_data.get('first_name', '')
            profile.last_name = self.cleaned_data.get('last_name', '')
            profile.bio = self.cleaned_data.get('bio', '')
            birth_date = self.cleaned_data.get('birth_date')
            if birth_date:
                profile.birth_date = birth_date
            profile.save()
        return user

