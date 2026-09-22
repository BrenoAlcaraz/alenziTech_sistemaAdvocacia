from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .services import registrar_atividade


@receiver(user_logged_in)
def registrar_login(sender, user, request, **kwargs):
    registrar_atividade(user, "login", "Login no sistema")


@receiver(user_logged_out)
def registrar_logout(sender, user, request, **kwargs):
    if user is not None:
        registrar_atividade(user, "logout", "Logout do sistema")
