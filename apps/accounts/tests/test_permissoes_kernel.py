"""
Suíte formal de testes do kernel de autorização.

Testa permissao_efetiva() e habilitacao_efetiva() contra o contrato definido.

Testes com FALHA_ESPERADA documentam o gap entre o kernel atual (pré-2.1C1B) e
o contrato aprovado em 2.1C0.1. Eles falharão agora e passarão após 2.1C1B.

Estrutura:
  TestKernelContrato      — invariantes do contrato (TODOS PASSAM agora)
  TestKernelGrupoLegado   — kernel atual com Groups (TODOS PASSAM agora)
  TestKernelFallbackGrupo — gate de fallback de Group via UsuarioPapel (FALHA ESPERADA)
  TestKernelPapelUnico    — resolução via papel FK / UsuarioPapel (FALHA ESPERADA)
  TestKernelMultiPapel    — agregação multi-papel (FALHA ESPERADA)
  TestKernelNiveis        — nível por módulo e tipo de conta (TODOS PASSAM agora)
  TestKernelQueries       — contagem de queries (limite superior)
"""

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    PerfilUsuario,
    PapelAcesso,
    UsuarioPapel,
    PermissaoPapel,
    HabilitacaoPapel,
    PermissaoUsuario,
    HabilitacaoUsuario,
)
from apps.accounts.permissoes import (
    permissao_efetiva,
    habilitacao_efetiva,
    tem_permissao_modulo,
    tem_habilitacao,
    tipo_conta_usuario,
)
from apps.accounts.permissoes_constants import (
    NIVEIS_POR_MODULO,
    TIPO_CONTA_ADMINISTRADOR,
    MODULO_PROCESSOS,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_TAREFAS,
    MODULO_MODELOS,
    MODULO_CHAT,
    MODULO_GERIR,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_EDITAR,
    HAB_CLIENTES_CRIAR,
    HAB_GERIR_CRIAR_USUARIO,
    NIVEL_TODOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_DADOS,
    NIVEL_SOLICITACOES,
)


# ---------------------------------------------------------------------------
# Base compartilhada
# ---------------------------------------------------------------------------

class KernelBase(TenantTestCase):
    """
    Base para todos os testes do kernel.
    Cada subclasse define schema e slug únicos.
    """

    FALHA_ESPERADA = "FALHA ESPERADA NO KERNEL ATUAL (pré-2.1C1B)"

    def assertFuturo(self, condicao, motivo=""):
        """
        Assert que documenta comportamento futuro (2.1C1B).
        Falha agora por design — passará após a implementação.
        """
        if not condicao:
            raise AssertionError(f"{self.FALHA_ESPERADA}: {motivo}")

    # ── fixtures ─────────────────────────────────────────────────────────────

    def _user(self, username, *, is_active=True, is_superuser=False):
        return User.objects.create_user(
            username=username,
            password="testpass",
            is_active=is_active,
            is_superuser=is_superuser,
        )

    def _set_admin_flag(self, user):
        # update() + limpeza de _state.fields_cache garante que usuario_admin_escritorio()
        # leia o valor atualizado. Django 5.x guarda reverse OneToOne em fields_cache.
        n = PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        if n != 1:
            raise AssertionError(f"_set_admin_flag: esperado 1 row atualizado, got {n}")
        user._state.fields_cache.pop("perfil", None)

    def _add_group(self, user, nome):
        grp = Group.objects.get(name=nome)
        user.groups.add(grp)

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        """Cria PermissaoPapel por papel FK (tipo_conta=None)."""
        return PermissaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=modulo,
            ativo=ativo,
            nivel=nivel,
        )

    def _hp(self, papel, modulo, item, *, ativo=True):
        """Cria HabilitacaoPapel por papel FK (tipo_conta=None)."""
        return HabilitacaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=modulo,
            item=item,
            ativo=ativo,
        )

    def _nivel_admin_para(self, modulo):
        """Retorna o nível máximo esperado para admin no módulo."""
        return NIVEIS_POR_MODULO.get(modulo, [""])[-1]

    def _perm_result_basico(self, r, *, tem_acesso, modulo, origem, tipo_conta=None):
        """Assert nas chaves principais de permissao_efetiva."""
        self.assertIn("tem_acesso", r)
        self.assertIn("modulo", r)
        self.assertIn("nivel", r)
        self.assertIn("origem", r)
        self.assertIn("tipo_conta", r)
        self.assertEqual(r["tem_acesso"], tem_acesso, f"tem_acesso errado: {r}")
        self.assertEqual(r["modulo"], modulo, f"modulo errado: {r}")
        self.assertEqual(r["origem"], origem, f"origem errada: {r}")
        if tipo_conta is not None:
            self.assertEqual(r["tipo_conta"], tipo_conta, f"tipo_conta errado: {r}")

    def _hab_result_basico(self, r, *, habilitado, modulo, item, origem):
        """Assert nas chaves principais de habilitacao_efetiva."""
        self.assertIn("habilitado", r)
        self.assertIn("modulo", r)
        self.assertIn("item", r)
        self.assertIn("origem", r)
        self.assertIn("tipo_conta", r)
        self.assertEqual(r["habilitado"], habilitado, f"habilitado errado: {r}")
        self.assertEqual(r["modulo"], modulo, f"modulo errado: {r}")
        self.assertEqual(r["item"], item, f"item errado: {r}")
        self.assertEqual(r["origem"], origem, f"origem errada: {r}")


