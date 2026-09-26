"""Representante da parte (sócio, pais, curador — não é parte) e
gratuidade de justiça por parte (só polo ativo, passivo e terceiro
interessado)."""

from apps.accounts.permissoes_constants import NIVEL_TODOS
from apps.processos.models import ParteProcesso, RepresentanteParte

from .test_escopo import ProcessosEscopoBase


class TestRepresentanteEGratuidade(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "processos_representante_gratuidade"

    def setUp(self):
        super().setUp()
        self.user = self._user("resp_representante")
        self._autorizar(self.user, NIVEL_TODOS)
        self.processo = self._processo(self.user, self._cliente(self.user), "Processo")
        self.parte = ParteProcesso.objects.create(processo=self.processo, papel="autor", nome="Empresa X")
        self.client.force_login(self.user)

    def _post(self, url, dados=None):
        return self.client.post(url, dados or {}, HTTP_HOST=self.http_host)

    def _url_representante(self, parte=None):
        parte = parte or self.parte
        return f"/processos/{parte.processo_id}/partes/{parte.pk}/representantes/novo/"

    def test_adiciona_varios_representantes_e_exibe_na_parte(self):
        self._post(self._url_representante(), {"qualificacao": "pai_mae", "nome": "Maria", "cpf": ""})
        self._post(self._url_representante(), {"qualificacao": "pai_mae", "nome": "João", "cpf": "1"})
        self.assertEqual(self.parte.representantes.count(), 2)
        conteudo = self.client.get(
            f"/processos/{self.processo.pk}/?aba=partes", HTTP_HOST=self.http_host
        ).content.decode()
        self.assertIn("Maria", conteudo)
        self.assertIn("Pai/Mãe", conteudo)
        # Representante não é parte: a contagem da aba continua 1.
        self.assertIn('Partes <span class="text-gray-500">(1)</span>', conteudo)

    def test_remove_representante(self):
        representante = RepresentanteParte.objects.create(parte=self.parte, qualificacao="curador", nome="C")
        self._post(f"/processos/{self.processo.pk}/representantes/{representante.pk}/remover/")
        self.assertFalse(RepresentanteParte.objects.exists())

    def test_fora_do_escopo_de_mutacao_nao_adiciona_nem_remove(self):
        estranho = self._user("estranho_representante")
        self._autorizar(estranho, NIVEL_TODOS)
        representante = RepresentanteParte.objects.create(parte=self.parte, qualificacao="curador", nome="C")
        self.client.force_login(estranho)
        self.assertEqual(self._post(self._url_representante(), {"qualificacao": "outro", "nome": "Z"}).status_code, 404)
        resposta = self._post(f"/processos/{self.processo.pk}/representantes/{representante.pk}/remover/")
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(RepresentanteParte.objects.count(), 1)

    def test_representante_de_parte_de_outro_processo_nao_e_alcancado(self):
        outro = self._processo(self.user, None, "Outro")
        parte_outro = ParteProcesso.objects.create(processo=outro, papel="reu", nome="Y")
        url = f"/processos/{self.processo.pk}/partes/{parte_outro.pk}/representantes/novo/"
        self.assertEqual(self._post(url, {"qualificacao": "outro", "nome": "Z"}).status_code, 404)

    def test_gratuidade_nos_polos_e_terceiro_interessado(self):
        for papel in ("autor", "reu", "terceiro_interessado"):
            with self.subTest(papel=papel):
                parte = ParteProcesso.objects.create(
                    processo=self.processo, papel=papel, nome=papel, gratuidade_justica=True
                )
                self.assertTrue(parte.gratuidade_justica)

    def test_gratuidade_descartada_nos_demais_papeis(self):
        self._post(
            f"/processos/{self.processo.pk}/partes/nova/",
            {"papel": "perito", "nome": "Perito", "gratuidade_justica": "on"},
        )
        self.assertFalse(ParteProcesso.objects.get(papel="perito").gratuidade_justica)

    def test_gratuidade_marcada_pelo_formulario_aparece_no_card(self):
        self._post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/editar/",
            {"papel": "autor", "nome": "Empresa X", "gratuidade_justica": "on"},
        )
        self.parte.refresh_from_db()
        self.assertTrue(self.parte.gratuidade_justica)
        conteudo = self.client.get(
            f"/processos/{self.processo.pk}/?aba=partes", HTTP_HOST=self.http_host
        ).content.decode()
        self.assertIn("data-parte-gratuidade", conteudo)
