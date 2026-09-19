"""
Fluxo "Criar modelo de Procuração": `modelos:novo?cliente=<pk>` (vindo da
tela Gerar procuração de Clientes) trava o tipo em Procuração e oferece
"Salvar modelo" e "Salvar e criar procuração para <cliente>"; sem o
parâmetro (ou com cliente inválido/fora do escopo) o formulário é o de
sempre.
"""

from unittest import mock

from apps.accounts.permissoes_constants import MODULO_CLIENTES, NIVEL_SOMENTE_SEUS
from apps.clientes.tests.test_gerar_procuracao import GerarProcuracaoBase
from apps.modelos.models import CategoriaModeloPeca, ModeloPeca

DADOS_MODELO = {
    "titulo": "Procuração ad judicia",
    "area_direito": "CÍVEL",
    "conteudo": "<p>Poderes gerais para o foro.</p>",
}


class CriarModeloProcuracaoBase(GerarProcuracaoBase):
    def setUp(self):
        super().setUp()
        self.user = self._user("dono_criar_modelo_procuracao")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)
        self.cliente = self._cliente(responsavel=self.user, nome_razao_social="Maria Souza")
        self.procuracao = CategoriaModeloPeca.objects.get(nome="Procuração")
        self.outra_categoria = CategoriaModeloPeca.objects.exclude(nome="Procuração").first()

    def _url(self, cliente=None):
        return "/modelos/novo/" + (f"?cliente={cliente.pk}" if cliente else "")

    def _get(self, cliente=None):
        return self.client.get(self._url(cliente), HTTP_HOST=self.http_host)

    def _post(self, cliente=None, *, categoria=None, criar_procuracao=False):
        dados = {**DADOS_MODELO, "categoria": (categoria or self.procuracao).pk}
        if criar_procuracao:
            dados["criar_procuracao"] = "1"
        return self.client.post(self._url(cliente), dados, HTTP_HOST=self.http_host)