# ===========================================================================
# 1. CONTRATO — invariantes fundamentais
# ===========================================================================

class TestKernelContrato(KernelBase):
    """
    Testa as invariantes do contrato.
    Todos devem PASSAR no kernel atual.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_contrato"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Contrato"
        tenant.slug = "tk-contrato"

    def test_retorno_dict_permissao_tem_chaves_esperadas(self):
        """permissao_efetiva sempre retorna dict com 5 chaves."""
        u = self._user("u_chaves")
        self._add_group(u, "limitado")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertIsInstance(r, dict)
        self.assertEqual(
            set(r.keys()),
            {"tem_acesso", "modulo", "nivel", "origem", "tipo_conta"},
        )

    def test_retorno_dict_habilitacao_tem_chaves_esperadas(self):
        """habilitacao_efetiva sempre retorna dict com 5 chaves."""
        u = self._user("u_hab_chaves")
        self._add_group(u, "limitado")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertIsInstance(r, dict)
        self.assertEqual(
            set(r.keys()),
            {"habilitado", "modulo", "item", "origem", "tipo_conta"},
        )

    def test_modulo_invalido_nega_sem_acesso(self):
        """Módulo não registrado em NIVEIS_POR_MODULO → nega sem DB."""
        u = self._user("u_mod_inv")
        self._add_group(u, "limitado")
        r = permissao_efetiva(u, "modulo_inexistente")
        self._perm_result_basico(r, tem_acesso=False, modulo="modulo_inexistente", origem="nenhuma")

    def test_item_invalido_habilitacao_nega(self):
        """Item que não pertence ao módulo → nega."""
        u = self._user("u_item_inv")
        self._add_group(u, "limitado")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, "item_inexistente")
        self._hab_result_basico(r, habilitado=False, modulo=MODULO_PROCESSOS, item="item_inexistente", origem="nenhuma")

    def test_modulo_sem_habilitacoes_nega_item(self):
        """Módulo sem itens (financeiro, chat) → nega habilitação de qualquer item."""
        u = self._user("u_fin_hab")
        self._add_group(u, "financeiro")
        # financeiro tem ITENS_POR_MODULO[MODULO_FINANCEIRO] = []
        r = habilitacao_efetiva(u, MODULO_FINANCEIRO, "item_qualquer")
        self._hab_result_basico(r, habilitado=False, modulo=MODULO_FINANCEIRO, item="item_qualquer", origem="nenhuma")

    def test_usuario_inativo_nega_permissao(self):
        """is_active=False → nega permissão."""
        u = self._user("u_inativo", is_active=False)
        self._add_group(u, "limitado")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="inativo")

    def test_usuario_inativo_nega_habilitacao(self):
        """is_active=False → nega habilitação."""
        u = self._user("u_inativo_h", is_active=False)
        self._add_group(u, "limitado")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self._hab_result_basico(r, habilitado=False, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_CRIAR, origem="inativo")

    def test_anonimo_nega_permissao(self):
        """AnonymousUser → nega permissão."""
        anon = AnonymousUser()
        r = permissao_efetiva(anon, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="nenhuma")

    def test_admin_acessa_todos_modulos(self):
        """Admin → acessa todos os módulos válidos, origem='admin'."""
        u = self._user("u_admin_all")
        self._set_admin_flag(u)
        for modulo in NIVEIS_POR_MODULO:
            r = permissao_efetiva(u, modulo)
            self.assertTrue(r["tem_acesso"], f"Admin deve acessar {modulo}")
            self.assertEqual(r["origem"], "admin", f"Origem errada para {modulo}")
            self.assertEqual(r["tipo_conta"], TIPO_CONTA_ADMINISTRADOR)

    def test_admin_habilita_todos_itens_validos(self):
        """Admin → todos os itens válidos habilitados, origem='admin'."""
        u = self._user("u_admin_hab")
        self._set_admin_flag(u)
        from apps.accounts.permissoes_constants import ITENS_POR_MODULO
        for modulo, itens in ITENS_POR_MODULO.items():
            for item in itens:
                r = habilitacao_efetiva(u, modulo, item)
                self.assertTrue(r["habilitado"], f"Admin deve habilitar {modulo}/{item}")
                self.assertEqual(r["origem"], "admin")

    def test_tem_permissao_modulo_delega_para_permissao_efetiva(self):
        """tem_permissao_modulo() retorna bool consistente com permissao_efetiva()."""
        u = self._user("u_wrap_perm")
        self._add_group(u, "limitado")
        resultado = permissao_efetiva(u, MODULO_PROCESSOS)["tem_acesso"]
        self.assertEqual(tem_permissao_modulo(u, MODULO_PROCESSOS), resultado)

    def test_tem_habilitacao_delega_para_habilitacao_efetiva(self):
        """tem_habilitacao() retorna bool consistente com habilitacao_efetiva()."""
        u = self._user("u_wrap_hab")
        self._add_group(u, "limitado")
        resultado = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)["habilitado"]
        self.assertEqual(tem_habilitacao(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR), resultado)


# ===========================================================================
# 2. GRUPO LEGADO — kernel atual com Groups
# ===========================================================================

class TestKernelGrupoLegado(KernelBase):
    """
    Testa o kernel atual usando Groups (tipo_conta).
    Todos devem PASSAR no kernel atual.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_grupo"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Grupo Legado"
        tenant.slug = "tk-grupo"

    def test_sem_grupo_nega_permissao(self):
        """Usuário sem Group técnico → nega (tipo_conta=None)."""
        u = self._user("u_sem_grp")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="nenhuma")

    def test_duplo_grupo_nega_permissao(self):
        """Usuário em Group limitado + financeiro → tipo_conta ambíguo → nega."""
        u = self._user("u_duplo_grp")
        self._add_group(u, "limitado")
        self._add_group(u, "financeiro")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="nenhuma")

    def test_grupo_limitado_processos_usa_seed(self):
        """Group=limitado → usa PermissaoPapel seed (tipo_conta=limitado, modulo=processos)."""
        u = self._user("u_lim_proc")
        self._add_group(u, "limitado")
        seed = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_PROCESSOS)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertEqual(r["tem_acesso"], seed.ativo)
        self.assertEqual(r["nivel"], seed.nivel)
        self.assertEqual(r["origem"], "grupo_legado")
        self.assertEqual(r["tipo_conta"], "limitado")

    def test_grupo_limitado_financeiro_modulo_inativo(self):
        """Group=limitado → financeiro seed é ativo=False → sem acesso."""
        u = self._user("u_lim_fin")
        self._add_group(u, "limitado")
        seed = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_FINANCEIRO)
        r = permissao_efetiva(u, MODULO_FINANCEIRO)
        self.assertEqual(r["tem_acesso"], seed.ativo)
        self.assertEqual(r["origem"], "grupo_legado")

    def test_grupo_financeiro_processos_usa_seed(self):
        """Group=financeiro → usa PermissaoPapel seed (tipo_conta=financeiro, modulo=processos)."""
        u = self._user("u_fin_proc")
        self._add_group(u, "financeiro")
        seed = PermissaoPapel.objects.get(tipo_conta="financeiro", modulo=MODULO_PROCESSOS)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertEqual(r["tem_acesso"], seed.ativo)
        self.assertEqual(r["nivel"], seed.nivel)
        self.assertEqual(r["origem"], "grupo_legado")
        self.assertEqual(r["tipo_conta"], "financeiro")

    def test_habilitacao_limitado_processos_criar_usa_seed(self):
        """Group=limitado → habilitacao usa HabilitacaoPapel seed."""
        u = self._user("u_lim_hab_proc")
        self._add_group(u, "limitado")
        seed_pp = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_PROCESSOS)
        seed_hp = HabilitacaoPapel.objects.get(
            tipo_conta="limitado", modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_CRIAR
        )
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        if not seed_pp.ativo:
            self.assertEqual(r["origem"], "permissao_desligada")
        else:
            self.assertEqual(r["habilitado"], seed_hp.ativo)
            self.assertEqual(r["origem"], "grupo_legado")
            self.assertEqual(r["tipo_conta"], "limitado")

    def test_habilitacao_nega_se_modulo_desligado(self):
        """Se permissão do módulo está desligada → habilitação retorna permissao_desligada."""
        u = self._user("u_mod_off")
        self._add_group(u, "limitado")
        seed_pp = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_FINANCEIRO)
        # financeiro está ativo=False para limitado (seed)
        if not seed_pp.ativo:
            r = habilitacao_efetiva(u, MODULO_FINANCEIRO, "financeiro_item_invalido")
            # item inválido → nega antes de verificar módulo
            self.assertEqual(r["origem"], "nenhuma")
        # Usar clientes com override individual desligado
        PermissaoUsuario.objects.create(usuario=u, modulo=MODULO_CLIENTES, ativo=False, nivel=NIVEL_TODOS)
        r = habilitacao_efetiva(u, MODULO_CLIENTES, HAB_CLIENTES_CRIAR)
        self.assertFalse(r["habilitado"])
        self.assertEqual(r["origem"], "permissao_desligada")

    def test_override_permissao_individual_sobre_papel_seed(self):
        """PermissaoUsuario individual prevalece sobre PermissaoPapel seed."""
        u = self._user("u_override_pp")
        self._add_group(u, "limitado")
        # Seed: processos está ativo para limitado. Vamos inverter via override.
        seed = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_MODELOS)
        override_ativo = not seed.ativo  # inverte para testar precedência
        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=override_ativo, nivel=NIVEL_TODOS
        )
        r = permissao_efetiva(u, MODULO_MODELOS)
        self.assertEqual(r["tem_acesso"], override_ativo)
        self.assertEqual(r["origem"], "individual")
        self.assertEqual(r["tipo_conta"], "limitado")

    def test_override_habilitacao_individual_sobre_papel_seed(self):
        """HabilitacaoUsuario individual prevalece sobre HabilitacaoPapel seed."""
        u = self._user("u_override_hp")
        self._add_group(u, "limitado")
        # Ativar módulo processos via override individual
        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        # Override de habilitação
        seed_hp = HabilitacaoPapel.objects.get(
            tipo_conta="limitado", modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_EDITAR
        )
        override_ativo = not seed_hp.ativo
        HabilitacaoUsuario.objects.create(
            usuario=u, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_EDITAR, ativo=override_ativo
        )
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR)
        self.assertEqual(r["habilitado"], override_ativo)
        self.assertEqual(r["origem"], "individual")


