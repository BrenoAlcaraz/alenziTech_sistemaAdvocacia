"""Lista de Processos em tabela: busca, ordenação, paginação e trilha
de contexto (specs/ui-05-shell-e-listas.md)."""

from apps.accounts.permissoes_constants import NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.processos.models import ParteProcesso, Processo

from .test_escopo import ProcessosEscopoBase


class TestListaProcessosTabela(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "ui05_lista_processos"

    def setUp(self):
        super().setUp()
        self.user = self._user("lista_somente_seus")
        self.outro = self._user("lista_alheio")
        self._autorizar(self.user, NIVEL_SOMENTE_SEUS)
        self.cliente = self._cliente(self.user, "Maria Aparecida")

    def _em_massa(self, responsavel, quantidade, *, inicio, **campos):
        # bulk_create pula o save(): o código interno vai explícito.
        Processo.objects.bulk_create([
            Processo(
                titulo=f"Processo {inicio + i:04d}",
                numero=f"{inicio + i:07d}-00.2024.8.26.0100",
                numero_interno=90000 + inicio + i,
                criado_por=responsavel,
                **campos,
            )
            for i in range(quantidade)
        ])

    def _get(self, query=""):
        return self.client.get(f"/processos/{query}", HTTP_HOST=self.http_host)

    def test_300_processos_paginam_em_50_mantendo_filtros_e_ordem(self):
        admin = self._admin()
        self._em_massa(admin, 300, inicio=1, area_direito="TRABALHISTA")
        self._em_massa(admin, 5, inicio=500, area_direito="CÍVEL")
        self.client.force_login(admin)

        resposta = self._get("?materia=TRABALHISTA&ordem=numero")
        pagina = resposta.context["processos"]
        self.assertEqual(len(pagina), 50)
        self.assertEqual(pagina.paginator.count, 300)
        self.assertEqual(pagina[0].numero, "0000001-00.2024.8.26.0100")
        self.assertContains(resposta, "?materia=TRABALHISTA&amp;ordem=numero&amp;pagina=2")

        segunda = self._get("?materia=TRABALHISTA&ordem=numero&pagina=2").context["processos"]
        self.assertEqual(segunda.number, 2)
        self.assertEqual(segunda[0].numero, "0000051-00.2024.8.26.0100")

        decrescente = self._get("?materia=TRABALHISTA&ordem=-numero").context["processos"]
        self.assertEqual(decrescente[0].numero, "0000300-00.2024.8.26.0100")

        # Ordem desconhecida cai na padrão, sem erro.
        self.assertEqual(self._get("?ordem=titulo;drop").status_code, 200)

    def test_busca_por_cnj_parcial_com_ou_sem_pontuacao_cliente_e_parte(self):
        processo = self._processo(self.user, self.cliente, "Ação de cobrança")
        processo.numero = "0001234-56.2024.8.26.0100"
        processo.save()
        ParteProcesso.objects.create(processo=processo, nome="Construtora Horizonte", papel="reu")
        self._processo(self.user, None, "Outro processo")
        self.client.force_login(self.user)

        for termo in ("1234-56.2024", "000123456", "aparecida", "horizonte"):
            with self.subTest(termo=termo):
                encontrados = list(self._get(f"?busca={termo}").context["processos"])
                self.assertEqual(encontrados, [processo])

    def test_somente_seus_nao_ve_alheios_na_busca_contagem_nem_paginacao(self):
        self._em_massa(self.user, 60, inicio=1)
        self._em_massa(self.outro, 60, inicio=1001)
        self.client.force_login(self.user)

        primeira = self._get("?busca=2024.8.26")
        pagina = primeira.context["processos"]
        self.assertEqual(pagina.paginator.count, 60)
        self.assertContains(primeira, "de 60 processos")
        segunda = self._get("?busca=2024.8.26&pagina=2").context["processos"]
        self.assertEqual(len(segunda), 10)
        vistos = {p.criado_por_id for p in list(pagina) + list(segunda)}
        self.assertEqual(vistos, {self.user.pk})

        # Página além do fim cai na última, ainda só com os próprios.
        alem = self._get("?busca=2024.8.26&pagina=99").context["processos"]
        self.assertEqual(alem.number, 2)
        self.assertNotContains(self._get("?busca=0001001"), "0001001-00")

    def test_escopo_todos_nao_amplia_para_quem_so_ve_os_seus(self):
        self.client.force_login(self.user)
        self.assertEqual(self._get(f"?escopo={NIVEL_TODOS}&pagina=2").status_code, 403)

    def test_tela_secundaria_mostra_trilha_de_contexto(self):
        processo = self._processo(self.user, self.cliente, "Ação de cobrança")
        processo.numero = "0001234-56.2024.8.26.0100"
        processo.save()
        self.client.force_login(self.user)

        detalhe = self.client.get(f"/processos/{processo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(detalhe, 'aria-label="Trilha"')
        self.assertContains(detalhe, '<a href="/processos/">Processos</a>', html=True)
        self.assertContains(detalhe, "0001234-56.2024.8.26.0100</span>")

        self.assertNotContains(self._get(), 'aria-label="Trilha"')
