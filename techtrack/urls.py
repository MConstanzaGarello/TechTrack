from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from inventario import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("ingresar/", auth_views.LoginView.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("inventario/", include("inventario.urls")),
    path("admin/", admin.site.urls),
]

handler403 = "inventario.views.acceso_denegado"
handler404 = "inventario.views.no_encontrado"
