from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from accounts.models import get_or_create_profile

class OrderForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Имя")
    last_name = forms.CharField(max_length=100, label="Фамилия")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(
        max_length=20,
        label="Телефон",
        validators=[
            RegexValidator(
                regex=r'^\+?7[\d]{10}$',
                message="Введите номер в формате +7XXXXXXXXXX"
            )
        ]
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