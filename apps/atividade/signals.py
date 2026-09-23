from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from apps.saas_tenants.schema import no_schema_publico

from .services import registrar_atividade


@receiver(user_logged_in)
def registrar_login(sender, user, request, **kwargs):
    if no_schema_publico():
        return
    registrar_atividade(user, "login", "Login no sistema")


@receiver(user_logged_out)
def registrar_logout(sender, user, request, **kwargs):
    if user is None or no_schema_publico():
        return
    registrar_atividade(user, "logout", "Logout do sistema")
