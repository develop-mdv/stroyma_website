from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from accounts.models import get_or_create_profile

class OrderForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Имя")
    last_name = forms.CharField(max_length=100, label="Фамилия")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(
        max_length=32,
        label="Телефон"
    )
    address = forms.CharField(max_length=255, label="Адрес доставки")
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Комментарий к заказу",
        max_length=1000,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            profile = get_or_create_profile(user)
            self.fields['phone'].initial = profile.phone
            self.fields['address'].initial = profile.delivery_address

    def clean_phone(self):
        value = (self.cleaned_data.get('phone') or '').strip()
        digits = ''.join(ch for ch in value if ch.isdigit())
        if not digits:
            raise ValidationError("Введите номер телефона.")

        # Нормализация РФ: 8XXXXXXXXXX или 7XXXXXXXXXX или 10 цифр без кода.
        if len(digits) == 10:
            digits = '7' + digits
        elif len(digits) == 11 and digits[0] == '8':
            digits = '7' + digits[1:]

        if len(digits) != 11 or digits[0] != '7':
            raise ValidationError("Введите номер в формате +7XXXXXXXXXX.")

        return '+' + digits

class SearchForm(forms.Form):
    query = forms.CharField(label='Поиск', max_length=100, required=False)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Имя")
    email = forms.EmailField(label="Email")
    message = forms.CharField(
        widget=forms.Textarea,
        label="Сообщение",
        max_length=1000,
    )