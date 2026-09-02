"""
Testes de autorização de módulo para apps/processos/views.py.

Cobre exclusivamente tem_permissao_modulo(user, "processos") nas nove
rotas existentes (lista, detalhe, novo, editar, arquivados, arquivar,
reabrir, adicionar_movimentacao, adicionar_parte). Por decisão de
produto (PDR-0010), esta versão de Processos NÃO aplica as
habilitações granulares já existentes no kernel (processos_criar,
processos_editar, processos_andamento_adicionar) — um usuário com o
módulo processos autorizado alcança todas as operações atuais,
independentemente dessas habilitações. Escopo de dados por responsável
(Fase B) também não é tratado por este arquivo.

Segue o mesmo padrão de fixtures de
apps/clientes/tests/test_autorizacao.py (_user, _new_papel,
_assign_papel, _pp) sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.clientes.models import Cliente
from apps.processos.models import Processo

_PROCESSO_FORM_BASE = {
    "area_direito": "CÍVEL",
    "fase": "conhecimento",
    "instancia": "1ª Instância",
    "gratuidade_justica_status": "nao_requerida",
}


class ProcessosAutorizacaoBase(TenantTestCase):
    """Helpers de fixture e de acesso HTTP compartilhados pelos testes deste módulo."""

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _set_admin_flag(self, user, value=True):
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=value)

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _cliente(self, *, responsavel, **kwargs):
        defaults = {"nome_razao_social": "Cliente Teste Processos", "tipo": "PF"}
        defaults.update(kwargs)
        return Cliente.objects.create(responsavel=responsavel, **defaults)

    def _processo(self, *, responsavel, cliente=None, **kwargs):
        defaults = {"titulo": "Processo Teste"}
        defaults.update(kwargs)
        return Processo.objects.create(responsavel=responsavel, cliente=cliente, **defaults)

    def _processo_payload(self, cliente, **overrides):
        payload = {"titulo": "Processo Form", "cliente": cliente.pk}
        payload.update(_PROCESSO_FORM_BASE)
        payload.update(overrides)
        return payload


class TestProcessosAutorizacaoModuloNegado(ProcessosAutorizacaoBase):
    """
    Usuário autenticado sem autorização do módulo `processos`
    (nenhum UsuarioPapel, nenhum Group técnico) — as nove rotas negam.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_negado"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Negado"
        tenant.slug = "wi0004-processos-negado"

    def setUp(self):
        super().setUp()
        self.user = self._user("sem_modulo_processos")
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_lista_negada(self):
        r = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_detalhe_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_arquivados_negado(self):
        r = self.client.get("/processos/arquivados/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_get_negado(self):
        r = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_post_negado_nao_cria_processo(self):
        antes = Processo.objects.count()
        r = self.client.post(
            "/processos/novo/",
            self._processo_payload(self.cliente, titulo="Tentativa Negada"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Processo.objects.count(), antes)

    def test_editar_get_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_post_negado_preserva_valores(self):
        titulo_original = self.processo.titulo
        r = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._processo_payload(self.cliente, titulo="Titulo Alterado Indevido"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.titulo, titulo_original)

    def test_arquivar_get_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/arquivar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_arquivar_post_negado_nao_altera_status(self):
        r = self.client.post(f"/processos/{self.processo.pk}/arquivar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "ativo")

    def test_reabrir_get_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/reabrir/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_reabrir_post_negado_nao_altera_status(self):
        self.processo.status = "arquivado"
        self.processo.save(update_fields=["status"])
        r = self.client.post(f"/processos/{self.processo.pk}/reabrir/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "arquivado")

    def test_adicionar_movimentacao_get_negado(self):
        r = self.client.get(
            f"/processos/{self.processo.pk}/movimentacoes/nova/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 403)

    def test_adicionar_movimentacao_post_negado_nao_cria(self):
        antes = self.processo.movimentacoes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            {"tipo": "andamento", "data": "2026-08-19T10:00", "descricao": "Tentativa negada"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.processo.movimentacoes.count(), antes)

    def test_adicionar_parte_get_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/partes/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_adicionar_parte_post_negado_nao_cria(self):
        antes = self.processo.partes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/partes/nova/",
            {"nome": "Parte Tentativa", "papel": "autor"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.processo.partes.count(), antes)


class TestProcessosAutorizacaoModuloConcedido(ProcessosAutorizacaoBase):
    """
    Usuário autorizado ao módulo `processos` (via papel dinâmico)
    preserva o comportamento HTTP existente das nove rotas — incluindo
    criar/editar/adicionar movimentação, mesmo sem processos_criar/
    processos_editar/processos_andamento_adicionar (PDR-0010:
    habilitações não aplicadas nesta versão).
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_concedido"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Concedido"
        tenant.slug = "wi0004-processos-concedido"

    def setUp(self):
        super().setUp()
        self.user = self._user("com_modulo_processos")
        papel = self._new_papel("Papel Processos Concedido")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        # Nenhuma HabilitacaoPapel concedida — PDR-0010 determina que
        # processos_criar/processos_editar/processos_andamento_adicionar
        # não restringem operações de Processos nesta versão.
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_lista_autorizada(self):
        r = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/lista.html")

    def test_detalhe_autorizado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/detalhe.html")

    def test_arquivados_autorizado(self):
        r = self.client.get("/processos/arquivados/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/arquivados.html")

    def test_novo_get_autorizado(self):
        r = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/form.html")

    def test_novo_post_autorizado_cria_processo_sem_habilitacao(self):
        antes = Processo.objects.count()
        r = self.client.post(
            "/processos/novo/",
            self._processo_payload(self.cliente, titulo="Processo Novo Autorizado"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Processo.objects.count(), antes + 1)
        criado = Processo.objects.get(titulo="Processo Novo Autorizado")
        self.assertEqual(criado.responsavel, self.user)

    def test_editar_get_autorizado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "processos/form.html")

    def test_editar_post_autorizado_altera_processo_sem_habilitacao(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._processo_payload(self.cliente, titulo="Titulo Alterado Autorizado"),
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/", fetch_redirect_response=False
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.titulo, "Titulo Alterado Autorizado")

    def test_arquivar_post_autorizado_arquiva_processo(self):
        r = self.client.post(f"/processos/{self.processo.pk}/arquivar/", HTTP_HOST=self.http_host)
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/", fetch_redirect_response=False
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "arquivado")

    def test_reabrir_post_autorizado_reabre_processo(self):
        self.processo.status = "arquivado"
        self.processo.save(update_fields=["status"])
        r = self.client.post(f"/processos/{self.processo.pk}/reabrir/", HTTP_HOST=self.http_host)
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/", fetch_redirect_response=False
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "ativo")

    def test_adicionar_movimentacao_post_autorizado_sem_habilitacao(self):
        antes = self.processo.movimentacoes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            {"tipo": "andamento", "data": "2026-08-19T10:00", "descricao": "Movimentação autorizada"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/?aba=andamentos", fetch_redirect_response=False
        )
        self.assertEqual(self.processo.movimentacoes.count(), antes + 1)

    def test_adicionar_parte_post_autorizado_sem_habilitacao(self):
        antes = self.processo.partes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/partes/nova/",
            {"nome": "Parte Autorizada", "papel": "autor"},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/?aba=partes", fetch_redirect_response=False
        )
        self.assertEqual(self.processo.partes.count(), antes + 1)


class TestProcessosAutorizacaoAdministrador(ProcessosAutorizacaoBase):
    """
    Administrador do escritório (is_admin_escritorio=True) continua
    autorizado a todas as operações de Processos, sem depender de
    UsuarioPapel/PermissaoPapel — tem_permissao_modulo() já resolve
    usuario_admin_escritorio() internamente antes de qualquer regra
    individual ou de papel.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_admin"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Admin"
        tenant.slug = "wi0004-processos-admin"

    def setUp(self):
        super().setUp()
        self.user = self._user("admin_escritorio_processos")
        self._set_admin_flag(self.user, True)
        # Nenhum UsuarioPapel/PermissaoPapel concedido — o acesso do
        # Administrador não depende do kernel de papéis dinâmicos.
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_lista_autorizada_para_admin(self):
        r = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_detalhe_autorizado_para_admin(self):
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_novo_post_autorizado_para_admin(self):
        antes = Processo.objects.count()
        r = self.client.post(
            "/processos/novo/",
            self._processo_payload(
                self.cliente,
                titulo="Processo Admin",
                responsavel=self.user.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Processo.objects.count(), antes + 1)

    def test_arquivar_post_autorizado_para_admin(self):
        r = self.client.post(f"/processos/{self.processo.pk}/arquivar/", HTTP_HOST=self.http_host)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "arquivado")
