from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from accounts.models import UserProfile

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
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        required=False,
        widget=forms.TextInput,
        help_text="Введите ваш номер телефона."
    )
    delivery_address = forms.CharField(
        label="Адрес доставки",
        required=False,
        widget=forms.Textarea,
        help_text="Введите ваш адрес доставки."
    )
    current_password = forms.CharField(
        label="Текущий пароль",
        widget=forms.PasswordInput,
        required=False,
        help_text="Введите текущий пароль, если хотите изменить пароль."
    )
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
        help_text="Введите новый пароль еще раз для подтверждения."
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'delivery_address')

    def __init__(self, *args, **kwargs):
        super(CustomUserChangeForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-deep-green focus:ring-deep-green  '
        # Заполняем начальные значения для полей phone и delivery_address
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['delivery_address'].initial = self.instance.profile.delivery_address
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
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')

        # Проверка текущего пароля только если меняется пароль
        if new_password:
            if not current_password or not self.instance.check_password(current_password):
                self.add_error('current_password', "Неверный текущий пароль.")
            if new_password != new_password_confirm:
                self.add_error('new_password_confirm', "Пароли не совпадают.")
        if new_password_confirm and not new_password:
            self.add_error('new_password', "Введите новый пароль.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        phone = self.cleaned_data.get('phone')
        delivery_address = self.cleaned_data.get('delivery_address')

        # Обновляем пароль только если он был введен
        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()
            # Сохраняем или обновляем профиль
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.delivery_address = delivery_address
            profile.save()

        return user

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-deep-green focus:ring-deep-green'})
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-deep-green focus:ring-deep-green'}),
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-deep-green focus:ring-deep-green'}),
    )