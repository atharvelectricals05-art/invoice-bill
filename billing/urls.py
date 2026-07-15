from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Parties
    path('parties/', views.party_list, name='party_list'),
    path('parties/add/', views.party_create, name='party_create'),
    path('parties/<int:pk>/', views.party_detail, name='party_detail'),
    path('parties/<int:pk>/edit/', views.party_edit, name='party_edit'),

    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),

    # Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/record/', views.payment_create, name='payment_create'),
    path('payments/party-invoices/', views.party_invoices, name='party_invoices'),

    # Company
    path('company/', views.company_profile, name='company_profile'),
]
