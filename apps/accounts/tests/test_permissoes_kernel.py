"""
Suíte formal de testes do kernel de autorização.

Testa permissao_efetiva() e habilitacao_efetiva() contra o contrato: o
Administrador do escritório tem tudo; os demais usuários só têm o que vem
dos papéis de acesso (PapelAcesso) e dos overrides individuais. Não existe
mais "Tipo de conta" nem fallback por Group (PDR-0030).

Estrutura:
  TestKernelContrato       — invariantes do contrato
  TestKernelSemPapel       — usuário sem papel e o papel Limitado de fábrica
  TestKernelOverrides      — override individual sobre o papel
  TestKernelPapelUnico     — resolução via UsuarioPapel → PapelAcesso
  TestKernelMultiPapel     — agregação multi-papel
  TestKernelNiveis         — nível por módulo
  TestKernelQueries        — contagem de queries (limite superior)
"""

from django.contrib.auth.models import AnonymousUser, User
from django.db import connection
from django.test.utils import CaptureQueriesContext
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
)
from apps.accounts.permissoes_constants import (
    ITENS_POR_MODULO,
    NIVEIS_POR_MODULO,
    MODULO_PROCESSOS,
    MODULO_CLIENTES,
    MODULO_FINANCEIRO,
    MODULO_MODELOS,
    MODULO_CHAT,
    HAB_PROCESSOS_CRIAR,
    HAB_PROCESSOS_EDITAR,
    HAB_CLIENTES_CRIAR,
    NIVEL_TODOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_DADOS_TODOS,
)


# ---------------------------------------------------------------------------
# Base compartilhada
# ---------------------------------------------------------------------------

class KernelBase(TenantTestCase):
    """
    Base para todos os testes do kernel.
    Cada subclasse define schema e slug únicos.
    """

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

    def _new_papel(self, nome, *, ativo=True):
        return PapelAcesso.objects.create(nome=nome, ativo=ativo)

    def _assign_papel(self, user, papel, *, ativo=True):
        return UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=ativo)

    def _pp(self, papel, modulo, *, ativo=True, nivel=NIVEL_TODOS):
        return PermissaoPapel.objects.create(
            papel=papel,
            modulo=modulo,
            ativo=ativo,
            nivel=nivel,
        )

    def _hp(self, papel, modulo, item, *, ativo=True):
        return HabilitacaoPapel.objects.create(
            papel=papel,
            modulo=modulo,
            item=item,
            ativo=ativo,
        )

    def _nivel_admin_para(self, modulo):
        """Retorna o nível máximo esperado para admin no módulo."""
        return NIVEIS_POR_MODULO.get(modulo, [""])[-1]

    def _perm_result_basico(self, r, *, tem_acesso, modulo, origem):
        """Assert nas chaves principais de permissao_efetiva."""
        self.assertEqual(r["tem_acesso"], tem_acesso, f"tem_acesso errado: {r}")
        self.assertEqual(r["modulo"], modulo, f"modulo errado: {r}")
        self.assertEqual(r["origem"], origem, f"origem errada: {r}")

    def _hab_result_basico(self, r, *, habilitado, modulo, item, origem):
        """Assert nas chaves principais de habilitacao_efetiva."""
        self.assertEqual(r["habilitado"], habilitado, f"habilitado errado: {r}")
        self.assertEqual(r["modulo"], modulo, f"modulo errado: {r}")
        self.assertEqual(r["item"], item, f"item errado: {r}")
        self.assertEqual(r["origem"], origem, f"origem errada: {r}")


# ===========================================================================
# 1. CONTRATO — invariantes fundamentais
# ===========================================================================

