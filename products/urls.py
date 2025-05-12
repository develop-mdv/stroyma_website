from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:pk>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('search-ajax/', views.search_ajax, name='search_ajax'),
    path('quick-view/<int:pk>/', views.quick_view, name='quick_view'),
    path('color-selection/', views.color_selection, name='color_selection'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('get-subcategories/', views.get_subcategories, name='get_subcategories'),
]