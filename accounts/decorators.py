# accounts/decorators.py

from functools import wraps
from django.shortcuts import redirect


def custom_login_required(function=None, login_url='/accounts/login/'):
    """Декоратор, перенаправляющий неавторизованных пользователей на страницу логина."""
    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            return redirect(login_url)
        return _wrapped_view
    if function:
        return _decorator(function)
    return _decorator