class TestKernelContrato(KernelBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tk_contrato"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Contrato"
        tenant.slug = "tk-contrato"

    def test_retorno_dict_permissao_tem_chaves_esperadas(self):
        """permissao_efetiva sempre retorna dict com 4 chaves (sem tipo_conta)."""
        u = self._user("u_chaves")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertIsInstance(r, dict)
        self.assertEqual(set(r.keys()), {"tem_acesso", "modulo", "nivel", "origem"})

    def test_retorno_dict_habilitacao_tem_chaves_esperadas(self):
        """habilitacao_efetiva sempre retorna dict com 4 chaves (sem tipo_conta)."""
        u = self._user("u_hab_chaves")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertIsInstance(r, dict)
        self.assertEqual(set(r.keys()), {"habilitado", "modulo", "item", "origem"})

    def test_modulo_invalido_nega_sem_acesso(self):
        """Módulo não registrado em NIVEIS_POR_MODULO → nega sem DB."""
        u = self._user("u_mod_inv")
        r = permissao_efetiva(u, "modulo_inexistente")
        self._perm_result_basico(r, tem_acesso=False, modulo="modulo_inexistente", origem="nenhuma")

    def test_item_invalido_habilitacao_nega(self):
        """Item que não pertence ao módulo → nega."""
        u = self._user("u_item_inv")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, "item_inexistente")
        self._hab_result_basico(r, habilitado=False, modulo=MODULO_PROCESSOS, item="item_inexistente", origem="nenhuma")

    def test_modulo_sem_habilitacoes_nega_item(self):
        """Módulo sem itens (chat) → nega habilitação de qualquer item."""
        u = self._user("u_chat_hab")
        r = habilitacao_efetiva(u, MODULO_CHAT, "item_qualquer")
        self._hab_result_basico(r, habilitado=False, modulo=MODULO_CHAT, item="item_qualquer", origem="nenhuma")

    def test_usuario_inativo_nega_permissao(self):
        """is_active=False → nega permissão."""
        u = self._user("u_inativo", is_active=False)
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="inativo")

    def test_usuario_inativo_nega_habilitacao(self):
        """is_active=False → nega habilitação."""
        u = self._user("u_inativo_h", is_active=False)
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

    def test_admin_habilita_todos_itens_validos(self):
        """Admin → todos os itens válidos habilitados, origem='admin'."""
        u = self._user("u_admin_hab")
        self._set_admin_flag(u)
        for modulo, itens in ITENS_POR_MODULO.items():
            for item in itens:
                r = habilitacao_efetiva(u, modulo, item)
                self.assertTrue(r["habilitado"], f"Admin deve habilitar {modulo}/{item}")
                self.assertEqual(r["origem"], "admin")

    def test_tem_permissao_modulo_delega_para_permissao_efetiva(self):
        """tem_permissao_modulo() retorna bool consistente com permissao_efetiva()."""
        u = self._user("u_wrap_perm")
        resultado = permissao_efetiva(u, MODULO_PROCESSOS)["tem_acesso"]
        self.assertEqual(tem_permissao_modulo(u, MODULO_PROCESSOS), resultado)

    def test_tem_habilitacao_delega_para_habilitacao_efetiva(self):
        """tem_habilitacao() retorna bool consistente com habilitacao_efetiva()."""
        u = self._user("u_wrap_hab")
        resultado = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)["habilitado"]
        self.assertEqual(tem_habilitacao(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR), resultado)


# ===========================================================================
# 2. SEM PAPEL E PAPEL LIMITADO DE FÁBRICA
# ===========================================================================

