from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count


class StroymaDashboardMixin:
    """Adds KPI data to the admin index page context."""

    def index(self, request, extra_context=None):
        from products.models import Product, Order, OrderItem

        extra_context = extra_context or {}
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        orders_today = Order.objects.filter(created_at__gte=today_start).count()
        orders_week = Order.objects.filter(created_at__gte=week_ago).count()

        revenue_week = sum(
            o.total_cost for o in Order.objects.filter(created_at__gte=week_ago)
        )
        revenue_month = sum(
            o.total_cost for o in Order.objects.filter(created_at__gte=month_ago)
        )

        active_orders = Order.objects.filter(
            status__in=["pending", "processing", "shipped"]
        ).count()

        low_stock = Product.objects.filter(stock__lte=5).order_by("stock")[:10]
        total_products = Product.objects.count()
        total_users_with_orders = (
            Order.objects.values("user").distinct().count()
        )

        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:8]

        status_counts = dict(
            Order.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        extra_context.update({
            "kpi_orders_today": orders_today,
            "kpi_orders_week": orders_week,
            "kpi_revenue_week": revenue_week,
            "kpi_revenue_month": revenue_month,
            "kpi_active_orders": active_orders,
            "kpi_low_stock": low_stock,
            "kpi_low_stock_count": low_stock.count() if hasattr(low_stock, 'count') else len(low_stock),
            "kpi_total_products": total_products,
            "kpi_total_clients": total_users_with_orders,
            "kpi_recent_orders": recent_orders,
            "kpi_status_pending": status_counts.get("pending", 0),
            "kpi_status_processing": status_counts.get("processing", 0),
            "kpi_status_shipped": status_counts.get("shipped", 0),
            "kpi_status_completed": status_counts.get("completed", 0),
            "kpi_status_canceled": status_counts.get("canceled", 0),
        })

        return super().index(request, extra_context=extra_context)


class StroymAdminSite(StroymaDashboardMixin, admin.AdminSite):
    site_header = "Stroyma"
    site_title = "Stroyma — Панель управления"
    index_title = "Панель управления"
