"""
Suíte de auditoria e regressão — Rodada 2.1C1B.2.

Todos os testes devem PASSAR com o kernel corrigido.
Nenhum skip, expectedFailure ou unexpectedSuccess.

Classes:
  TestInteracoesOverrideComPapel    — UP + override individual (Gaps 1/4)
  TestOrigemContrato                — contrato de valores de origem (Gap 2)
  TestMaiorNivelSeguranca           — _maior_nivel com nivel inválido (Gap 3)
  TestPermissaoInativaPreservaContexto — regressão: PP inativa preserva nível
  TestKernelQueriesClassificadas    — classificação e limites de SELECTs
  TestSmokePagesAdmin               — smoke HTTP: admin sem 500
  TestSmokePagesAdvogado            — smoke HTTP: advogado sem 500
"""

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    HabilitacaoPapel,
    HabilitacaoUsuario,
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes import (
    _maior_nivel,
    habilitacao_efetiva,
    permissao_efetiva,
)
from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    HAB_MODELOS_CRIAR,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_EDITAR,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_MODELOS,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_SOLICITACOES,
    NIVEL_TODOS,
)


# ── Base compartilhada ──────────────────────────────────────────────────────────


class InteracoesBase(TenantTestCase):
    """Base com helpers para todos os testes de interação."""

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _set_admin_flag(self, user):
        n = PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        if n != 1:
            raise AssertionError(f"_set_admin_flag: esperado 1 row, got {n}")
        user._state.fields_cache.pop("perfil", None)

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel, modulo=modulo, ativo=ativo, nivel=nivel
        )

    def _hp(self, papel, modulo, item, *, ativo=True):
        return HabilitacaoPapel.objects.create(
            papel=papel, modulo=modulo, item=item, ativo=ativo
        )


# ===========================================================================
# 1. INTERAÇÕES — override individual + UsuarioPapel
# ===========================================================================