# ===========================================================================
# 3. FALLBACK DE GROUP — gate via UsuarioPapel
# ===========================================================================

class TestKernelFallbackGrupo(KernelBase):
    """
    Testa o gate de fallback de Group via UsuarioPapel.

    Regra futura (2.1C1B):
      - Se UsuarioPapel existe (qualquer estado) → NÃO usa Group fallback
      - Se UsuarioPapel não existe → usa Group fallback (comportamento atual)

    test_usuario_sem_up_usa_group_fallback PASSA agora (é o comportamento atual).
    test_usuario_com_up_nao_usa_group_fallback FALHA agora (kernel atual ignora UP).
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_fallback"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Fallback"
        tenant.slug = "tk-fallback"

    def test_usuario_sem_up_usa_group_fallback(self):
        """
        Sem UsuarioPapel → usa Group (fallback legado).
        PASSA no kernel atual (é o comportamento existente).
        """
        u = self._user("u_sem_up")
        self._add_group(u, "limitado")
        # Sem UsuarioPapel → deve usar Group=limitado → PermissaoPapel(tipo_conta=limitado)
        seed = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_PROCESSOS)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertEqual(r["tem_acesso"], seed.ativo)
        self.assertEqual(r["origem"], "grupo_legado")

    def test_usuario_com_up_inativo_nao_usa_group_fallback(self):
        """
        FALHA ESPERADA: UsuarioPapel(ativo=False) existe → NÃO deve usar Group fallback → deny.
        Kernel atual: ignora UP, usa Group=limitado → permite.

        Regra futura: qualquer UP (mesmo ativo=False) bloqueia o fallback de Group.
        """
        u = self._user("u_up_inativo")
        self._add_group(u, "limitado")
        papel = self._new_papel("Papel Fallback Inativo")
        self._assign_papel(u, papel, ativo=False)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        # Futuro: UP existe → não usa Group → papel FK sem PP → deny
        self.assertFuturo(
            r["tem_acesso"] is False,
            "UP(ativo=False) deve bloquear fallback de Group → deny",
        )

    def test_usuario_com_up_ativo_papel_inativo_nao_usa_group_fallback(self):
        """
        FALHA ESPERADA: UP(ativo=True) com PapelAcesso(ativo=False) → NÃO usa Group → deny.
        Kernel atual: ignora UP, usa Group=limitado → permite.
        """
        u = self._user("u_up_papel_off")
        self._add_group(u, "limitado")
        papel = self._new_papel("Papel Inativo", ativo=False)
        self._assign_papel(u, papel, ativo=True)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFuturo(
            r["tem_acesso"] is False,
            "PapelAcesso(ativo=False) deve resultar em deny (não fallback Group)",
        )


# ===========================================================================
# 4. PAPEL ÚNICO — resolução via papel FK / UsuarioPapel
# ===========================================================================

class TestKernelPapelUnico(KernelBase):
    """
    Testa resolução de permissão via UsuarioPapel → PapelAcesso → PermissaoPapel(papel FK).

    Todos com FALHA ESPERADA — kernel atual não consulta UsuarioPapel.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_papel"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Papel Único"
        tenant.slug = "tk-papel"

    def test_papel_unico_ativo_concede_permissao(self):
        """
        FALHA ESPERADA: UP(ativo=True) + PA(ativo=True) + PP(papel, processos, ativo=True)
        → deve conceder.
        Kernel atual: não consulta UP → nega (sem Group → tipo_conta=None).
        """
        u = self._user("u_papel_ativo")
        papel = self._new_papel("Papel Ativo A")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFuturo(
            r["tem_acesso"] is True,
            "papel ativo com PP → deve conceder",
        )

    def test_papel_sem_pp_nega(self):
        """
        FALHA ESPERADA: UP(ativo=True) + PA(ativo=True) sem PP para o módulo → nega.
        Kernel atual: não consulta UP → também nega (coincide, mas pela razão errada).

        Este teste passa no kernel atual pela razão errada — documentado para
        verificar que o futuro kernel nega pela razão correta (sem PP, não sem Group).
        """
        u = self._user("u_papel_sem_pp")
        papel = self._new_papel("Papel Sem PP")
        # Sem _pp(papel, ...) → papel não tem PermissaoPapel
        self._assign_papel(u, papel)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        # Ambos kernel atual e futuro negam, mas por razões diferentes.
        # No futuro: UP existe → não usa Group; PP por papel não existe → deny.
        # Verificar que o resultado é deny de qualquer forma.
        self.assertFalse(r["tem_acesso"])

    def test_up_inativo_nega_modulo(self):
        """
        FALHA ESPERADA: UP(ativo=False) → usuário não tem papel ativo → nega.
        Kernel atual: não consulta UP → nega pelo mesmo motivo (sem Group).
        """
        u = self._user("u_up_off")
        papel = self._new_papel("Papel UP Inativo")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel, ativo=False)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(r["tem_acesso"])

    def test_papel_ativo_concede_habilitacao(self):
        """
        FALHA ESPERADA: UP(ativo=True) + PA(ativo=True) + PP(papel, processos, ativo=True)
        + HP(papel, processos, processos_criar, ativo=True) → habilitado=True.
        Kernel atual: não consulta UP → nega permissão → permissao_desligada.
        """
        u = self._user("u_papel_hab")
        papel = self._new_papel("Papel Hab A")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR, ativo=True)
        self._assign_papel(u, papel)

        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFuturo(
            r["habilitado"] is True,
            "papel com PP+HP ativos → deve habilitar",
        )


