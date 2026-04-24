from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('order/<int:order_id>/reorder/', views.reorder_view, name='reorder'),

    path('confirm-email/<str:token>/', views.confirm_email_view, name='confirm_email'),
    path('resend-confirmation/', views.resend_confirmation, name='resend_confirmation'),

    path('password-reset/', views.RateLimitedPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.RateLimitedPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
