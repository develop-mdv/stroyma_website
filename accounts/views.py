import logging
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from products.models import Cart, CartItem, Order
from products.views import merge_session_cart_to_user_cart

from .decorators import custom_login_required
from .forms import CustomPasswordResetForm, CustomSetPasswordForm, CustomUserChangeForm, LoginForm, RegisterForm
from .models import UserProfile, get_or_create_profile

logger = logging.getLogger(__name__)


def _send_confirmation_email(user, profile, request):
    """Рендерит и отправляет письмо с подтверждением email. Возвращает True/False."""
    current_site = get_current_site(request)
    mail_subject = 'Подтверждение регистрации на сайте Stroyma'
    message = render_to_string('accounts/email/email_confirmation.html', {
        'user': user,
        'domain': current_site.domain,
        'protocol': 'https' if request.is_secure() else 'http',
        'token': profile.confirmation_token,
    })
    try:
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error('Ошибка отправки письма подтверждения email для %s: %s', user.email, exc)
        return False

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = UserProfile.objects.create(user=user)

            email_sent = _send_confirmation_email(user, profile, request)

            login(request, user)
            merge_session_cart_to_user_cart(request)
            if email_sent:
                messages.success(
                    request,
                    "Регистрация прошла успешно! Пожалуйста, проверьте вашу почту и подтвердите email-адрес."
                )
            else:
                messages.warning(
                    request,
                    "Регистрация прошла успешно, но письмо подтверждения не удалось отправить. "
                    "Попробуйте отправить его повторно из личного кабинета."
                )
            return JsonResponse({'success': True})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'success': False, 'message': errors}, status=400)
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@ratelimit(key='ip', rate='60/h', block=True)
def confirm_email_view(request, token):
    success = False
    try:
        token_uuid = UUID(token)
    except (ValueError, TypeError):
        token_uuid = None

    profile = None
    if token_uuid is not None:
        profile = UserProfile.objects.filter(confirmation_token=token_uuid).first()

    if profile is None:
        messages.error(request, "Ссылка для подтверждения email недействительна.")
    elif profile.email_confirmed:
        success = True
        messages.info(request, "Ваш email уже был подтверждён ранее.")
    elif not profile.token_is_valid():
        messages.error(
            request,
            "Ссылка для подтверждения устарела. Запросите новое письмо в личном кабинете."
        )
    else:
        profile.email_confirmed = True
        profile.save(update_fields=['email_confirmed'])
        profile.rotate_confirmation_token()
        if not request.user.is_authenticated:
            login(request, profile.user)
            merge_session_cart_to_user_cart(request)
        success = True
        messages.success(request, "Ваш email успешно подтверждён!")

    return render(request, 'accounts/email_confirmation.html', {'success': success})

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, "Вы уже авторизованы.")
        return redirect('profile')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                merge_session_cart_to_user_cart(request)
                messages.info(request, f"Вы вошли как {user.get_username()}.")
                return redirect("product_list")
            messages.error(request, "Неверный логин или пароль.")
        else:
            messages.error(request, "Неверные данные формы.")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

@custom_login_required
def logout_view(request):
    merge_session_cart_to_user_cart(request)
    logout(request)
    messages.info(request, "Вы вышли из аккаунта.")
    return redirect("product_list")

@custom_login_required
def profile_view(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related('items__product')
        .annotate(
            items_count=Count('items'),
            total_sum=Sum(F('items__quantity') * F('items__product__price')),
        )
        .order_by('-created_at')
    )
    profile = get_or_create_profile(request.user)
    email_warning = not profile.email_confirmed
    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'email_warning': email_warning,
    })

@custom_login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
        'items': order.items.all(),
        'status_history': order.status_history.all(),
        'total_items': order.total_items_count,
    }
    return render(request, 'accounts/order_detail.html', context)

@custom_login_required
def edit_profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные профиля успешно обновлены!')
            return redirect('profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})

@custom_login_required
@ratelimit(key='ip', rate='3/m', block=True)
def resend_confirmation(request):
    profile = get_or_create_profile(request.user)
    if profile.email_confirmed:
        messages.info(request, "Ваш email уже подтверждён.")
        return redirect('profile')

    profile.rotate_confirmation_token()
    if _send_confirmation_email(request.user, profile, request):
        messages.success(
            request,
            "Письмо с подтверждением отправлено повторно. Пожалуйста, проверьте вашу почту."
        )
    else:
        messages.error(
            request,
            "Не удалось отправить письмо подтверждения. Попробуйте позже."
        )
    return redirect('profile')

@custom_login_required
@require_POST
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def reorder_view(request, order_id):
    """Копирует позиции заказа в корзину пользователя (доступно при любом остатке на складе)."""
    try:
        with transaction.atomic():
            original_order = (
                Order.objects.filter(id=order_id, user=request.user)
                .first()
            )
            if not original_order:
                return JsonResponse(
                    {
                        'success': False,
                        'message': 'Заказ не найден или нет доступа.',
                    },
                    status=404,
                )
            cart, _created = Cart.objects.get_or_create(user=request.user)
            cart.items.all().delete()
            order_items = list(
                original_order.items.select_related('product').all()
            )
            for item in order_items:
                existing = cart.items.filter(product_id=item.product_id).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save(update_fields=['quantity'])
                else:
                    CartItem.objects.create(
                        cart=cart,
                        product=item.product,
                        quantity=item.quantity,
                    )
        return JsonResponse(
            {
                'success': True,
                'redirect_url': reverse('view_cart'),
            }
        )
    except Exception:
        logger.exception(
            'reorder_view failed for user=%s order_id=%s',
            request.user.pk,
            order_id,
        )
        return JsonResponse(
            {
                'success': False,
                'message': 'Не удалось обновить корзину. Попробуйте снова.',
            },
            status=400,
        )


from django.contrib.auth import views as auth_views  # noqa: E402


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    template_name = 'accounts/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'accounts/email/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class RateLimitedPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')