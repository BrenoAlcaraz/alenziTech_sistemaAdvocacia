"""
Rótulo "Categoria" renomeado para "Tipo de Peça" em toda a interface —
o catálogo por trás (`CategoriaModeloPeca`, campo `categoria`) não muda de
estrutura, só o texto exibido ao usuário (spec: peças repetitivas, filtros
e exportação, "Listagem").

Reaproveita as fixtures de apps/modelos/tests/test_autorizacao.py.
"""

from apps.accounts.permissoes_constants import (
    HAB_MODELOS_CRIAR,
    HAB_MODELOS_GERIR_CATEGORIAS,
    MODULO_MODELOS,
)
from apps.modelos.forms import CategoriaModeloPecaForm, ImportarModeloPecaForm, ModeloPecaForm
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase


class TestRotulosDeFormularioRenomeados(ModelosAutorizacaoBase):
    """Os rótulos de campo não dependem de renderização de template —
    testados direto no form, que é a fonte única usada por form.html,
    importar.html e categoria_editar.html."""

    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_rotulo_form"

    def test_modelo_peca_form_usa_tipo_de_peca(self):
        form = ModeloPecaForm()
        self.assertEqual(form.fields["categoria"].label, "Tipo de peça")

    def test_importar_form_usa_tipo_de_peca(self):
        form = ImportarModeloPecaForm()
        self.assertEqual(form.fields["categoria"].label, "Tipo de peça")

    def test_categoria_form_usa_nome_do_tipo_de_peca(self):
        form = CategoriaModeloPecaForm()
        self.assertEqual(form.fields["nome"].label, "Nome do tipo de peça")


class TestPaginasRenomeadasNaInterface(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_rotulo_paginas"

    def setUp(self):
        super().setUp()
        self.user = self._user("rotulo_tipo_peca")
        papel = self._new_papel("Papel Rotulo Tipo Peca")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_CRIAR)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_GERIR_CATEGORIAS)
        self.client.force_login(self.user)

    def test_lista_filtro_mostra_tipo_de_peca(self):
        r = self.client.get("/modelos/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Todos os tipos de peça")
        self.assertNotContains(r, "Todas as categorias")

    def test_pagina_categorias_renomeada(self):
        r = self.client.get("/modelos/categorias/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Tipos de peça")
        self.assertContains(r, "Novo tipo de peça")

    def test_detalhe_mostra_tipo_de_peca(self):
        modelo = self._modelo(criado_por=self.user)
        r = self.client.get(f"/modelos/{modelo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Tipo de peça:")
