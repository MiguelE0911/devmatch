from django.urls import path
from apps.applications.views import (
    mis_postulaciones_view,
    postular_postulacion_view,
    retirar_postulacion_view,
)

app_name = 'applications'

urlpatterns = [
    path('mis-postulaciones/', mis_postulaciones_view, name='mis_postulaciones'),
    path('mis-postulaciones/<int:pk>/retirar/', retirar_postulacion_view, name='retirar_postulacion'),
    path('postular/<int:pk>/', postular_postulacion_view, name='postular'),
]
