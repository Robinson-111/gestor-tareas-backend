"""
Rutas de la API, agrupadas para montarse bajo un prefijo versionado.

El prefijo (`/api/v1/`) se define en `config/urls.py`; aquí solo se declaran
los recursos. Para una versión nueva incompatible se crea `config/api_v2_urls.py`
y se monta en `/api/v2/`, dejando `v1` funcionando mientras se migra el cliente.
"""

from django.urls import include, path

urlpatterns = [
    path('auth/', include('auth.urls')),
    path('users/', include('account.urls')),
    path('modules/<int:id>/tasks/', include('tasks.urls')),
    path('modules/', include('modules.urls')),
]
