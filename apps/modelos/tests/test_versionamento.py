"""
Testes de versionamento de ModeloPeca: snapshot ao editar, reversão para
versão anterior e remoção do histórico junto com o modelo excluído.

Autorização de `reverter` é idêntica à de `editar` (dono OU
modelos_editar_alheio — PDR-0018); reaproveita as fixtures de
apps/modelos/tests/test_autorizacao.py.
"""

from apps.accounts.permissoes_constants import HAB_MODELOS_EDITAR_ALHEIO, MODULO_MODELOS
from apps.modelos.models import ModeloPeca, VersaoModeloPeca
from apps.modelos.tests.test_autorizacao import ModelosAutorizacaoBase
from apps.notificacoes.models import Notificacao


class TestModelosEdicaoGeraVersao(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_versao_editar"

    def setUp(self):
        super().setUp()
        self.user = self._user("editor_versao")
        papel = self._new_papel("Papel Editor Versao")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self.client.force_login(self.user)
        self.modelo = self._modelo(
            criado_por=self.user,
            titulo="Título original",
            conteudo="Conteúdo original.",
        )

    def test_editar_cria_snapshot_da_versao_anterior(self):
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(),
            HTTP_HOST=self.http_host,
        )
        versao = VersaoModeloPeca.objects.get(modelo=self.modelo)
        self.assertEqual(versao.titulo, "Título original")
        self.assertEqual(versao.conteudo, "Conteúdo original.")
        self.assertEqual(versao.editado_por, self.user)

    def test_formulario_invalido_nao_cria_versao(self):
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(titulo=""),
            HTTP_HOST=self.http_host,
        )
        self.assertFalse(VersaoModeloPeca.objects.exists())

    def test_excluir_modelo_remove_historico(self):
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(),
            HTTP_HOST=self.http_host,
        )
        self.assertTrue(VersaoModeloPeca.objects.filter(modelo=self.modelo).exists())
        self.client.post(f"/modelos/{self.modelo.pk}/excluir/", HTTP_HOST=self.http_host)
        self.assertFalse(VersaoModeloPeca.objects.filter(modelo_id=self.modelo.pk).exists())


class TestModelosReverterProprio(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_reverter_proprio"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_reverte")
        papel = self._new_papel("Papel Dono Reverte")
        self._assign_papel(self.user, papel)
        self._pp(papel, MODULO_MODELOS)
        self.client.force_login(self.user)
        self.modelo = self._modelo(
            criado_por=self.user,
            titulo="Título original",
            conteudo="Conteúdo original.",
        )
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(),
            HTTP_HOST=self.http_host,
        )
        self.modelo.refresh_from_db()
        self.versao = VersaoModeloPeca.objects.get(modelo=self.modelo)

    def test_reverter_aplica_versao_antiga_e_gera_novo_historico(self):
        r = self.client.post(
            f"/modelos/{self.modelo.pk}/reverter/{self.versao.pk}/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.titulo, "Título original")
        self.assertEqual(self.modelo.conteudo, "Conteúdo original.")
        # snapshot da versão editada (pré-reversão) + a original: 2 entradas.
        self.assertEqual(VersaoModeloPeca.objects.filter(modelo=self.modelo).count(), 2)
        self.assertFalse(Notificacao.objects.exists())


class TestModelosReverterAlheioNegado(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_reverter_alheio_negado"

    def setUp(self):
        super().setUp()
        self.autor = self._user("autor_reversao")
        self.outro = self._user("outro_reversao")
        papel_autor = self._new_papel("Papel Autor Reverter Negado")
        self._assign_papel(self.autor, papel_autor)
        self._pp(papel_autor, MODULO_MODELOS)
        papel = self._new_papel("Papel Reverter Negado")
        self._assign_papel(self.outro, papel)
        self._pp(papel, MODULO_MODELOS)
        # Sem modelos_editar_alheio.
        self.modelo = self._modelo(criado_por=self.autor)
        self.client.force_login(self.autor)
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(),
            HTTP_HOST=self.http_host,
        )
        self.versao = VersaoModeloPeca.objects.get(modelo=self.modelo)
        self.client.force_login(self.outro)

    def test_reverter_negado(self):
        r = self.client.post(
            f"/modelos/{self.modelo.pk}/reverter/{self.versao.pk}/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.titulo, "Modelo Editado")


class TestModelosReverterAlheioConcedidoNotifica(ModelosAutorizacaoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_modelos_reverter_alheio_ok"

    def setUp(self):
        super().setUp()
        self.autor = self._user("autor_reversao_2")
        self.revertedor = self._user("revertedor_alheio")
        papel_autor = self._new_papel("Papel Autor Reverter Alheio")
        self._assign_papel(self.autor, papel_autor)
        self._pp(papel_autor, MODULO_MODELOS)
        papel = self._new_papel("Papel Reverter Alheio")
        self._assign_papel(self.revertedor, papel)
        self._pp(papel, MODULO_MODELOS)
        self._hp(papel, MODULO_MODELOS, HAB_MODELOS_EDITAR_ALHEIO)
        self.modelo = self._modelo(
            criado_por=self.autor, titulo="Título original", conteudo="Conteúdo original."
        )
        self.client.force_login(self.autor)
        self.client.post(
            f"/modelos/{self.modelo.pk}/editar/",
            self._payload_edicao(),
            HTTP_HOST=self.http_host,
        )
        self.versao = VersaoModeloPeca.objects.get(modelo=self.modelo)
        self.client.force_login(self.revertedor)

    def test_reverter_ok_e_notifica_autor(self):
        r = self.client.post(
            f"/modelos/{self.modelo.pk}/reverter/{self.versao.pk}/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.modelo.refresh_from_db()
        self.assertEqual(self.modelo.titulo, "Título original")
        notificacao = Notificacao.objects.get()
        self.assertEqual(notificacao.destinatario_id, self.autor.id)
