"""Versioned public legal documents and minimal evidence of acceptance."""

from django import forms
from django.template.loader import render_to_string

DOCUMENT_VERSION = '2026-09-30'
COMPANY = {
    'name': 'ООО «СТРОЙМА»',
    'full_name': 'Общество с ограниченной ответственностью «СТРОЙМА»',
    'inn': '4632128411',
    'kpp': '463201001',
    'ogrn': '1114632000339',
    'address': '305004, Курская область, г. Курск, ул. Ленина, д. 90/2, офис 215В',
    'email': 'mvv@stroyma.ru',
    'phone': '+7 (910) 211-40-41',
    'phone_link': '+79102114041',
    'warehouse': 'г. Курск, проспект Кулакова, 109В',
    'office_hours': 'Пн–Пт: 09:00–18:00 (московское время)',
}
CONSENTS = {
    'registration': {
        'title': 'Регистрация и личный кабинет',
        'purpose': 'создание и обслуживание личного кабинета, подтверждение электронной почты и восстановление доступа',
        'data': 'имя пользователя, электронная почта, хеш пароля, дата регистрации и сведения о подтверждении почты; при заполнении профиля — имя, фамилия, телефон и адрес доставки',
        'term': 'до удаления личного кабинета, прекращения его обслуживания или отзыва согласия — в зависимости от того, что наступит раньше',
    },
    'contact': {
        'title': 'Обратная связь',
        'purpose': 'рассмотрение обращения и направление ответа',
        'data': 'имя, электронная почта и сведения, которые я самостоятельно указал(а) в сообщении',
        'term': 'до завершения рассмотрения обращения, но не более 90 дней со дня его отправки, либо до отзыва согласия, если он поступит раньше',
    },
    'color_selection': {
        'title': 'Подбор цвета фасада',
        'purpose': 'подготовка консультации по выбранным материалам и цветам фасада и связь по моей заявке',
        'data': 'имя, телефон, электронная почта (если указана), выбранные цвета и материалы фасада и цоколя, сведения из комментария',
        'term': 'до завершения консультации, но не более 90 дней со дня отправки заявки, либо до отзыва согласия, если он поступит раньше',
    },
}


def document_version_field():
    return forms.ChoiceField(
        choices=[(DOCUMENT_VERSION, DOCUMENT_VERSION)], initial=DOCUMENT_VERSION,
        widget=forms.HiddenInput,
        error_messages={
            'required': 'Обновите страницу и ознакомьтесь с действующей редакцией документа.',
            'invalid_choice': 'Документ обновлён. Обновите страницу и подтвердите действующую редакцию.',
        },
    )


def legal_context(request=None):
    from django.conf import settings
    return {'company': COMPANY, 'legal_version': DOCUMENT_VERSION,
            'site_public_url': settings.SITE_URL}


def document_snapshot(kind):
    context = legal_context()
    if kind == 'sale':
        templates = ('products/legal/offer_document.html',
                     'products/legal/delivery_document.html',
                     'products/legal/returns_document.html')
        return '\n'.join(render_to_string(template, context) for template in templates)
    context['consent'] = CONSENTS[kind]
    return render_to_string('products/legal/consent_document.html', context)


def record_acceptance(request, kind, *, user=None, order=None, subject=''):
    from accounts.models import LegalAcceptance
    return LegalAcceptance.objects.create(
        kind=kind, version=DOCUMENT_VERSION, document_snapshot=document_snapshot(kind),
        source_path=request.path, subject=subject, user=user, order=order,
    )
