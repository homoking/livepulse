from django.contrib import admin
from django.urls import path, include
from lipapp import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),      # صفحهٔ خانه‌ی واقعی
    path("healthz", views.healthz, name="healthz"),
    path("version", views.version, name="version"),
    path("", include("lipapp.urls")),       # روت‌های اپ
]