class TestKernelSemPapel(KernelBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tk_sem_papel"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Sem Papel"
        tenant.slug = "tk-sem-papel"

    def test_usuario_sem_papel_nega_permissao(self):
        u = self._user("u_sem_papel")
        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="nenhuma")

    def test_usuario_sem_papel_nega_habilitacao(self):
        u = self._user("u_sem_papel_h")
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFalse(r["habilitado"])

    def test_grupo_legado_nao_concede_nada(self):
        """Group 'limitado'/'financeiro' (legado) não é mais fonte de autorização."""
        from django.contrib.auth.models import Group

        u = self._user("u_grupo_legado")
        u.groups.add(Group.objects.get_or_create(name="financeiro")[0])
        for modulo in NIVEIS_POR_MODULO:
            self.assertFalse(tem_permissao_modulo(u, modulo), modulo)

    def test_papel_limitado_de_fabrica_nega_todos_os_modulos_e_itens(self):
        u = self._user("u_limitado_fabrica")
        self._assign_papel(u, PapelAcesso.objects.get(codigo_preset="limitado"))
        for modulo in NIVEIS_POR_MODULO:
            self.assertFalse(tem_permissao_modulo(u, modulo), modulo)
        for modulo, itens in ITENS_POR_MODULO.items():
            for item in itens:
                self.assertFalse(tem_habilitacao(u, modulo, item), f"{modulo}/{item}")

    def test_papel_limitado_editado_passa_a_conceder(self):
        u = self._user("u_limitado_editado")
        limitado = PapelAcesso.objects.get(codigo_preset="limitado")
        self._assign_papel(u, limitado)
        self._pp(limitado, MODULO_CLIENTES, ativo=True, nivel=NIVEL_SOMENTE_SEUS)
        self._hp(limitado, MODULO_CLIENTES, HAB_CLIENTES_CRIAR, ativo=True)
        self.assertTrue(tem_permissao_modulo(u, MODULO_CLIENTES))
        self.assertTrue(tem_habilitacao(u, MODULO_CLIENTES, HAB_CLIENTES_CRIAR))


# ===========================================================================
# 3. OVERRIDES INDIVIDUAIS
# ===========================================================================

class TestKernelOverrides(KernelBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tk_overrides"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Overrides"
        tenant.slug = "tk-overrides"

    def test_habilitacao_nega_se_modulo_desligado_por_override(self):
        u = self._user("u_mod_off")
        papel = self._new_papel("Papel Clientes")
        self._pp(papel, MODULO_CLIENTES, ativo=True)
        self._hp(papel, MODULO_CLIENTES, HAB_CLIENTES_CRIAR, ativo=True)
        self._assign_papel(u, papel)
        PermissaoUsuario.objects.create(usuario=u, modulo=MODULO_CLIENTES, ativo=False, nivel=NIVEL_TODOS)
        r = habilitacao_efetiva(u, MODULO_CLIENTES, HAB_CLIENTES_CRIAR)
        self.assertFalse(r["habilitado"])
        self.assertEqual(r["origem"], "permissao_desligada")

    def test_override_permissao_individual_prevalece_sobre_papel(self):
        u = self._user("u_override_pp")
        papel = self._new_papel("Papel Modelos")
        self._pp(papel, MODULO_MODELOS, ativo=True)
        self._assign_papel(u, papel)
        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=False, nivel=NIVEL_TODOS
        )
        r = permissao_efetiva(u, MODULO_MODELOS)
        self.assertFalse(r["tem_acesso"])
        self.assertEqual(r["origem"], "individual")

    def test_override_concede_a_usuario_sem_papel(self):
        u = self._user("u_override_sem_papel")
        PermissaoUsuario.objects.create(
            usuario=u, modulo=MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS
        )
        r = permissao_efetiva(u, MODULO_MODELOS)
        self.assertTrue(r["tem_acesso"])
        self.assertEqual(r["origem"], "individual")

    def test_override_habilitacao_individual_prevalece_sobre_papel(self):
        u = self._user("u_override_hp")
        papel = self._new_papel("Papel Processos")
        self._pp(papel, MODULO_PROCESSOS, ativo=True)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR, ativo=True)
        self._assign_papel(u, papel)
        HabilitacaoUsuario.objects.create(
            usuario=u, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_EDITAR, ativo=False
        )
        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR)
        self.assertFalse(r["habilitado"])
        self.assertEqual(r["origem"], "individual")


# ===========================================================================
# 4. PAPEL ÚNICO — resolução via papel FK / UsuarioPapel
# ===========================================================================

