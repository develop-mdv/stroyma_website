from .models import Cart
from django.db.models import Q, Sum


def cart_info(request):
    """
    Глобальный контекст для бэйджа корзины в header/mobile-nav.
    Считает сумму quantity (а не число позиций) для авторизованного пользователя
    и для гостя (сессия).
    """
    count = 0
    try:
        if request.user.is_authenticated:
            count = Cart.objects.filter(user=request.user).aggregate(
                quantity=Sum('items__quantity', filter=Q(items__product__is_published=True))
            )['quantity'] or 0
        else:
            session_cart = request.session.get('cart', {}) or {}
            count = sum(int(q) for q in session_cart.values())
    except Exception:
        count = 0
    return {'cart_item_count': count}