class TestFormularioDoFluxo(CriarModeloProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criar_modelo_procuracao_form"

    def test_tela_gerar_procuracao_leva_o_cliente_no_botao(self):
        r = self.client.get(
            f"/clientes/{self.cliente.pk}/gerar-procuracao/", HTTP_HOST=self.http_host
        )
        self.assertContains(r, f"/modelos/novo/?cliente={self.cliente.pk}")

    def test_tipo_de_peca_vem_procuracao_e_travado(self):
        r = self._get(self.cliente)
        campo = r.context["form"].fields["categoria"]
        self.assertTrue(campo.disabled)
        self.assertEqual(r.context["form"]["categoria"].value(), self.procuracao.pk)
        self.assertContains(r, "disabled")

    def test_rodape_tem_os_dois_botoes_com_o_nome_do_cliente(self):
        r = self._get(self.cliente)
        self.assertContains(r, "Salvar modelo")
        self.assertContains(r, "Salvar e criar procuração para Maria Souza")
        self.assertContains(r, 'name="criar_procuracao"')

    def test_nome_longo_do_cliente_usa_a_regra_de_quebra(self):
        longo = self._cliente(
            responsavel=self.user, nome_razao_social="A" * 200, cpf_cnpj="529.982.247-25"
        )
        r = self._get(longo)
        self.assertContains(r, "texto-quebra")
        self.assertContains(r, "A" * 200)

    def test_sem_parametro_o_formulario_e_o_de_sempre(self):
        r = self._get()
        self.assertFalse(r.context["form"].fields["categoria"].disabled)
        self.assertNotContains(r, "criar_procuracao")
        self.assertNotContains(r, "Salvar e criar procuração")
        self.assertContains(r, "Criar modelo")

    def test_parametro_invalido_e_ignorado(self):
        for valor in ("abc", "", "99999", "-1"):
            r = self.client.get(f"/modelos/novo/?cliente={valor}", HTTP_HOST=self.http_host)
            self.assertEqual(r.status_code, 200, valor)
            self.assertIsNone(r.context["cliente_origem"], valor)
            self.assertFalse(r.context["form"].fields["categoria"].disabled, valor)

    def test_sem_categoria_procuracao_comportamento_normal(self):
        ModeloPeca.objects.filter(categoria=self.procuracao).delete()
        self.procuracao.delete()
        r = self._get(self.cliente)
        self.assertIsNone(r.context["cliente_origem"])
        self.assertFalse(r.context["form"].fields["categoria"].disabled)
        self.assertNotContains(r, "Salvar e criar procuração")


class TestBotoes(CriarModeloProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criar_modelo_procuracao_botoes"

    def test_salvar_modelo_vai_ao_detalhe_sem_gerar_procuracao(self):
        r = self._post(self.cliente)
        modelo = ModeloPeca.objects.get()
        self.assertRedirects(r, f"/modelos/{modelo.pk}/", fetch_redirect_response=False)
        self.assertEqual(modelo.categoria, self.procuracao)
        self.assertIsNone(modelo.cliente)

    def test_salvar_e_criar_gera_procuracao_vinculada_e_vai_aos_documentos(self):
        r = self._post(self.cliente, criar_procuracao=True)
        self.assertRedirects(
            r, f"/clientes/{self.cliente.pk}/?aba=documentos", fetch_redirect_response=False
        )
        modelo = ModeloPeca.objects.get(cliente__isnull=True)
        peca = ModeloPeca.objects.get(cliente=self.cliente)
        self.assertEqual(peca.categoria, self.procuracao)
        self.assertEqual(peca.criado_por, self.user)
        self.assertIn("Maria Souza", peca.conteudo)
        self.assertIn("Poderes gerais para o foro.", peca.conteudo)
        self.assertNotEqual(peca.pk, modelo.pk)

        pagina = self.client.get(r.url, HTTP_HOST=self.http_host)
        self.assertContains(pagina, "Procuração criada")
        self.assertContains(pagina, "Procurações geradas")
        self.assertContains(pagina, f"/modelos/{peca.pk}/")

    def test_procuracao_criada_fica_fora_da_lista_de_modelos_base(self):
        self._post(self.cliente, criar_procuracao=True)
        peca = ModeloPeca.objects.get(cliente=self.cliente)
        modelo = ModeloPeca.objects.get(cliente__isnull=True)
        outro = self._cliente(
            responsavel=self.user, nome_razao_social="Outro Cliente", cpf_cnpj="529.982.247-25"
        )
        r = self.client.get(f"/clientes/{outro.pk}/gerar-procuracao/", HTTP_HOST=self.http_host)
        self.assertEqual(list(r.context["modelos_procuracao"]), [modelo])
        self.assertNotIn(peca, list(r.context["modelos_procuracao"]))

    def test_falha_ao_gerar_nao_deixa_modelo_pela_metade(self):
        with mock.patch(
            "apps.modelos.views.gerar_peca_procuracao", side_effect=RuntimeError("falha")
        ):
            with self.assertRaises(RuntimeError):
                self._post(self.cliente, criar_procuracao=True)
        self.assertEqual(ModeloPeca.objects.count(), 0)


class TestTipoTravadoNoBackend(CriarModeloProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criar_modelo_procuracao_travado"

    def test_post_com_outra_categoria_e_forcado_para_procuracao(self):
        self._post(self.cliente, categoria=self.outra_categoria)
        self.assertEqual(ModeloPeca.objects.get().categoria, self.procuracao)

    def test_post_com_outra_categoria_tambem_no_segundo_botao(self):
        self._post(self.cliente, categoria=self.outra_categoria, criar_procuracao=True)
        self.assertEqual(
            set(ModeloPeca.objects.values_list("categoria__nome", flat=True)), {"Procuração"}
        )
        self.assertEqual(ModeloPeca.objects.count(), 2)

    def test_sem_cliente_a_categoria_postada_vale(self):
        self._post(categoria=self.outra_categoria)
        self.assertEqual(ModeloPeca.objects.get().categoria, self.outra_categoria)

    def test_segundo_botao_sem_cliente_valido_so_salva_o_modelo(self):
        r = self.client.post(
            "/modelos/novo/?cliente=99999",
            {**DADOS_MODELO, "categoria": self.procuracao.pk, "criar_procuracao": "1"},
            HTTP_HOST=self.http_host,
        )
        modelo = ModeloPeca.objects.get()
        self.assertRedirects(r, f"/modelos/{modelo.pk}/", fetch_redirect_response=False)


class TestAutorizacaoEEscopo(CriarModeloProcuracaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "criar_modelo_procuracao_escopo"

    def test_cliente_fora_do_escopo_e_ignorado_no_get_e_no_post(self):
        outro = self._user("outro_criar_modelo_procuracao")
        self._dar_permissoes_completas(outro, nivel_clientes=NIVEL_SOMENTE_SEUS)
        self.client.force_login(outro)
        r = self._get(self.cliente)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["cliente_origem"])
        self.assertNotContains(r, "Maria Souza")

        r = self._post(self.cliente, criar_procuracao=True)
        modelo = ModeloPeca.objects.get()
        self.assertRedirects(r, f"/modelos/{modelo.pk}/", fetch_redirect_response=False)
        self.assertFalse(ModeloPeca.objects.filter(cliente=self.cliente).exists())

    def test_sem_acesso_ao_modulo_clientes_o_cliente_e_ignorado(self):
        so_modelos = self._user("so_modelos_criar_modelo_procuracao")
        from apps.accounts.permissoes_constants import HAB_MODELOS_CRIAR, MODULO_MODELOS

        self._dar_modulo(so_modelos, MODULO_MODELOS, habilitacao=HAB_MODELOS_CRIAR)
        self.client.force_login(so_modelos)
        r = self._get(self.cliente)
        self.assertIsNone(r.context["cliente_origem"])
        r = self._post(self.cliente, criar_procuracao=True)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(ModeloPeca.objects.filter(cliente=self.cliente).exists())

    def test_sem_modelos_criar_e_negado(self):
        sem_criar = self._user("sem_criar_criar_modelo_procuracao")
        self._dar_modulo(sem_criar, MODULO_CLIENTES)
        self.client.force_login(sem_criar)
        self.assertEqual(self._get(self.cliente).status_code, 403)
        self.assertEqual(self._post(self.cliente, criar_procuracao=True).status_code, 403)
        self.assertEqual(ModeloPeca.objects.count(), 0)
