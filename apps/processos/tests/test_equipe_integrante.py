"""
Testes de vínculo dinâmico de Equipe como integrante habilitado do
Processo (specs/grupo-integrante-participante-dinamico.md) — reaproveita
o mesmo motor de apps/accounts/vinculo_equipe.py testado em
apps/accounts/tests/test_vinculo_equipe.py; aqui cobre a integração real
via view + sinal de MembroEquipe, autorização (mesma
`gerir_habilitar_usuario_processos` de sempre, nenhuma nova) e que não
afeta o responsável principal.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    Equipe,
    HabilitacaoPapel,
    MembroEquipe,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    MODULO_GERIR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo


class EquipeIntegranteBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _autorizar_processos(self, user, *, nivel=NIVEL_SOMENTE_SEUS):
        papel = PapelAcesso.objects.create(nome=f"Papel Processos {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=nivel
        )

    def _conceder_gerir_habilitar(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel="",
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_USUARIO_PROCESSOS, ativo=True,
        )

    def _processo(self, responsavel, titulo="Processo Equipe Integrante"):
        return Processo.objects.create(titulo=titulo, responsavel=responsavel, status="ativo")


class TestAdicionarERemoverEquipeIntegrante(EquipeIntegranteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "equipe_integrante_add_remove"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_equipe_integrante")
        self._autorizar_processos(self.responsavel)
        self.gestor = self._user("gestor_equipe_integrante")
        self._conceder_gerir_habilitar(self.gestor)
        self.membro_a = self._user("membro_a_equipe_integrante")
        self.membro_b = self._user("membro_b_equipe_integrante")
        self.equipe = Equipe.objects.create(nome="Equipe Cível Integrante")
        MembroEquipe.objects.create(usuario=self.membro_a, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=self.equipe, ativo=True)
        self.processo = self._processo(self.responsavel)
        self.client.force_login(self.gestor)

    def test_adicionar_equipe_habilita_todos_os_membros_atuais(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/?aba=integrantes", fetch_redirect_response=False
        )
        self.assertIn(self.membro_a, self.processo.integrantes_habilitados.all())
        self.assertIn(self.membro_b, self.processo.integrantes_habilitados.all())

    def test_adicionar_equipe_nao_altera_responsavel_principal(self):
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.responsavel.pk)

    def test_remover_equipe_desfaz_habilitacao_de_todos_os_membros(self):
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        r = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/{self.equipe.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.membro_a, self.processo.integrantes_habilitados.all())
        self.assertNotIn(self.membro_b, self.processo.integrantes_habilitados.all())

    def test_sem_habilitacao_gerir_e_negado(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.processo.integrantes_habilitados.count(), 0)


class TestSincronizacaoDinamicaViaProcesso(EquipeIntegranteBase):
    """Um novo membro que entra na equipe depois aparece habilitado
    automaticamente, sem ação manual; quem sai perde o acesso que vinha
    só da equipe."""

    @classmethod
    def get_test_schema_name(cls):
        return "equipe_integrante_sincronizacao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_sync_integrante")
        self._autorizar_processos(self.responsavel)
        self.gestor = self._user("gestor_sync_integrante")
        self._conceder_gerir_habilitar(self.gestor)
        self.equipe = Equipe.objects.create(nome="Equipe Sincronização")
        self.processo = self._processo(self.responsavel)
        self.client.force_login(self.gestor)
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )

    def test_novo_membro_da_equipe_e_habilitado_automaticamente(self):
        novo = self._user("novo_membro_sync_integrante")
        MembroEquipe.objects.create(usuario=novo, equipe=self.equipe, ativo=True)

        self.assertIn(novo, self.processo.integrantes_habilitados.all())

    def test_membro_que_sai_perde_o_acesso(self):
        saindo = self._user("saindo_membro_sync_integrante")
        vinculo = MembroEquipe.objects.create(usuario=saindo, equipe=self.equipe, ativo=True)
        self.assertIn(saindo, self.processo.integrantes_habilitados.all())

        vinculo.delete()

        self.assertNotIn(saindo, self.processo.integrantes_habilitados.all())

    def test_membro_desativado_perde_o_acesso(self):
        vinculo = MembroEquipe.objects.create(
            usuario=self._user("inativado_sync_integrante"), equipe=self.equipe, ativo=True
        )
        usuario = vinculo.usuario
        self.assertIn(usuario, self.processo.integrantes_habilitados.all())

        vinculo.ativo = False
        vinculo.save()

        self.assertNotIn(usuario, self.processo.integrantes_habilitados.all())

    def test_usuario_adicionado_individualmente_nao_e_afetado_por_sair_da_equipe(self):
        pessoa = self._user("individual_sync_integrante")
        self._autorizar_processos(pessoa)
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": pessoa.pk},
            HTTP_HOST=self.http_host,
        )
        vinculo = MembroEquipe.objects.create(usuario=pessoa, equipe=self.equipe, ativo=True)
        vinculo.delete()

        self.assertIn(pessoa, self.processo.integrantes_habilitados.all())
