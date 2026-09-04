"""
Testes de autorização de módulo e de habilitação para
apps/processos/views.py.

Cobre tem_permissao_modulo(user, "processos") nas nove rotas
existentes (lista, detalhe, novo, editar, arquivados, arquivar,
reabrir, adicionar_movimentacao, adicionar_parte), e, a partir de
PDR-0017, tem_habilitacao(user, "processos", <item>) para
processos_criar (novo), processos_editar (editar) e
processos_andamento_adicionar (adicionar_movimentacao) — módulo
autorizado não equivale mais a poder criar/editar/adicionar andamento
sem a habilitação específica. As demais rotas (arquivar, reabrir,
apensos, partes) continuam regidas apenas pela autorização binária de
módulo, conforme PDR-0010. Escopo de dados por responsável (Fase B)
também não é tratado por este arquivo.

Segue o mesmo padrão de fixtures de
apps/clientes/tests/test_autorizacao.py (_user, _new_papel,
_assign_papel, _pp, _hp) sobre django_tenants.test.cases.TenantTestCase.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_ANDAMENTO_ADICIONAR,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_EDITAR,
    MODULO_PROCESSOS,
    NIVEL_TODOS,
)
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

    def _hp(self, papel, modulo, item, *, ativo=True):
        return HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=modulo, item=item, ativo=ativo
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
    Usuário autorizado ao módulo `processos` (via papel dinâmico) e às
    três habilitações de PDR-0017 (processos_criar, processos_editar,
    processos_andamento_adicionar) preserva o comportamento HTTP
    existente das nove rotas — caminho autorizado completo (Camada 1 +
    Camada 2).
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
        # As três habilitações de PDR-0017 são concedidas neste fixture
        # para representar o caminho autorizado completo de novo/editar/
        # adicionar_movimentacao (Camada 1 + Camada 2).
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_ANDAMENTO_ADICIONAR)
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

    def test_novo_post_autorizado_cria_processo(self):
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

    def test_editar_post_autorizado_altera_processo(self):
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

    def test_adicionar_movimentacao_post_autorizado(self):
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


class TestProcessosAutorizacaoHabilitacaoCriarAusente(ProcessosAutorizacaoBase):
    """
    Usuário com módulo `processos` autorizado, mas sem
    `processos_criar` (Camada 2, PDR-0017) — prova que módulo
    autorizado não equivale a poder criar processo.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_sem_criar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Sem Criar"
        tenant.slug = "wi0004-processos-sem-criar"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_processos_criar")
        papel = self._new_papel("Papel Processos Sem Criar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        # Nenhuma HabilitacaoPapel para HAB_PROCESSOS_CRIAR — módulo
        # aberto, habilitação de criação ausente.
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)

    def test_novo_get_negado(self):
        r = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_novo_post_negado_nao_cria_processo(self):
        antes = Processo.objects.count()
        r = self.client.post(
            "/processos/novo/",
            self._processo_payload(self.cliente, titulo="Tentativa Sem Habilitacao"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Processo.objects.count(), antes)


class TestProcessosAutorizacaoHabilitacaoEditarAusente(ProcessosAutorizacaoBase):
    """
    Usuário com módulo `processos` autorizado, mas sem
    `processos_editar` (Camada 2, PDR-0017) — prova que módulo
    autorizado não equivale a poder editar processo, mesmo dentro do
    próprio escopo de mutação.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_sem_editar"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Sem Editar"
        tenant.slug = "wi0004-processos-sem-editar"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_processos_editar")
        papel = self._new_papel("Papel Processos Sem Editar")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        # Nenhuma HabilitacaoPapel para HAB_PROCESSOS_EDITAR — módulo
        # aberto, habilitação de edição ausente.
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_editar_get_negado(self):
        r = self.client.get(f"/processos/{self.processo.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 403)

    def test_editar_post_negado_preserva_valores(self):
        titulo_original = self.processo.titulo
        r = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._processo_payload(self.cliente, titulo="Titulo Alterado Sem Habilitacao"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.titulo, titulo_original)


class TestProcessosAutorizacaoHabilitacaoAndamentoAusente(ProcessosAutorizacaoBase):
    """
    Usuário com módulo `processos` autorizado, mas sem
    `processos_andamento_adicionar` (Camada 2, PDR-0017) — prova que
    módulo autorizado não equivale a poder adicionar andamento.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "wi0004_processos_sem_andamento"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0004 Processos Sem Andamento"
        tenant.slug = "wi0004-processos-sem-andamento"

    def setUp(self):
        super().setUp()
        self.user = self._user("modulo_sem_processos_andamento")
        papel = self._new_papel("Papel Processos Sem Andamento")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_PROCESSOS)
        # Nenhuma HabilitacaoPapel para HAB_PROCESSOS_ANDAMENTO_ADICIONAR
        # — módulo aberto, habilitação de andamento ausente.
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user)
        self.processo = self._processo(responsavel=self.user, cliente=self.cliente)

    def test_adicionar_movimentacao_post_negado_nao_cria(self):
        antes = self.processo.movimentacoes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            {"tipo": "andamento", "data": "2026-08-19T10:00", "descricao": "Tentativa negada"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.processo.movimentacoes.count(), antes)


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

    def test_editar_post_autorizado_para_admin_sem_habilitacao(self):
        # tem_habilitacao() já concede automaticamente ao Administrador
        # do escritório (bypass interno do kernel) — sem depender de
        # HabilitacaoPapel para processos_editar.
        r = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._processo_payload(
                self.cliente, titulo="Titulo Alterado Admin", responsavel=self.user.pk
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.titulo, "Titulo Alterado Admin")

    def test_adicionar_movimentacao_post_autorizado_para_admin_sem_habilitacao(self):
        antes = self.processo.movimentacoes.count()
        r = self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            {"tipo": "andamento", "data": "2026-08-19T10:00", "descricao": "Movimentação admin"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.processo.movimentacoes.count(), antes + 1)