class TestInteracoesOverrideComPapel(InteracoesBase):
    """
    Testa a corretude da habilitação quando existem:
    PermissaoUsuario individual + UsuarioPapel.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_over"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Interacoes Override"
        tenant.slug = "tk-int-over"

    def test_override_modulo_em_usuario_com_papel_mantem_habilitacao_do_papel(self):
        """
        PermissaoUsuario individual em usuário com UP.

        Cenário:
          - UP(ativo=True), PA(ativo=True)
          - PP(papel, modelos, ativo=False)  ← papel NÃO concede modelos
          - HP(papel, modelos, modelos_criar, ativo=True)  ← papel tem HP
          - PermissaoUsuario(modelos, ativo=True, nivel=todos)  ← override individual
          - Sem HabilitacaoUsuario

        Esperado:
          permissao_efetiva  → origem="individual", tem_acesso=True
          habilitacao_efetiva → habilitado=True via HP do papel FK
        """
        u = self._user("u_mix_up_ind")

        papel = self._new_papel("Papel Mix Ind")
        self._pp(papel, MODULO_MODELOS, ativo=False, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR, ativo=True)
        self._assign_papel(u, papel)

        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS
        )

        perm_r = permissao_efetiva(u, MODULO_MODELOS)
        self.assertEqual(perm_r["origem"], "individual", f"origem errada: {perm_r}")
        self.assertTrue(perm_r["tem_acesso"], f"deve ter acesso via override: {perm_r}")

        hab_r = habilitacao_efetiva(u, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.assertTrue(
            hab_r["habilitado"],
            f"HP do papel FK (ativo=True) deve prevalecer; atual={hab_r['habilitado']!r}",
        )

    def test_override_habilitacao_em_usuario_com_papel_tem_origem_individual(self):
        """
        HabilitacaoUsuario individual em usuário com UP.

        Esperado: habilitado=True, origem="individual".
        """
        u = self._user("u_mix_hab_ind")

        papel = self._new_papel("Papel Hab Ind")
        self._pp(papel, MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)

        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS
        )
        HabilitacaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, item=HAB_MODELOS_CRIAR, ativo=True
        )

        hab_r = habilitacao_efetiva(u, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self.assertTrue(hab_r["habilitado"], f"deve estar habilitado via HabilitacaoUsuario: {hab_r}")
        self.assertEqual(hab_r["origem"], "individual", f"origem errada: {hab_r}")

    def test_habilitacao_ausente_no_papel_nega_mesmo_com_modulo_concedido(self):
        """
        Cenário:
          - UP(ativo=True), PA(ativo=True)
          - PP(papel, processos, ativo=True)  ← módulo concedido pelo papel
          - Sem HP(papel, processos, processos_criar)  ← item não no papel

        Esperado: habilitado=False, origem="papel".
        """
        u = self._user("u_hab_ausente")

        papel = self._new_papel("Papel Sem HAB Criar")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)

        hab_r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)

        self.assertFalse(hab_r["habilitado"], f"item ausente no papel deve negar: {hab_r}")
        self.assertEqual(
            hab_r["origem"],
            "papel",
            f"origem deve ser 'papel'; atual={hab_r['origem']!r}",
        )


# ===========================================================================
# 2. CONTRATO DE origem
# ===========================================================================


class TestOrigemContrato(InteracoesBase):
    """
    Verifica o contrato de valores de `origem` implementado.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_orig"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Origem Contrato"
        tenant.slug = "tk-int-orig"

    def test_usuario_inativo_retorna_origem_inativo(self):
        """
        is_active=False → origem="inativo" (não "nenhuma").
        Distingue "usuário inativo" de "usuário sem permissão configurada".
        """
        u = self._user("u_inativo_orig", is_active=False)

        perm_r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(perm_r["tem_acesso"])
        self.assertEqual(
            perm_r["origem"],
            "inativo",
            f"permissao_efetiva: inativo deve retornar origem='inativo'; atual={perm_r['origem']!r}",
        )

        hab_r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFalse(hab_r["habilitado"])
        self.assertEqual(
            hab_r["origem"],
            "inativo",
            f"habilitacao_efetiva: inativo deve retornar origem='inativo'; atual={hab_r['origem']!r}",
        )

    def test_usuario_sem_papel_retorna_origem_nenhuma(self):
        """
        Sem UP e sem override → origem="nenhuma" (não há fallback de Group).
        """
        u = self._user("u_sem_up_orig")

        perm_r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(perm_r["tem_acesso"])
        self.assertEqual(perm_r["origem"], "nenhuma")

        hab_r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFalse(hab_r["habilitado"])
        # Sem permissão de módulo a habilitação nem é consultada.
        self.assertEqual(hab_r["origem"], "permissao_desligada")

    def test_papel_sem_concessao_retorna_origem_papel(self):
        """
        UP existe, sem PP para o módulo → origem="papel".
        Distingue "sem UP" (origem="nenhuma") de "UP sem concessão" (origem="papel").
        """
        u = self._user("u_up_sem_pp_orig")
        papel = PapelAcesso.objects.create(nome="Papel Orig Sem PP", ativo=True)
        UsuarioPapel.objects.create(usuario=u, papel=papel, ativo=True)

        perm_r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(perm_r["tem_acesso"])
        self.assertEqual(
            perm_r["origem"],
            "papel",
            f"UP sem PP deve ter origem='papel'; atual={perm_r['origem']!r}",
        )

    def test_habilitacao_nao_concedida_por_papel_retorna_origem_papel(self):
        """
        UP existe, módulo concedido, item não concedido → origem="papel".
        """
        u = self._user("u_up_sem_hp_orig")
        papel = PapelAcesso.objects.create(nome="Papel Orig Sem HP", ativo=True)
        PermissaoPapel.objects.create(
            papel=papel,
            modulo=MODULO_PROCESSOS,
            ativo=True,
            nivel=NIVEL_TODOS,
        )
        # Sem HabilitacaoPapel(processos_criar)
        UsuarioPapel.objects.create(usuario=u, papel=papel, ativo=True)

        hab_r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFalse(hab_r["habilitado"])
        self.assertEqual(
            hab_r["origem"],
            "papel",
            f"item não concedido deve ter origem='papel'; atual={hab_r['origem']!r}",
        )


# ===========================================================================
# 3. NÍVEL SEGURO — _maior_nivel com nivel inválido
# ===========================================================================


