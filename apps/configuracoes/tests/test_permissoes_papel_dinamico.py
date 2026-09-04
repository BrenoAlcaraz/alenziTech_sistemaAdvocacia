"""
Testes da Issue #6 (spec `specs/gerir-papeis-e-habilitacoes-granulares.md`,
seção "3. Permissão de módulo/nível e habilitação granular por papel").

Cobre a extensão de `configuracoes:permissoes`: aba por papel dinâmico
ativo (`PermissaoPapel` via `papel`) e habilitação granular
(`HabilitacaoPapel`) tanto para papel dinâmico quanto para tipo de
conta legado (Limitado/Financeiro) — hoje sem UI antes desta feature.

Autorização (403 sem `gerir_habilitar_terceiros`, bypass de
Administrador) já está coberta em
`apps/configuracoes/tests/test_autorizacao.py` (PDR-0019) para a rota
`permissoes`; não duplicada aqui.

Segue o mesmo padrão de fixtures de test_autorizacao.py/test_papeis.py.
"""

from django_tenants.test.cases import TenantTestCase
from django.contrib.auth.models import User

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes import tem_habilitacao, tem_permissao_modulo
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_GERIR_HABILITAR_TERCEIROS,
    MODULO_CLIENTES,
    MODULO_GERIR,
)


class PermissoesPapelDinamicoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _conceder_gerir(self, user):
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_GERIR, ativo=True, nivel=""
        )
        HabilitacaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_TERCEIROS,
            ativo=True,
        )
        return papel


class TestPermissoesAbaPapelDinamico(PermissoesPapelDinamicoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "permissoes_aba_papel"

    def setUp(self):
        super().setUp()
        self.user = self._user("gestor_permissoes")
        self._conceder_gerir(self.user)
        self.client.force_login(self.user)
        self.papel_alvo = PapelAcesso.objects.create(nome="Estagiários", ativo=True)
        self.papel_inativo = PapelAcesso.objects.create(nome="Descontinuado", ativo=False)

    def test_papel_ativo_aparece_como_aba(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Estagiários")

    def test_papel_inativo_nao_aparece_como_aba(self):
        r = self.client.get("/configuracoes/permissoes/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Descontinuado")

    def test_post_papel_id_salva_modulo_e_nivel(self):
        r = self.client.post(
            "/configuracoes/permissoes/",
            {
                "papel_id": str(self.papel_alvo.pk),
                "ativo_clientes": "on",
                "nivel_clientes": "todos",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        pp = PermissaoPapel.objects.get(papel=self.papel_alvo, modulo=MODULO_CLIENTES)
        self.assertTrue(pp.ativo)
        self.assertEqual(pp.nivel, "todos")
        self.assertIsNone(pp.tipo_conta)

    def test_post_papel_id_salva_habilitacao_granular(self):
        r = self.client.post(
            "/configuracoes/permissoes/",
            {
                "papel_id": str(self.papel_alvo.pk),
                "ativo_clientes": "on",
                "nivel_clientes": "todos",
                f"hab_{MODULO_CLIENTES}_{HAB_CLIENTES_CRIAR}": "on",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            HabilitacaoPapel.objects.get(
                papel=self.papel_alvo, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR
            ).ativo
        )

        alvo = self._user("beneficiario_papel")
        UsuarioPapel.objects.create(usuario=alvo, papel=self.papel_alvo, ativo=True)
        self.assertTrue(tem_permissao_modulo(alvo, MODULO_CLIENTES))
        self.assertTrue(tem_habilitacao(alvo, MODULO_CLIENTES, HAB_CLIENTES_CRIAR))

    def test_post_papel_id_omitindo_habilitacao_desativa(self):
        HabilitacaoPapel.objects.create(
            papel=self.papel_alvo,
            tipo_conta=None,
            modulo=MODULO_CLIENTES,
            item=HAB_CLIENTES_CRIAR,
            ativo=True,
        )
        r = self.client.post(
            "/configuracoes/permissoes/",
            {"papel_id": str(self.papel_alvo.pk), "ativo_clientes": "on", "nivel_clientes": "todos"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(
            HabilitacaoPapel.objects.get(
                papel=self.papel_alvo, modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR
            ).ativo
        )

    def test_post_papel_id_inativo_nao_altera_nada(self):
        antes = PermissaoPapel.objects.filter(papel=self.papel_inativo).count()
        r = self.client.post(
            "/configuracoes/permissoes/",
            {
                "papel_id": str(self.papel_inativo.pk),
                "ativo_clientes": "on",
                "nivel_clientes": "todos",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            PermissaoPapel.objects.filter(papel=self.papel_inativo).count(), antes
        )

    def test_post_tipo_conta_salva_habilitacao_granular(self):
        r = self.client.post(
            "/configuracoes/permissoes/",
            {
                "tipo_conta": "limitado",
                "ativo_clientes": "on",
                "nivel_clientes": "somente_seus",
                f"hab_{MODULO_CLIENTES}_{HAB_CLIENTES_CRIAR}": "on",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            HabilitacaoPapel.objects.get(
                tipo_conta="limitado", modulo=MODULO_CLIENTES, item=HAB_CLIENTES_CRIAR
            ).ativo
        )
