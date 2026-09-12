from django.apps import AppConfig


class ProcessosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.processos"
    verbose_name = "Processos"

    def ready(self):
        import apps.processos.signals  # noqa: F401
