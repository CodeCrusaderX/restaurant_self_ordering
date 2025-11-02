from django.urls import path
from . import views

urlpatterns = [
    path("table/", views.choose_table, name="choose_table"),
    path("table/submit/", views.choose_table_submit, name="choose_table_submit"),
    path('order/start/', views.order_start, name='order_start'),   # QR entry point ?t=<token>
    path('', views.home, name='home'),
    path('menu/', views.customer_menu, name='customer_menu'),      # menu after table set
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('place-order/', views.place_order, name='place_order'),
    path('order/<int:order_id>/upi/', views.upi_pay, name='upi_pay'),
    path('order/<int:order_id>/submit-upi/', views.submit_upi_txn, name='submit_upi_txn'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/order/<int:order_id>/status/<str:new_status>/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/bill/', views.order_bill, name='order_bill'),
    path('order/<int:order_id>/track/', views.track_order, name='track_order'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    #path('pay/<int:order_id>/', views.fake_pay, name='fake_pay'),
    #path('pay/<int:order_id>/mark-paid/', views.mark_paid, name='mark_paid'),
    path("pay/<int:order_id>/", views.upi_pay, name="upi_pay"),
    path("pay/<int:order_id>/submit/", views.submit_upi_txn, name="submit_upi_txn"),
    path("kitchen/order/<int:order_id>/verify/", views.verify_payment, name="verify_payment"),
    path('billing/', views.billing_dashboard, name='billing_dashboard'),
    


]
