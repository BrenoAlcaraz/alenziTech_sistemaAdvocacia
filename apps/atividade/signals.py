from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .services import registrar_atividade


@receiver(user_logged_in)
def registrar_login(sender, user, request, **kwargs):
    registrar_atividade(user, "login", "Login no sistema")
