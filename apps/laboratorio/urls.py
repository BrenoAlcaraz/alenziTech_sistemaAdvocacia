from django.urls import path
from . import views

app_name = "laboratorio"

urlpatterns = [
    path("laboratorio/", views.index, name="index"),
]
