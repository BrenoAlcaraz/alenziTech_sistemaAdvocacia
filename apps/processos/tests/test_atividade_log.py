"""
Ações de escrita do módulo Processos geram LogAtividade —
specs/dashboard-painel-do-gestor.md (fase 1 do log: login + Processos).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.atividade.models import LogAtividade
from apps.clientes.models import Cliente
from apps.processos.models import MovimentacaoProcessual, Processo


FORM_BASE = {
    "area_direito": "CÍVEL",
    "fase": "conhecimento",
    "instancia": "1ª Instância",
    "gratuidade_justica_status": "nao_requerida",
}


class AtividadeLogProcessosBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi_processos_atividade_log"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.admin = User.objects.create_user("admin_log", password="testpass")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.client.force_login(self.admin)
        self.cliente = Cliente.objects.create(
            nome_razao_social="Cliente Log", tipo="PF", responsavel=self.admin, ativo=True
        )
        self.processo = Processo.objects.create(
            titulo="Processo Log", responsavel=self.admin, cliente=self.cliente
        )

    def _payload(self, titulo="Processo Log", **extra):
        # self.admin sempre usa ProcessoResponsavelForm (bypass de Admin em
        # _pode_atribuir_responsavel) — "responsavel" é obrigatório nesse
        # formulário, igual o campo pré-selecionado (initial) que o GET real
        # já mostra na tela.
        payload = {
            "titulo": titulo, "cliente": self.cliente.pk, "responsavel": self.admin.pk,
            **FORM_BASE,
        }
        payload.update(extra)
        return payload

    def _ultimo_log(self):
        return LogAtividade.objects.order_by("-criado_em", "-pk").first()


class TestLogCriarEditarArquivarReabrir(AtividadeLogProcessosBase):
    def test_criar_processo_gera_log(self):
        LogAtividade.objects.all().delete()
        resposta = self.client.post(
            "/processos/novo/", self._payload(titulo="Novo via form"), HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 302)
        log = self._ultimo_log()
        self.assertEqual(log.tipo, "processo_criado")
        self.assertIn("Novo via form", log.descricao)

    def test_editar_processo_gera_log(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._payload(titulo="Editado"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        log = self._ultimo_log()
        self.assertEqual(log.tipo, "processo_editado")
        self.assertEqual(log.processo_id, self.processo.pk)

    def test_arquivar_e_reabrir_geram_log(self):
        self.client.post(f"/processos/{self.processo.pk}/arquivar/", HTTP_HOST=self.http_host)
        self.assertEqual(self._ultimo_log().tipo, "processo_arquivado")

        self.client.post(f"/processos/{self.processo.pk}/reabrir/", HTTP_HOST=self.http_host)
        self.assertEqual(self._ultimo_log().tipo, "processo_reaberto")


class TestLogMovimentacaoParteDocumento(AtividadeLogProcessosBase):
    def test_adicionar_movimentacao_gera_log(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/movimentacoes/nova/",
            {"tipo": "andamento", "data": "2026-01-10T10:00", "descricao": "Contestação protocolada"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        log = self._ultimo_log()
        self.assertEqual(log.tipo, "processo_andamento_adicionado")
        self.assertEqual(log.processo_id, self.processo.pk)

    def test_adicionar_e_editar_parte_geram_log(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/partes/nova/",
            {"papel": "autor", "nome": "Fulano de Tal", "cpf_cnpj": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_parte_adicionada")

        parte = self.processo.partes.get()
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/partes/{parte.pk}/editar/",
            {"papel": "autor", "nome": "Fulano Editado", "cpf_cnpj": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_parte_editada")

    def test_adicionar_e_excluir_documento_geram_log(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        arquivo = SimpleUploadedFile("peticao.pdf", b"conteudo", content_type="application/pdf")
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/documentos/nova/",
            {"arquivo": arquivo, "tipo": "peticao", "descricao": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_documento_adicionado")

        documento = self.processo.documentos.get()
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/documentos/{documento.pk}/excluir/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_documento_excluido")


class TestLogIntegranteEApenso(AtividadeLogProcessosBase):
    def test_adicionar_e_remover_integrante_geram_log(self):
        outro = User.objects.create_user("integrante", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Integrante Elegivel")
        UsuarioPapel.objects.create(usuario=outro, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS
        )
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/adicionar/",
            {"usuario": outro.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_integrante_adicionado")

        resposta = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/{outro.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_integrante_removido")

    def test_adicionar_e_remover_apenso_geram_log(self):
        outro_processo = Processo.objects.create(
            titulo="Processo Apenso", responsavel=self.admin, cliente=self.cliente
        )
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/apensos/adicionar/",
            {"processo_apenso": outro_processo.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_apenso_adicionado")

        vinculo = self.processo.vinculos_apensos_como_menor.first() or self.processo.vinculos_apensos_como_maior.first()
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/apensos/{vinculo.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self._ultimo_log().tipo, "processo_apenso_removido")