class TestKernelPapelUnico(KernelBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tk_papel"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Papel Único"
        tenant.slug = "tk-papel"

    def test_papel_unico_ativo_concede_permissao(self):
        u = self._user("u_papel_ativo")
        papel = self._new_papel("Papel Ativo A")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=True, modulo=MODULO_PROCESSOS, origem="papel")
        self.assertEqual(r["nivel"], NIVEL_TODOS)

    def test_papel_sem_pp_nega(self):
        u = self._user("u_papel_sem_pp")
        papel = self._new_papel("Papel Sem PP")
        self._assign_papel(u, papel)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self._perm_result_basico(r, tem_acesso=False, modulo=MODULO_PROCESSOS, origem="papel")

    def test_up_inativo_nega_modulo(self):
        u = self._user("u_up_off")
        papel = self._new_papel("Papel UP Inativo")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel, ativo=False)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(r["tem_acesso"])

    def test_papel_inativo_nega_modulo(self):
        u = self._user("u_papel_off")
        papel = self._new_papel("Papel Inativo", ativo=False)
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel, ativo=True)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(r["tem_acesso"])

    def test_papel_ativo_concede_habilitacao(self):
        u = self._user("u_papel_hab")
        papel = self._new_papel("Papel Hab A")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR, ativo=True)
        self._assign_papel(u, papel)

        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self._hab_result_basico(
            r, habilitado=True, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_CRIAR, origem="papel"
        )

    def test_habilitacao_desligada_no_papel_nega(self):
        u = self._user("u_papel_hab_off")
        papel = self._new_papel("Papel Hab Off")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR, ativo=False)
        self._assign_papel(u, papel)

        r = habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertFalse(r["habilitado"])


# ===========================================================================
# 5. MULTI-PAPEL — agregação de permissões
# ===========================================================================

