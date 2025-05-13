from django.shortcuts import render, redirect, get_object_or_404
from products.models import Order
from products.views import merge_session_cart_to_user_cart
from .forms import RegisterForm, LoginForm, CustomUserChangeForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .decorators import login_required, custom_login_required
from django.http import JsonResponse
from accounts.models import UserProfile
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from uuid import UUID

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = UserProfile.objects.create(user=user)
            
            # Отправка письма с подтверждением email
            current_site = get_current_site(request)
            mail_subject = 'Подтверждение регистрации на сайте Stroyma'
            message = render_to_string('accounts/email/email_confirmation.html', {
                'user': user,
                'domain': current_site.domain,
                'protocol': 'https' if request.is_secure() else 'http',
                'token': profile.confirmation_token,
            })
            
            to_email = form.cleaned_data.get('email')
            send_mail(mail_subject, message, settings.EMAIL_HOST_USER, [to_email])
            
            login(request, user)
            merge_session_cart_to_user_cart(request)
            messages.success(request, "Вы успешно зарегистрировались! На вашу почту отправлено письмо с подтверждением.")
            return JsonResponse({'success': True})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'success': False, 'message': errors}, status=400)
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def confirm_email_view(request, token):
    try:
        profile = get_object_or_404(UserProfile, confirmation_token=UUID(token))
        profile.email_confirmed = True
        profile.save()
        success = True
        messages.success(request, "Ваш email успешно подтвержден!")
    except (ValueError, UserProfile.DoesNotExist):
        success = False
        messages.error(request, "Ссылка для подтверждения email недействительна!")
    
    return render(request, 'accounts/email_confirmation.html', {'success': success})

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, "Вы уже авторизованы.")
        return redirect('profile')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                merge_session_cart_to_user_cart(request)
                messages.info(request, f"Вы вошли как {username}.")
                return redirect("product_list")
            else:
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
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/profile.html', {'orders': orders})

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