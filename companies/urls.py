from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/<str:symbol>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('sectors/<str:code>/', views.SectorDetailView.as_view(), name='sector_detail'),
    path('api/search/', views.api_search_companies, name='api_search'),
    path('api/search-codal/', views.api_search_codal, name='api_search_codal'),
    path('api/search-codal/<str:symbol>/all/', views.api_search_codal_all, name='api_search_codal_all'),
    path('api/companies/<str:symbol>/reports/', views.api_company_reports, name='api_company_reports'),
    path('api/autocomplete/', views.api_autocomplete, name='api_autocomplete'),
    path('api/sectors/', views.api_sectors, name='api_sectors'),
    path('api/debug-codal/', views.api_debug_codal, name='api_debug_codal'),
]