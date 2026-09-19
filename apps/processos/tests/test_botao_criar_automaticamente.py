"""
Botão "Criar automaticamente" em Novo processo (specs/processo-criacao-
automatica-ia.md): ponto de entrada reservado para a IA jurídica (PDR-0008),
inerte e desabilitado; só aparece na criação.
"""

from apps.accounts.permissoes_constants import HAB_PROCESSOS_EDITAR, MODULO_PROCESSOS
from apps.processos.models import Processo

from .test_criacao_cruzada import CriacaoCruzadaBase

MARCADOR_BOTAO = "data-criar-automaticamente"


class TestBotaoCriarAutomaticamente(CriacaoCruzadaBase):
    @classmethod
    def get_test_schema_name(cls):
        return "botao_criar_automaticamente"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_botao_criar_automaticamente")
        self._dar_permissoes_completas(self.user)
        self.client.force_login(self.user)

    def test_novo_exibe_botao_desabilitado_em_breve(self):
        r = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertContains(r, MARCADOR_BOTAO)
        self.assertContains(r, "Criar automaticamente")
        self.assertRegex(r.content.decode(), r"<button[^>]*\bdisabled\b[^>]*data-criar-automaticamente")
        self.assertContains(r, "em breve")

    def test_editar_nao_exibe_botao(self):
        editor = self._user("editor_botao_criar_automaticamente")
        self._dar_modulo(editor, MODULO_PROCESSOS, habilitacao=HAB_PROCESSOS_EDITAR)
        self.client.force_login(editor)
        processo = Processo.objects.create(titulo="Processo editar", responsavel=editor)
        r = self.client.get(f"/processos/{processo.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, MARCADOR_BOTAO)

    def test_criacao_cruzada_por_cliente_continua_funcionando(self):
        cliente = self._cliente(responsavel=self.user)
        r = self.client.get(f"/processos/novo/?cliente={cliente.pk}", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'value="{cliente.pk}" selected')
