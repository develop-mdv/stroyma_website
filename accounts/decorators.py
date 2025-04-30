# accounts/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.utils.decorators import decorator_from_middleware_with_args
from django.contrib.auth.models import AnonymousUser

def login_required(function=None, login_url='/login/'):
    """
    Декоратор для проверки авторизации.
    Если пользователь не залогинен, перенаправляет на указанный URL.
    """
    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            else:
                return redirect(login_url)
        return _wrapped_view
    if function:
        return _decorator(function)
    return _decorator

def custom_login_required(function=None, login_url='/accounts/login/'):
    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            else:
                return redirect(login_url)
        return _wrapped_view
    if function:
        return _decorator(function)
    return _decorator