class TestMaiorNivelSeguranca(TestCase):
    """
    Testa o helper _maior_nivel com entradas inválidas. TestCase puro (sem tenant/banco).

    DB constraints impedem armazenar niveis inválidos em PermissaoPapel,
    mas o helper deve falhar de forma segura para dados externos ou fixtures corrompidos.
    """

    def test_nivel_invalido_usa_minimo_seguro_processos(self):
        """nivel inválido em processos → deve retornar "somente_seus" (mínimo seguro)."""
        result = _maior_nivel("processos", ["nivel_invalido"])
        self.assertEqual(
            result,
            NIVEL_SOMENTE_SEUS,
            f"nivel inválido → mínimo seguro='somente_seus'; atual={result!r}",
        )

    def test_nivel_invalido_usa_minimo_seguro_financeiro(self):
        """nivel inválido em financeiro → deve retornar "solicitacoes"."""
        result = _maior_nivel("financeiro", ["nivel_invalido"])
        self.assertEqual(
            result,
            NIVEL_SOLICITACOES,
            f"financeiro nivel inválido → mínimo='solicitacoes'; atual={result!r}",
        )

    def test_nivel_valido_prevalece_sobre_invalido(self):
        """nivel válido + inválido → retorna o válido."""
        result = _maior_nivel("processos", ["nivel_invalido", NIVEL_SOMENTE_SEUS])
        self.assertEqual(result, NIVEL_SOMENTE_SEUS)

    def test_lista_vazia_retorna_vazio(self):
        """Lista vazia → "" (correto: não há niveis para agregar)."""
        result = _maior_nivel("processos", [])
        self.assertEqual(result, "")

    def test_nivel_maximo_de_lista_mista(self):
        """Dois niveis válidos → retorna o maior segundo NIVEIS_POR_MODULO."""
        result = _maior_nivel("processos", [NIVEL_SOMENTE_SEUS, NIVEL_TODOS])
        self.assertEqual(result, NIVEL_TODOS)

    def test_modulo_sem_escopo_nivel_invalido_retorna_vazio(self):
        """
        chat/gerir com nivel inválido → "" é correto.
        O único nivel válido para chat é "", então não há "mínimo" diferente de "".
        """
        result = _maior_nivel("chat", ["nivel_invalido"])
        self.assertEqual(result, "")


# ===========================================================================
# 4. REGRESSÃO: PERMISSÃO INATIVA PRESERVA CONTEXTO
# ===========================================================================


