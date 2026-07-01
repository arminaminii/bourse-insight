from django.urls import path
from companies import views

urlpatterns = [
    path('search/companies/', views.api_search_companies, name='api_search'),
    path('search-codal/', views.api_search_codal, name='api_search_codal'),
    path('search-codal/<str:symbol>/all/', views.api_search_codal_all, name='api_search_codal_all'),
    path('companies/<str:symbol>/reports/', views.api_company_reports, name='api_company_reports'),
    path('autocomplete/', views.api_autocomplete, name='api_autocomplete'),
    path('sectors/', views.api_sectors, name='api_sectors'),
    path('debug-codal/', views.api_debug_codal, name='api_debug_codal'),
]