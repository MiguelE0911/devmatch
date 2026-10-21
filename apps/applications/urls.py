from django.urls import path
from apps.applications.views import mis_postulaciones_view

app_name = 'applications'

urlpatterns = [
    path('mis-postulaciones/', mis_postulaciones_view, name='mis_postulaciones'),
]