# ===========================================================================
# 5. MULTI-PAPEL — agregação de permissões
# ===========================================================================

class TestKernelMultiPapel(KernelBase):
    """
    Testa agregação de permissões de múltiplos UsuarioPapel.

    Todos com FALHA ESPERADA — kernel atual não consulta UsuarioPapel.

    Regra futura: agrega pelo maior nível entre todos os papéis ativos.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_multi"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Multi Papel"
        tenant.slug = "tk-multi"

    def test_dois_papeis_ativos_agregam_permissoes(self):
        """
        FALHA ESPERADA: Papel A → processos; Papel B → clientes.
        Futuro: user tem acesso a processos E clientes.
        Kernel atual: sem Group → nega ambos.
        """
        u = self._user("u_dois_papeis")
        papel_a = self._new_papel("Multi A")
        papel_b = self._new_papel("Multi B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r_proc = permissao_efetiva(u, MODULO_PROCESSOS)
        r_clie = permissao_efetiva(u, MODULO_CLIENTES)
        self.assertFuturo(
            r_proc["tem_acesso"] is True,
            "Papel A deve conceder processos",
        )
        self.assertFuturo(
            r_clie["tem_acesso"] is True,
            "Papel B deve conceder clientes",
        )

    def test_dois_papeis_nivel_maximo_agregado(self):
        """
        FALHA ESPERADA: Papel A → processos/somente_seus; Papel B → processos/todos.
        Futuro: nível agregado = 'todos' (máximo).
        Kernel atual: sem Group → nega.
        """
        u = self._user("u_nivel_agr")
        papel_a = self._new_papel("Nivel Agr A")
        papel_b = self._new_papel("Nivel Agr B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_SOMENTE_SEUS)
        self._pp(papel_b, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFuturo(
            r["tem_acesso"] is True,
            "Ambos papéis concedem processos",
        )
        self.assertFuturo(
            r["nivel"] == NIVEL_TODOS,
            "Nível agregado deve ser o máximo (todos)",
        )

    def test_papel_inativo_nao_contribui_para_agregacao(self):
        """
        FALHA ESPERADA: Papel A ativo (processos), Papel B inativo (clientes).
        Futuro: processos=True, clientes=False (Papel B UP inativo não agrega).
        Kernel atual: nega ambos.
        """
        u = self._user("u_agr_inativo")
        papel_a = self._new_papel("Agr Ativo")
        papel_b = self._new_papel("Agr Inativo")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a, ativo=True)
        self._assign_papel(u, papel_b, ativo=False)

        r_proc = permissao_efetiva(u, MODULO_PROCESSOS)
        r_clie = permissao_efetiva(u, MODULO_CLIENTES)
        self.assertFuturo(
            r_proc["tem_acesso"] is True,
            "Papel A ativo deve conceder processos",
        )
        self.assertFuturo(
            r_clie["tem_acesso"] is False,
            "Papel B inativo não deve conceder clientes",
        )

    def test_dois_papeis_sem_pp_nega(self):
        """
        Dois papéis ativos, nenhum com PP para o módulo → nega.
        Deve PASSAR no kernel atual (sem Group → deny) e no futuro (sem PP → deny).
        """
        u = self._user("u_dois_sem_pp")
        papel_a = self._new_papel("Sem PP A")
        papel_b = self._new_papel("Sem PP B")
        # PP para módulos que o usuário NÃO vai consultar
        self._pp(papel_a, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_TAREFAS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(
            r["tem_acesso"],
            "Nenhum papel tem PP para processos → deve negar",
        )

    def test_dois_papeis_agregam_habilitacoes(self):
        """
        FALHA ESPERADA: Papel A → HP(processos_criar); Papel B → HP(processos_editar).
        Futuro: usuário obtém ambas as habilitações.
        Kernel atual: sem Group → nega processsos → habilitação nega antes.
        """
        u = self._user("u_agr_hab")
        papel_a = self._new_papel("Agr Hab A")
        papel_b = self._new_papel("Agr Hab B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._hp(papel_a, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR, ativo=True)
        self._hp(papel_b, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR, ativo=True)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r_criar = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        r_editar = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR)
        self.assertFuturo(
            r_criar["habilitado"] is True,
            "Papel A deve conceder processos_criar via habilitacao",
        )
        self.assertFuturo(
            r_editar["habilitado"] is True,
            "Papel B deve conceder processos_editar via habilitacao",
        )


# ===========================================================================
# 6. NÍVEIS — verificação por módulo e tipo de conta
# ===========================================================================

class TestKernelNiveis(KernelBase):
    """
    Testa que os níveis corretos são retornados por módulo e tipo de conta.
    Todos devem PASSAR no kernel atual.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_niveis"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Niveis"
        tenant.slug = "tk-niveis"

    def test_admin_nivel_maximo_processos(self):
        """Admin → nivel='todos' em processos (máximo da lista NIVEIS_POR_MODULO)."""
        u = self._user("u_adm_niv_proc")
        self._set_admin_flag(u)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertEqual(r["nivel"], self._nivel_admin_para(MODULO_PROCESSOS))
        self.assertEqual(r["nivel"], NIVEL_TODOS)

    def test_admin_nivel_maximo_financeiro(self):
        """Admin → nivel='dados' em financeiro (máximo da lista NIVEIS_POR_MODULO)."""
        u = self._user("u_adm_niv_fin")
        self._set_admin_flag(u)
        r = permissao_efetiva(u, MODULO_FINANCEIRO)
        self.assertEqual(r["nivel"], self._nivel_admin_para(MODULO_FINANCEIRO))
        self.assertEqual(r["nivel"], NIVEL_DADOS)

    def test_grupo_limitado_processos_nivel_somente_seus(self):
        """Group=limitado → processos seed deve retornar nivel correto do seed."""
        u = self._user("u_lim_niv_proc")
        self._add_group(u, "limitado")
        seed = PermissaoPapel.objects.get(tipo_conta="limitado", modulo=MODULO_PROCESSOS)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertEqual(r["nivel"], seed.nivel)

    def test_grupo_financeiro_financeiro_nivel_dados(self):
        """Group=financeiro → financeiro seed (ativo=True) → nivel=dados."""
        u = self._user("u_fin_niv_fin")
        self._add_group(u, "financeiro")
        seed = PermissaoPapel.objects.get(tipo_conta="financeiro", modulo=MODULO_FINANCEIRO)
        r = permissao_efetiva(u, MODULO_FINANCEIRO)
        if seed.ativo:
            self.assertEqual(r["nivel"], seed.nivel)
        else:
            self.assertFalse(r["tem_acesso"])

    def test_nivel_vazio_em_modulo_sem_nivel(self):
        """Módulos sem nível (chat, gerir) → nivel='' para admin."""
        u = self._user("u_adm_chat")
        self._set_admin_flag(u)
        r = permissao_efetiva(u, MODULO_CHAT)
        self.assertEqual(r["nivel"], "")


