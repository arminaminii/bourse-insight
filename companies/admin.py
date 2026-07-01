from django.contrib import admin
from .models import Sector, Company


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'sector', 'company_type', 'is_active')
    search_fields = ('symbol', 'name')
    list_filter = ('company_type', 'is_active', 'sector')
    list_per_page = 50