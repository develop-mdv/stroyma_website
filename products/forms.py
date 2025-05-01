from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            if hasattr(user, 'profile'):
                self.fields['phone'].initial = user.profile.phone
                self.fields['address'].initial = user.profile.delivery_address

class SearchForm(forms.Form):
    query = forms.CharField(label='Поиск', max_length=100, required=False)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Имя")
    email = forms.EmailField(label="Email")
    message = forms.CharField(
        widget=forms.Textarea,
        label="Сообщение",
        max_length=1000,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s.,!?]*$',
                message="Сообщение может содержать только буквы, цифры, пробелы и знаки препинания."
            )
        ]
    )