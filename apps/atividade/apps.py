from django.apps import AppConfig


class AtividadeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.atividade"
    verbose_name = "Atividade"

    def ready(self):
        import apps.atividade.signals  # noqa: F401
