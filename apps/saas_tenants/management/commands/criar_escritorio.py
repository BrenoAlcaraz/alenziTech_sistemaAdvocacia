from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.saas_tenants.onboarding import ErroOnboarding, criar_escritorio


class Command(BaseCommand):
    help = "Cria um escritório pronto para uso: schema, domínio, identidade visual e dono."

    def add_arguments(self, parser):
        parser.add_argument("--nome", required=True)
        parser.add_argument("--slug", required=True)
        parser.add_argument("--admin-usuario", required=True)
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-nome", required=True)

    def handle(self, *args, **opcoes):
        self.stdout.write("Criando escritório (schema e migrations)...")
        try:
            criado = criar_escritorio(
                nome=opcoes["nome"],
                slug=opcoes["slug"],
                admin_usuario=opcoes["admin_usuario"],
                admin_email=opcoes["admin_email"],
                admin_nome=opcoes["admin_nome"],
            )
        except ErroOnboarding as erro:
            raise CommandError(str(erro))
        except Exception as erro:
            raise CommandError(f"Falha ao criar o escritório; nada foi mantido. Motivo: {erro}")

        self.stdout.write(self.style.SUCCESS("Escritório criado."))
        self.stdout.write(f"  Escritório: {criado.escritorio.nome}")
        self.stdout.write(f"  Endereço:   {self._endereco(criado.dominio)}")
        self.stdout.write(f"  Usuário:    {criado.usuario}")
        self.stdout.write(f"  Senha:      {criado.senha}")
        self.stdout.write(self.style.WARNING(
            "Senha provisória exibida apenas agora — repasse ao dono com segurança."
        ))

    def _endereco(self, dominio):
        # runserver escuta na 8000 em dev; em produção o proxy atende em HTTPS.
        return f"http://{dominio}:8000" if settings.DEBUG else f"https://{dominio}"
