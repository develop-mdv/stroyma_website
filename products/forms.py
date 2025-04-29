from django import forms

class OrderForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Имя")
    last_name = forms.CharField(max_length=100, label="Фамилия")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=20, label="Телефон")
    address = forms.CharField(max_length=255, label="Адрес доставки")

class SearchForm(forms.Form):
    query = forms.CharField(label='Поиск', max_length=100, required=False)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Имя")
    email = forms.EmailField(label="Email")
    message = forms.CharField(widget=forms.Textarea, label="Сообщение")