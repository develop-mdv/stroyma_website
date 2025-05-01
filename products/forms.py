from django import forms
from django.contrib.auth.models import User

class OrderForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Имя")
    last_name = forms.CharField(max_length=100, label="Фамилия")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=20, label="Телефон")
    address = forms.CharField(max_length=255, label="Адрес доставки")

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            # Поле phone и address не заполняем, так как они не хранятся в модели User
            # Можно добавить кастомные поля в модель User, если нужно

class SearchForm(forms.Form):
    query = forms.CharField(label='Поиск', max_length=100, required=False)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Имя")
    email = forms.EmailField(label="Email")
    message = forms.CharField(widget=forms.Textarea, label="Сообщение")