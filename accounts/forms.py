from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class CustomUserChangeForm(UserChangeForm):
    new_password = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Оставьте пустым, если не хотите менять пароль."
    )
    new_password_confirm = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
        required=False,
        help_text="Введите пароль еще раз для подтверждения."
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super(CustomUserChangeForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-deep-green focus:ring-deep-green dark:bg-input-bg dark:border-input-border'
        # Удаляем ненужные поля
        self.fields.pop('is_active', None)
        self.fields.pop('is_staff', None)
        self.fields.pop('is_superuser', None)
        self.fields.pop('last_login', None)
        self.fields.pop('date_joined', None)
        self.fields.pop('groups', None)
        self.fields.pop('user_permissions', None)
        self.fields.pop('password', None)  # Удаляем поле password модели

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        if new_password and new_password != new_password_confirm:
            self.add_error('new_password_confirm', "Пароли не совпадают.")
        if new_password_confirm and not new_password:
            self.add_error('new_password', "Введите новый пароль.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        # Обновляем пароль только если он был введен
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user