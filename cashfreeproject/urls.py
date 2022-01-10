from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('customapi/', include('customapi.urls')),
    path('admin/', admin.site.urls),
]
