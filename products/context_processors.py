from .models import Cart


def cart_info(request):
    """
    Глобальный контекст для бэйджа корзины в header/mobile-nav.
    Считает сумму quantity (а не число позиций) для авторизованного пользователя
    и для гостя (сессия).
    """
    count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                count = sum(item.quantity for item in cart.items.all())
        else:
            session_cart = request.session.get('cart', {}) or {}
            count = sum(int(q) for q in session_cart.values())
    except Exception:
        count = 0
    return {'cart_item_count': count}
