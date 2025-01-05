
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse

def create_superuser(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "adminpassword")
        return HttpResponse("Superuser created successfully.")
    return HttpResponse("Superuser already exists.")

urlpatterns = [
    path('', include('store.urls')),
    path('admin/', admin.site.urls),  # This enables the Django admin interface
    path('create_superuser/', create_superuser),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)