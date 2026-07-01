from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('companies.api_urls')),
    path('reports/', include('reports.urls')),
    path('', include('companies.urls')),
]