class TestKernelMultiPapel(KernelBase):
    """Agrega pelo maior nível entre todos os papéis ativos."""

    @classmethod
    def get_test_schema_name(cls):
        return "tk_multi"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Multi Papel"
        tenant.slug = "tk-multi"

    def test_dois_papeis_ativos_agregam_permissoes(self):
        u = self._user("u_dois_papeis")
        papel_a = self._new_papel("Multi A")
        papel_b = self._new_papel("Multi B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        self.assertTrue(permissao_efetiva(u, MODULO_PROCESSOS)["tem_acesso"])
        self.assertTrue(permissao_efetiva(u, MODULO_CLIENTES)["tem_acesso"])

    def test_dois_papeis_nivel_maximo_agregado(self):
        u = self._user("u_nivel_agr")
        papel_a = self._new_papel("Nivel Agr A")
        papel_b = self._new_papel("Nivel Agr B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_SOMENTE_SEUS)
        self._pp(papel_b, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertTrue(r["tem_acesso"])
        self.assertEqual(r["nivel"], NIVEL_TODOS)

    def test_papel_inativo_nao_contribui_para_agregacao(self):
        u = self._user("u_agr_inativo")
        papel_a = self._new_papel("Agr Ativo")
        papel_b = self._new_papel("Agr Inativo")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a, ativo=True)
        self._assign_papel(u, papel_b, ativo=False)

        self.assertTrue(permissao_efetiva(u, MODULO_PROCESSOS)["tem_acesso"])
        self.assertFalse(permissao_efetiva(u, MODULO_CLIENTES)["tem_acesso"])

    def test_dois_papeis_sem_pp_nega(self):
        u = self._user("u_dois_sem_pp")
        papel_a = self._new_papel("Sem PP A")
        papel_b = self._new_papel("Sem PP B")
        self._pp(papel_a, MODULO_CLIENTES, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_MODELOS, ativo=True, nivel=NIVEL_TODOS)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        r = permissao_efetiva(u, MODULO_PROCESSOS)
        self.assertFalse(r["tem_acesso"], "Nenhum papel tem PP para processos → deve negar")

    def test_dois_papeis_agregam_habilitacoes(self):
        u = self._user("u_agr_hab")
        papel_a = self._new_papel("Agr Hab A")
        papel_b = self._new_papel("Agr Hab B")
        self._pp(papel_a, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._pp(papel_b, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._hp(papel_a, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR, ativo=True)
        self._hp(papel_b, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR, ativo=True)
        self._assign_papel(u, papel_a)
        self._assign_papel(u, papel_b)

        self.assertTrue(habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)["habilitado"])
        self.assertTrue(habilitacao_efetiva(u, MODULO_PROCESSOS, HAB_PROCESSOS_EDITAR)["habilitado"])


# ===========================================================================
# 6. NÍVEIS — verificação por módulo
# ===========================================================================

class TestKernelNiveis(KernelBase):
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
        """Admin → nivel='dados_todos' em financeiro (máximo da lista NIVEIS_POR_MODULO)."""
        u = self._user("u_adm_niv_fin")
        self._set_admin_flag(u)
        r = permissao_efetiva(u, MODULO_FINANCEIRO)
        self.assertEqual(r["nivel"], self._nivel_admin_para(MODULO_FINANCEIRO))
        self.assertEqual(r["nivel"], NIVEL_DADOS_TODOS)

    def test_papel_retorna_o_nivel_configurado(self):
        u = self._user("u_papel_niv")
        papel = self._new_papel("Papel Nivel")
        self._pp(papel, MODULO_PROCESSOS, ativo=True, nivel=NIVEL_SOMENTE_SEUS)
        self._assign_papel(u, papel)
        self.assertEqual(permissao_efetiva(u, MODULO_PROCESSOS)["nivel"], NIVEL_SOMENTE_SEUS)

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
    Se exceder o limite, indica regressão de performance.
    """

    @classmethod
    def get_test_schema_name(cls):
        return "tk_queries"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Kernel Queries"
        tenant.slug = "tk-queries"

    # Limites superiores permissivos
    # (perfil pode ou não estar em cache dependendo do estado do objeto)
    QUERY_LIMIT_PERM = 15
    QUERY_LIMIT_HAB = 20

    def _usuario_com_papel(self, username):
        u = self._user(username)
        papel = self._new_papel(f"Papel {username}")
        self._pp(papel, MODULO_PROCESSOS)
        self._hp(papel, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self._assign_papel(u, papel)
        return User.objects.get(pk=u.pk)

    def _queries(self, funcao, *args):
        with CaptureQueriesContext(connection) as ctx:
            funcao(*args)
        return len(ctx)

    def test_permissao_efetiva_admin_queries(self):
        u = self._user("u_q_admin")
        self._set_admin_flag(u)
        u_fresh = User.objects.get(pk=u.pk)
        n = self._queries(permissao_efetiva, u_fresh, MODULO_PROCESSOS)
        self.assertLessEqual(n, self.QUERY_LIMIT_PERM, f"permissao_efetiva(admin) usou {n} queries")

    def test_permissao_efetiva_com_papel_queries(self):
        u_fresh = self._usuario_com_papel("u_q_papel")
        n = self._queries(permissao_efetiva, u_fresh, MODULO_PROCESSOS)
        self.assertLessEqual(n, self.QUERY_LIMIT_PERM, f"permissao_efetiva(papel) usou {n} queries")

    def test_habilitacao_efetiva_admin_queries(self):
        u = self._user("u_q_adm_h")
        self._set_admin_flag(u)
        u_fresh = User.objects.get(pk=u.pk)
        n = self._queries(habilitacao_efetiva, u_fresh, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertLessEqual(n, self.QUERY_LIMIT_HAB, f"habilitacao_efetiva(admin) usou {n} queries")

    def test_habilitacao_efetiva_com_papel_queries(self):
        u_fresh = self._usuario_com_papel("u_q_papel_h")
        n = self._queries(habilitacao_efetiva, u_fresh, MODULO_PROCESSOS, HAB_PROCESSOS_CRIAR)
        self.assertLessEqual(n, self.QUERY_LIMIT_HAB, f"habilitacao_efetiva(papel) usou {n} queries")
