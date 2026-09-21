"""
Processos em comum na aba "Clientes relacionados" da ficha do cliente:
escopo de leitura de Processos, módulo Processos desabilitado, limite de 3
com "+N" e as duas origens da relação (processo compartilhado e polo em
comum por CPF/CNPJ).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.models import ParteProcesso, Processo

DOC_A = "111.444.777-35"
DOC_B = "529.982.247-25"


class RelacionadosProcessosBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"
        self.user = User.objects.create_user(username="resp_rel_proc", password="x")
        self.outro = User.objects.create_user(username="outro_rel_proc", password="x")
        self.client.force_login(self.user)

    def _dar_modulo(self, modulo, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel {modulo}", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=modulo, ativo=True, nivel=nivel
        )

    def _cliente(self, nome, **kw):
        return Cliente.objects.create(nome_razao_social=nome, responsavel=self.user, **kw)

    def _processo(self, titulo, *, responsavel=None, **kw):
        return Processo.objects.create(
            titulo=titulo, responsavel=responsavel or self.user, **kw
        )

    def _aba_relacionados(self, cliente):
        return self.client.get(
            f"/clientes/{cliente.pk}/?aba=relacionados", HTTP_HOST=self.http_host
        )

    def _link_processo(self, processo):
        return f'href="/processos/{processo.pk}/"'


class TestProcessoCompartilhado(RelacionadosProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_rel_proc_compart"

    def setUp(self):
        super().setUp()
        self._dar_modulo(MODULO_CLIENTES)
        self.a, self.b = self._cliente("CLIENTE A"), self._cliente("CLIENTE B")

    def test_com_modulo_mostra_processo_em_comum_com_numero_e_status(self):
        self._dar_modulo(MODULO_PROCESSOS)
        p = self._processo("Proc", numero="0001234-56.2024.8.26.0100", status="suspenso")
        p.clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, self._link_processo(p))
        self.assertContains(r, "0001234-56.2024.8.26.0100 · Suspenso")

    def test_sem_modulo_processos_nao_mostra_processos_mas_lista_o_cliente(self):
        p = self._processo("Proc", numero="0001234-56.2024.8.26.0100")
        p.clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, "CLIENTE B")
        self.assertNotContains(r, self._link_processo(p))
        self.assertNotContains(r, "0001234-56.2024.8.26.0100")

    def test_somente_seus_esconde_processo_de_outro_responsavel_e_mantem_cliente(self):
        self._dar_modulo(MODULO_PROCESSOS, nivel=NIVEL_SOMENTE_SEUS)
        alheio = self._processo("Alheio", responsavel=self.outro, numero="9999999-99.2024.8.26.0100")
        proprio = self._processo("Proprio", numero="1111111-11.2024.8.26.0100")
        alheio.clientes.add(self.a, self.b)
        proprio.clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, "CLIENTE B")
        self.assertContains(r, self._link_processo(proprio))
        self.assertNotContains(r, self._link_processo(alheio))
        self.assertNotContains(r, "9999999-99.2024.8.26.0100")

    def test_somente_seus_com_unico_processo_alheio_mantem_cliente_sem_processo(self):
        self._dar_modulo(MODULO_PROCESSOS, nivel=NIVEL_SOMENTE_SEUS)
        alheio = self._processo("Alheio", responsavel=self.outro, numero="9999999-99.2024.8.26.0100")
        alheio.clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, "CLIENTE B")
        self.assertNotContains(r, self._link_processo(alheio))

    def test_mais_de_tres_mostra_tres_e_contador(self):
        self._dar_modulo(MODULO_PROCESSOS)
        processos = [self._processo(f"P{i}", numero=f"000000{i}-00.2024.8.26.0100") for i in range(5)]
        for p in processos:
            p.clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        links = sum(self._link_processo(p) in r.content.decode() for p in processos)
        self.assertEqual(links, 3)
        self.assertContains(r, "+2")

    def test_ate_tres_nao_mostra_contador(self):
        self._dar_modulo(MODULO_PROCESSOS)
        for i in range(3):
            self._processo(f"P{i}").clientes.add(self.a, self.b)
        r = self._aba_relacionados(self.a)
        self.assertNotContains(r, "+0")
        self.assertNotContains(r, "+1")


class TestPoloEmComum(RelacionadosProcessosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "clientes_rel_proc_polo"

    def setUp(self):
        super().setUp()
        self._dar_modulo(MODULO_CLIENTES)
        self._dar_modulo(MODULO_PROCESSOS)
        self.a = self._cliente("CLIENTE A", cpf_cnpj=DOC_A)
        self.b = self._cliente("CLIENTE B", cpf_cnpj=DOC_B)

    def _parte(self, processo, papel, nome, cpf_cnpj):
        return ParteProcesso.objects.create(
            processo=processo, papel=papel, nome=nome, cpf_cnpj=cpf_cnpj
        )

    def test_partes_no_mesmo_polo_mostram_o_processo(self):
        p = self._processo("Polo", numero="2222222-22.2024.8.26.0100")
        self._parte(p, "autor", "A", DOC_A)
        self._parte(p, "requerente", "B", DOC_B)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, "CLIENTE B")
        self.assertContains(r, self._link_processo(p))

    def test_partes_em_polos_opostos_nao_relacionam(self):
        p = self._processo("Polo")
        self._parte(p, "autor", "A", DOC_A)
        self._parte(p, "reu", "B", DOC_B)
        r = self._aba_relacionados(self.a)
        self.assertNotContains(r, "CLIENTE B")
        self.assertNotContains(r, self._link_processo(p))

    def test_polo_em_comum_respeita_escopo_de_processos(self):
        PermissaoPapel.objects.filter(modulo=MODULO_PROCESSOS).update(nivel=NIVEL_SOMENTE_SEUS)
        alheio = self._processo("Alheio", responsavel=self.outro)
        self._parte(alheio, "autor", "A", DOC_A)
        self._parte(alheio, "requerente", "B", DOC_B)
        r = self._aba_relacionados(self.a)
        self.assertContains(r, "CLIENTE B")
        self.assertNotContains(r, self._link_processo(alheio))

    def test_processo_compartilhado_e_polo_no_mesmo_processo_nao_duplicam(self):
        p = self._processo("Ambos", numero="3333333-33.2024.8.26.0100")
        p.clientes.add(self.a, self.b)
        self._parte(p, "autor", "A", DOC_A)
        self._parte(p, "autor", "B", DOC_B)
        r = self._aba_relacionados(self.a)
        self.assertEqual(r.content.decode().count(self._link_processo(p)), 1)