# ===========================================================================
# 7. QUERIES — caracterização de contagem de acesso ao banco
# ===========================================================================

class TestKernelQueries(KernelBase):
    """
    Mede o número de queries de permissao_efetiva e habilitacao_efetiva.

    Os limites superiores refletem o kernel ATUAL (pré-2.1C1B).
    Após 2.1C1B, os limites podem ser reduzidos conforme a implementação.

    Não usa assertFuturo — estes testes documentam o estado atual.
    Se exceder o limite, indica regressão de performance.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_queries"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Queries"
        tenant.slug = "tk-queries"

    # Limites superiores permissivos para o kernel atual
    # (perfil pode ou não estar em cache dependendo do estado do objeto)
    QUERY_LIMIT_PERM = 15
    QUERY_LIMIT_HAB = 20

    def test_permissao_efetiva_admin_queries(self):
        """Admin: permissao_efetiva usa queries abaixo do limite."""
        u = self._user("u_q_admin")
        self._set_admin_flag(u)
        # Fresh user — perfil não está em cache
        u_fresh = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            permissao_efetiva(u_fresh, MODULO_PROCESSOS)
        n = len(ctx)
        self.assertLessEqual(
            n,
            self.QUERY_LIMIT_PERM,
            f"permissao_efetiva(admin) usou {n} queries (limite={self.QUERY_LIMIT_PERM})",
        )

    def test_permissao_efetiva_limitado_queries(self):
        """Limitado: permissao_efetiva usa queries abaixo do limite."""
        u = self._user("u_q_lim")
        self._add_group(u, "limitado")
        u_fresh = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            permissao_efetiva(u_fresh, MODULO_PROCESSOS)
        n = len(ctx)
        self.assertLessEqual(
            n,
            self.QUERY_LIMIT_PERM,
            f"permissao_efetiva(limitado) usou {n} queries (limite={self.QUERY_LIMIT_PERM})",
        )

    def test_habilitacao_efetiva_admin_queries(self):
        """Admin: habilitacao_efetiva usa queries abaixo do limite."""
        u = self._user("u_q_adm_h")
        self._set_admin_flag(u)
        u_fresh = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            habilitacao_efetiva(u_fresh, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        n = len(ctx)
        self.assertLessEqual(
            n,
            self.QUERY_LIMIT_HAB,
            f"habilitacao_efetiva(admin) usou {n} queries (limite={self.QUERY_LIMIT_HAB})",
        )

    def test_habilitacao_efetiva_limitado_queries(self):
        """Limitado: habilitacao_efetiva usa queries abaixo do limite."""
        u = self._user("u_q_lim_h")
        self._add_group(u, "limitado")
        u_fresh = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx:
            habilitacao_efetiva(u_fresh, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        n = len(ctx)
        self.assertLessEqual(
            n,
            self.QUERY_LIMIT_HAB,
            f"habilitacao_efetiva(limitado) usou {n} queries (limite={self.QUERY_LIMIT_HAB})",
        )

    def test_permissao_efetiva_queries_reportado(self):
        """
        Reporta a contagem real de queries para documentação.
        Este teste nunca falha — apenas imprime os valores medidos.
        """
        u = self._user("u_q_rep")
        self._add_group(u, "limitado")
        u_fresh = User.objects.get(pk=u.pk)
        with CaptureQueriesContext(connection) as ctx_perm:
            permissao_efetiva(u_fresh, MODULO_PROCESSOS)
        n_perm = len(ctx_perm)

        with CaptureQueriesContext(connection) as ctx_hab:
            habilitacao_efetiva(u_fresh, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        n_hab = len(ctx_hab)

        # Imprime para ser visível no output do test runner com -v 2
        print(
            f"\n  [queries] permissao_efetiva(limitado, processos)={n_perm}; "
            f"habilitacao_efetiva(limitado, processos, processos_criar)={n_hab}"
        )
        # Não falha — apenas documenta
        self.assertTrue(True)