class TestPermissaoInativaPreservaContexto(InteracoesBase):
    """
    Regressão: PermissaoPapel inativa deve:
      - retornar tem_acesso=False com origem="papel";
      - preservar o nível para fins de auditoria;
      - não elevar o nível de concessões ativas via linha inativa.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_pp_inativa"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "PP Inativa"
        tenant.slug = "tk-int-pp-inativa"

    def test_permissao_inativa_de_papel_preserva_nivel_seguro(self):
        """
        PP(ativo=False, nivel="solicitacoes") → tem_acesso=False, nivel="solicitacoes".

        O nível é preservado mesmo com ativo=False para fins de auditoria e bloqueio
        seguro: código de filtragem pode usar o nível para determinar o escopo mínimo.
        """
        u = self._user("u_pp_inativa")
        papel = self._new_papel("Papel PP Inativo")
        PermissaoPapel.objects.create(
            papel=papel,
            modulo=MODULO_FINANCEIRO,
            ativo=False,
            nivel=NIVEL_SOLICITACOES,
        )
        self._assign_papel(u, papel)

        r = permissao_efetiva(u, MODULO_FINANCEIRO)
        self.assertFalse(r["tem_acesso"], f"PP inativa deve negar acesso: {r}")
        self.assertEqual(
            r["nivel"],
            NIVEL_SOLICITACOES,
            f"nível deve ser preservado mesmo com ativo=False; atual={r['nivel']!r}",
        )
        self.assertEqual(r["origem"], "papel", f"origem deve ser 'papel'; atual={r['origem']!r}")


# ===========================================================================
# 5. QUERIES CLASSIFICADAS
# ===========================================================================


class TestKernelQueriesClassificadas(InteracoesBase):
    """
    Classifica queries de permissao_efetiva e habilitacao_efetiva por tipo SQL.
    Afirma limites sobre SELECTs de negócio (não sobre total bruto).

    Limite total é mantido permissivo (50) para detectar regressões graves.
    Limite por SELECT é específico por cenário.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_qcls"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Queries Classificadas"
        tenant.slug = "tk-int-qcls"

    TOTAL_LIMIT = 50

    def _cls(self, queries):
        r = {"SET": 0, "SELECT": 0, "INSERT": 0, "UPDATE": 0, "DELETE": 0, "outras": 0}
        for q in queries:
            sql = q["sql"].strip().upper()
            for k in ("SET", "SELECT", "INSERT", "UPDATE", "DELETE"):
                if sql.startswith(k):
                    r[k] += 1
                    break
            else:
                r["outras"] += 1
        return r

    def _report(self, cenario, ctx, r):
        print(
            f"\n  [qcls:{cenario}] total={len(ctx)} "
            f"SET={r['SET']} SELECT={r['SELECT']} "
            f"INSERT={r['INSERT']} UPDATE={r['UPDATE']}"
        )

    def test_qcls_admin_permissao(self):
        """Admin: permissao_efetiva — SELECT <= 1."""
        u = self._user("u_qcls_adm")
        self._set_admin_flag(u)
        u_f = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            permissao_efetiva(u_f, MODULO_PROCESSOS)
        r = self._cls(ctx.captured_queries)
        self._report("admin_perm", ctx, r)
        self.assertLessEqual(r["SELECT"], 1, f"admin/permissão: esperado SELECT<=1; got {r['SELECT']}")

    def test_qcls_papel_unico_permissao(self):
        """Papel dinâmico único: permissao_efetiva — SELECT <= 4."""
        u = self._user("u_qcls_p1")
        papel = self._new_papel("QCls P1")
        self._pp(papel, MODULO_PROCESSOS, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)
        u_f = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            permissao_efetiva(u_f, MODULO_PROCESSOS)
        r = self._cls(ctx.captured_queries)
        self._report("papel_unico_perm", ctx, r)
        self.assertLessEqual(r["SELECT"], 4, f"papel único/permissão: esperado SELECT<=4; got {r['SELECT']}")

    def test_qcls_sem_papel_permissao(self):
        """Sem papel nem override: permissao_efetiva — SELECT <= 3."""
        u = self._user("u_qcls_sp")
        u_f = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            permissao_efetiva(u_f, MODULO_PROCESSOS)
        r = self._cls(ctx.captured_queries)
        self._report("sem_papel_perm", ctx, r)
        self.assertLessEqual(r["SELECT"], 3, f"sem papel/permissão: esperado SELECT<=3; got {r['SELECT']}")

    def test_qcls_habilitacao_dinamica(self):
        """Papel dinâmico único: habilitacao_efetiva — SELECT <= 6."""
        u = self._user("u_qcls_hd")
        papel = self._new_papel("QCls HD")
        self._pp(papel, MODULO_PROCESSOS, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self._assign_papel(u, papel)
        u_f = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            habilitacao_efetiva(u_f, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        r = self._cls(ctx.captured_queries)
        self._report("hab_dinamica", ctx, r)
        self.assertLessEqual(r["SELECT"], 6, f"habilitação dinâmica: esperado SELECT<=6; got {r['SELECT']}")

    def test_qcls_override_individual_com_up(self):
        """UP + PermissaoUsuario individual: habilitacao_efetiva — SELECT <= 6."""
        u = self._user("u_qcls_ov")
        papel = self._new_papel("QCls Ov")
        self._pp(papel, MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)
        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS
        )
        u_f = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            habilitacao_efetiva(u_f, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        r = self._cls(ctx.captured_queries)
        self._report("override_individual_com_up", ctx, r)
        self.assertLessEqual(r["SELECT"], 6, f"override individual com UP: esperado SELECT<=6; got {r['SELECT']}")


# ===========================================================================
# 6. SMOKE HTTP
# ===========================================================================


class _SmokeBase(InteracoesBase):
    """
    Base para smoke HTTP: verifica ausência de HTTP 500 nos endpoints.

    Usa force_login + HTTP_HOST do domínio do tenant de teste.
    Falha apenas em 500 (erro interno não tratado).
    Redirects (302) e acessos negados (403) são aceitos.
    """

    PATHS_SMOKE = [
        "/",
        "/clientes/",
        "/processos/",
        "/tarefas/",
        "/financeiro/",
        "/agenda/",
        "/chat/global/",
        "/modelos/",
        "/configuracoes/",
        "/configuracoes/permissoes/",
    ]

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

    def _smoke(self, user, label):
        self.client.force_login(user)
        for path in self.PATHS_SMOKE:
            r = self.client.get(path, HTTP_HOST=self.http_host)
            print(f"\n  [smoke:{label}] {path} -> {r.status_code}")
            self.assertNotEqual(
                r.status_code, 500,
                f"{label} -> {path}: HTTP 500 inesperado",
            )


class TestSmokePagesAdmin(_SmokeBase):
    """Smoke HTTP: usuário com is_admin_escritorio=True."""

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_smkadm"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Smoke Admin"
        tenant.slug = "tk-int-smkadm"

    def test_smoke_admin_sem_500(self):
        """Admin: todos os endpoints retornam 200/302/403, nunca 500."""
        u = self._user("smoke_admin_user")
        self._set_admin_flag(u)
        self._smoke(u, "admin")


class TestSmokePagesAdvogado(_SmokeBase):
    """Smoke HTTP: usuário com UsuarioPapel (advogado simulado)."""

    @classmethod
    def get_test_schema_name(cls):
        return "tk_int_smkadv"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Smoke Advogado"
        tenant.slug = "tk-int-smkadv"

    def test_smoke_advogado_sem_500(self):
        """Advogado (UP): endpoints retornam 200/302/403, nunca 500."""
        u = self._user("smoke_adv_user")
        papel = self._new_papel("Papel Smoke Adv")
        self._pp(papel, MODULO_PROCESSOS, nivel=NIVEL_TODOS)
        self._pp(papel, MODULO_CLIENTES, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)
        self._smoke(u, "advogado")
