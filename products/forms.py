from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from accounts.models import get_or_create_profile
from stroyma.legal import document_version_field

class OrderForm(forms.Form):
    sales_terms = forms.BooleanField(label='Условия продажи',
                                     error_messages={'required': 'Ознакомьтесь с условиями продажи и подтвердите их принятие.'})
    document_version = document_version_field()
    name = forms.CharField(max_length=255, label="Имя или название организации")
    email = forms.EmailField(label="Электронная почта")
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
            self.fields['name'].initial = ' '.join(
                part for part in (user.first_name, user.last_name) if part
            )
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
            raise ValidationError("Введите российский номер: 10 цифр без кода страны либо номер с 8 или +7.")

        return '+' + digits

class SearchForm(forms.Form):
    query = forms.CharField(label='Поиск', max_length=100, required=False)

class ContactForm(forms.Form):
    consent = forms.BooleanField(label='Согласие на обработку персональных данных',
                                 error_messages={'required': 'Подтвердите согласие на обработку данных для ответа на обращение.'})
    document_version = document_version_field()
    name = forms.CharField(max_length=100, label="Имя")
    email = forms.EmailField(label="Электронная почта")
    message = forms.CharField(
        widget=forms.Textarea,
        label="Сообщение",
        max_length=1000,
    )


class ColorSelectionRequestForm(forms.Form):
    document_version = document_version_field()
    name = forms.CharField(max_length=100, label='Имя')
    phone = forms.CharField(max_length=32, label='Телефон')
    email = forms.EmailField(required=False, label='Электронная почта')
    message = forms.CharField(required=False, max_length=1000, label='Комментарий')
    facade = forms.CharField(required=False, max_length=160)
    plinth = forms.CharField(required=False, max_length=160)
    config_state = forms.CharField(required=False, max_length=500)
    consent = forms.BooleanField(label='Согласие на обработку персональных данных')

    def clean_phone(self):
        value = (self.cleaned_data.get('phone') or '').strip()
        digits = ''.join(char for char in value if char.isdigit())
        if len(digits) == 10:
            digits = '7' + digits
        elif len(digits) == 11 and digits[0] == '8':
            digits = '7' + digits[1:]
        if len(digits) != 11 or digits[0] != '7':
            raise ValidationError('Введите российский номер: 10 цифр без кода страны либо номер с 8 или +7.')
        return '+' + digits
