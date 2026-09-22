"""
Procuração gerada vinculada ao cliente.

Cobre: a peça gerada grava o cliente e aparece em "Procurações geradas"
na aba Documentos; peça vinculada nunca é oferecida como modelo-base
(nem por POST direto); a seção respeita escopo de leitura do cliente e o
acesso ao módulo Modelos (filtro no backend); exclusão definitiva do
cliente leva a peça junto.
"""


from apps.accounts.permissoes_constants import (
    HAB_CLIENTES_CRIAR,
    MODULO_CLIENTES,
    NIVEL_SOMENTE_SEUS,
)
from apps.clientes.models import Cliente
from apps.clientes.tests.test_gerar_procuracao import GerarProcuracaoBase
from apps.modelos.models import ModeloPeca


class TestProcuracaoVinculadaAoCliente(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "procuracao_vinculada_cliente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_procuracao_vinculada")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.joao = self._cliente(responsavel=self.user, nome_razao_social="João da Silva")
        self.pedro = self._cliente(
            responsavel=self.user, nome_razao_social="Pedro Souza", cpf_cnpj="529.982.247-25"
        )
        self.modelo_base = self._modelo_procuracao(criado_por=self.user)

    def _gerar(self, cliente, modelo_base=None):
        return self.client.post(
            f"/clientes/{cliente.pk}/gerar-procuracao/",
            {"modelo_base": (modelo_base or self.modelo_base).pk},
            HTTP_HOST=self.http_host,
        )

    def _documentos(self, cliente):
        return self.client.get(f"/clientes/{cliente.pk}/?aba=documentos", HTTP_HOST=self.http_host)

    def test_peca_gerada_grava_o_cliente(self):
        self._gerar(self.joao)
        peca = ModeloPeca.objects.exclude(pk=self.modelo_base.pk).get()
        self.assertEqual(peca.cliente, self.joao)

    def test_modelo_cadastrado_normalmente_fica_sem_cliente(self):
        self.assertIsNone(self.modelo_base.cliente)

    def test_aparece_em_procuracoes_geradas_do_cliente_e_nao_no_contador(self):
        self._gerar(self.joao)
        peca = ModeloPeca.objects.get(cliente=self.joao)
        r = self._documentos(self.joao)
        self.assertContains(r, "Procurações geradas")
        self.assertContains(r, peca.titulo)
        self.assertContains(r, f"/modelos/{peca.pk}/")
        self.assertContains(r, "Documentos <span")
        self.assertEqual(r.context["documentos_total"], 0)

    def test_nao_mostra_conteudo_da_peca(self):
        self._gerar(self.joao)
        r = self._documentos(self.joao)
        self.assertNotContains(r, "Texto padrão de poderes.")

    def test_procuracao_do_joao_nao_aparece_na_ficha_do_pedro(self):
        self._gerar(self.joao)
        peca = ModeloPeca.objects.get(cliente=self.joao)
        r = self._documentos(self.pedro)
        self.assertNotContains(r, f"/modelos/{peca.pk}/")
        self.assertContains(r, "Nenhuma procuração gerada para este cliente.")

    def test_procuracao_do_joao_nao_e_modelo_base_para_o_pedro(self):
        self._gerar(self.joao)
        peca_joao = ModeloPeca.objects.get(cliente=self.joao)
        r = self.client.get(f"/clientes/{self.pedro.pk}/gerar-procuracao/", HTTP_HOST=self.http_host)
        self.assertEqual(list(r.context["modelos_procuracao"]), [self.modelo_base])
        self.assertNotContains(r, peca_joao.titulo)

    def test_post_direto_com_peca_vinculada_como_base_e_404(self):
        self._gerar(self.joao)
        peca_joao = ModeloPeca.objects.get(cliente=self.joao)
        antes = ModeloPeca.objects.count()
        r = self._gerar(self.pedro, modelo_base=peca_joao)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(ModeloPeca.objects.count(), antes)

    def test_so_pecas_vinculadas_orienta_a_criar_modelo(self):
        self._gerar(self.joao)
        self.modelo_base.delete()
        r = self.client.get(f"/clientes/{self.pedro.pk}/gerar-procuracao/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Criar modelo de Procuração")

    def test_procuracao_antiga_sem_cliente_continua_como_modelo_base(self):
        antiga = self._modelo_procuracao(criado_por=self.user, titulo="Procuração antiga")
        r = self.client.get(f"/clientes/{self.joao.pk}/gerar-procuracao/", HTTP_HOST=self.http_host)
        self.assertIn(antiga, list(r.context["modelos_procuracao"]))

    def test_excluir_cliente_leva_as_pecas_geradas_e_nunca_as_torna_modelo_base(self):
        self._gerar(self.joao)
        peca = ModeloPeca.objects.get(cliente=self.joao)
        self.joao.delete()
        self.assertFalse(ModeloPeca.objects.filter(pk=peca.pk).exists())
        self.assertTrue(ModeloPeca.objects.filter(pk=self.modelo_base.pk).exists())

    def test_cliente_desativado_mantem_a_peca_vinculada(self):
        self._gerar(self.joao)
        Cliente.objects.filter(pk=self.joao.pk).update(ativo=False)
        peca = ModeloPeca.objects.get(cliente=self.joao)
        r = self.client.get(f"/clientes/{self.pedro.pk}/gerar-procuracao/", HTTP_HOST=self.http_host)
        self.assertNotIn(peca, list(r.context["modelos_procuracao"]))


class TestEscopoEAcessoAModelos(GerarProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "procuracao_vinculada_escopo"

    def setUp(self):
        super().setUp()
        self.dono = self._user("dono_cliente_escopo_procuracao")
        self._dar_permissoes_completas(self.dono)
        self.cliente = self._cliente(responsavel=self.dono)
        self.modelo_base = self._modelo_procuracao(criado_por=self.dono)
        self.client.force_login(self.dono)
        self.client.post(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/",
            {"modelo_base": self.modelo_base.pk},
            HTTP_HOST=self.http_host,
        )
        self.peca = ModeloPeca.objects.get(cliente=self.cliente)

    def test_cliente_fora_do_escopo_nao_expoe_procuracoes(self):
        outro = self._user("outro_escopo_procuracao")
        self._dar_permissoes_completas(outro, nivel_clientes=NIVEL_SOMENTE_SEUS)
        self.client.force_login(outro)
        r = self.client.get(f"/clientes/{self.cliente.pk}/?aba=documentos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)
        self.assertNotContains(r, self.peca.titulo, status_code=404)

    def test_usuario_sem_acesso_a_modelos_nao_ve_secao_nem_link(self):
        sem_modelos = self._user("sem_modelos_procuracao")
        self._dar_modulo(sem_modelos, MODULO_CLIENTES, habilitacao=HAB_CLIENTES_CRIAR)
        self.client.force_login(sem_modelos)
        r = self.client.get(f"/clientes/{self.cliente.pk}/?aba=documentos", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Procurações geradas")
        self.assertNotContains(r, f"/modelos/{self.peca.pk}/")
        self.assertNotContains(r, self.peca.titulo)
        self.assertEqual(r.context["procuracoes_geradas"], [])

    def test_usuario_com_acesso_a_modelos_ve_secao_e_link(self):
        r = self.client.get(f"/clientes/{self.cliente.pk}/?aba=documentos", HTTP_HOST=self.http_host)
        self.assertContains(r, "Procurações geradas")
        self.assertContains(r, f"/modelos/{self.peca.pk}/")
