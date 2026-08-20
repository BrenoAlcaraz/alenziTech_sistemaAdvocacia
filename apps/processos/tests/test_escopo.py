from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.clientes.models import Cliente
from apps.processos.forms import (
    MovimentacaoProcessualForm,
    ParteProcessoForm,
    ProcessoForm,
)
from apps.processos.models import Processo


FORM_BASE = {
    "area_direito": "CÍVEL",
    "fase": "conhecimento",
    "instancia": "1ª Instância",
    "gratuidade_justica_status": "nao_requerida",
}


class ProcessosEscopoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username, *, is_active=True):
        return User.objects.create_user(
            username=username, password="testpass", is_active=is_active
        )

    def _admin(self, username="admin_processos"):
        user = self._user(username)
        PerfilUsuario.objects.filter(user=user).update(is_admin_escritorio=True)
        return user

    def _autorizar(self, user, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel,
            tipo_conta=None,
            modulo=MODULO_PROCESSOS,
            ativo=True,
            nivel=nivel,
        )
        return papel

    def _cliente(self, responsavel, nome="Cliente Processo", *, ativo=True):
        return Cliente.objects.create(
            nome_razao_social=nome,
            tipo="PF",
            responsavel=responsavel,
            ativo=ativo,
        )

    def _processo(self, responsavel, cliente, titulo, *, status="ativo"):
        return Processo.objects.create(
            titulo=titulo,
            responsavel=responsavel,
            cliente=cliente,
            status=status,
        )

    def _payload(self, cliente, titulo="Processo alterado", **extra):
        payload = {"titulo": titulo, "cliente": cliente.pk, **FORM_BASE}
        payload.update(extra)
        return payload


class TestProcessosSomenteSeus(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0005_processos_somente_seus"

    def setUp(self):
        super().setUp()
        self.user = self._user("processos_somente_seus")
        self.outro = self._user("responsavel_alheio")
        self._autorizar(self.user, NIVEL_SOMENTE_SEUS)
        self.cliente = self._cliente(self.user)
        self.proprio = self._processo(self.user, self.cliente, "Processo próprio")
        self.alheio = self._processo(self.outro, self.cliente, "Processo alheio")
        self.arquivado_proprio = self._processo(
            self.user, self.cliente, "Arquivado próprio", status="arquivado"
        )
        self.arquivado_alheio = self._processo(
            self.outro, self.cliente, "Arquivado alheio", status="arquivado"
        )
        self.client.force_login(self.user)

    def test_ativos_arquivados_e_detalhe_respeitam_responsavel(self):
        ativos = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(ativos.status_code, 200)
        self.assertEqual(list(ativos.context["processos"]), [self.proprio])

        arquivados = self.client.get("/processos/arquivados/", HTTP_HOST=self.http_host)
        self.assertEqual(arquivados.status_code, 200)
        self.assertEqual(list(arquivados.context["processos"]), [self.arquivado_proprio])

        detalhe = self.client.get(
            f"/processos/{self.alheio.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(detalhe.status_code, 404)

    def test_escopos_acima_do_maximo_invalidos_vazio_e_equipe_sao_403(self):
        for valor in ("todos", "", "da_equipe", "inexistente"):
            with self.subTest(valor=valor):
                resposta = self.client.get(
                    "/processos/", {"escopo": valor}, HTTP_HOST=self.http_host
                )
                self.assertEqual(resposta.status_code, 403)

    def test_seletor_nao_expoe_todos_nem_equipe(self):
        resposta = self.client.get("/processos/", HTTP_HOST=self.http_host)
        conteudo = resposta.content.decode()
        self.assertNotIn('option value="todos"', conteudo)
        self.assertNotIn("Da equipe", conteudo)

    def test_criacao_forca_usuario_autenticado_apesar_de_post_adulterado(self):
        resposta = self.client.post(
            "/processos/novo/",
            self._payload(
                self.cliente,
                titulo="Criado com posse segura",
                responsavel=self.outro.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        criado = Processo.objects.get(titulo="Criado com posse segura")
        self.assertEqual(criado.responsavel_id, self.user.pk)

    def test_editar_processo_alheio_retorna_404_e_preserva_todos_os_campos(self):
        estado_anterior = Processo.objects.values().get(pk=self.alheio.pk)
        payload = self._payload(
            self.cliente,
            titulo="Título adulterado",
            numero="9999999-99.9999.9.99.9999",
            vara_juizo="Vara adulterada",
            valor_causa="12345.67",
            data_distribuicao="2026-08-20",
            prazo_proximo="2026-09-20",
            responsavel=self.user.pk,
        )
        formulario = ProcessoForm(
            payload,
            instance=Processo.objects.get(pk=self.alheio.pk),
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

        resposta = self.client.post(
            f"/processos/{self.alheio.pk}/editar/",
            payload,
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            Processo.objects.values().get(pk=self.alheio.pk),
            estado_anterior,
        )
        self.alheio.refresh_from_db()
        self.assertEqual(self.alheio.responsavel_id, self.outro.pk)

    def test_arquivar_processo_alheio_retorna_404_e_preserva_estado(self):
        resposta = self.client.post(
            f"/processos/{self.alheio.pk}/arquivar/",
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)
        self.alheio.refresh_from_db()
        self.assertEqual(self.alheio.status, "ativo")
        self.assertEqual(self.alheio.responsavel_id, self.outro.pk)

    def test_reabrir_processo_alheio_retorna_404_e_preserva_arquivamento(self):
        resposta = self.client.post(
            f"/processos/{self.arquivado_alheio.pk}/reabrir/",
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)
        self.arquivado_alheio.refresh_from_db()
        self.assertEqual(self.arquivado_alheio.status, "arquivado")
        self.assertEqual(self.arquivado_alheio.responsavel_id, self.outro.pk)

    def test_adicionar_movimentacao_alheia_retorna_404_e_nao_cria(self):
        quantidade_anterior = self.alheio.movimentacoes.count()
        payload = {
            "tipo": "andamento",
            "data": "2026-08-20T10:00",
            "descricao": "Movimentação adversarial válida",
        }
        formulario = MovimentacaoProcessualForm(payload)
        self.assertTrue(formulario.is_valid(), formulario.errors)

        resposta = self.client.post(
            f"/processos/{self.alheio.pk}/movimentacoes/nova/",
            payload,
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.alheio.movimentacoes.count(), quantidade_anterior)

    def test_adicionar_parte_alheia_retorna_404_e_nao_cria(self):
        quantidade_anterior = self.alheio.partes.count()
        payload = {
            "nome": "Parte adversarial válida",
            "tipo": "autor",
            "cpf_cnpj": "529.982.247-25",
        }
        formulario = ParteProcessoForm(payload)
        self.assertTrue(formulario.is_valid(), formulario.errors)

        resposta = self.client.post(
            f"/processos/{self.alheio.pk}/partes/nova/",
            payload,
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.alheio.partes.count(), quantidade_anterior)

    def test_cliente_ativo_independe_de_acesso_a_clientes_e_inativo_e_rejeitado(self):
        formulario = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        self.assertIn(self.cliente, formulario.context["form"].fields["cliente"].queryset)

        inativo = self._cliente(self.user, "Cliente inativo", ativo=False)
        resposta = self.client.post(
            "/processos/novo/",
            self._payload(inativo, titulo="Não deve existir"),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Processo.objects.filter(titulo="Não deve existir").exists())


class TestProcessosTodosNaoAdmin(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0005_processos_todos"

    def setUp(self):
        super().setUp()
        self.user = self._user("processos_todos")
        self.outro = self._user("dono_de_outro_processo")
        self._autorizar(self.user, NIVEL_TODOS)
        self.cliente = self._cliente(self.user)
        self.proprio = self._processo(self.user, self.cliente, "Processo próprio")
        self.alheio = self._processo(self.outro, self.cliente, "Processo alheio")
        self.client.force_login(self.user)

    def test_padrao_todos_e_reducao_temporaria_para_somente_seus(self):
        todos = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual({p.pk for p in todos.context["processos"]}, {self.proprio.pk, self.alheio.pk})
        self.assertEqual(todos.context["escopo_atual"], NIVEL_TODOS)

        proprios = self.client.get(
            "/processos/", {"escopo": NIVEL_SOMENTE_SEUS}, HTTP_HOST=self.http_host
        )
        self.assertEqual(list(proprios.context["processos"]), [self.proprio])
        novamente = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(novamente.context["escopo_atual"], NIVEL_TODOS)

    def test_seletor_expoe_todos_e_somente_seus_sem_equipe(self):
        resposta = self.client.get("/processos/", HTTP_HOST=self.http_host)
        conteudo = resposta.content.decode()
        self.assertIn('option value="somente_seus"', conteudo)
        self.assertIn('option value="todos"', conteudo)
        self.assertNotIn("Da equipe", conteudo)

    def test_detalhe_alheio_e_legivel_mas_interface_oculta_mutacoes(self):
        resposta = self.client.get(
            f"/processos/{self.alheio.pk}/", HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.context["pode_modificar"])
        conteudo = resposta.content.decode()
        self.assertNotIn("Editar processo", conteudo)
        self.assertNotIn("+ Adicionar andamento", conteudo)
        self.assertNotIn("+ Adicionar parte", conteudo)

    def test_cinco_mutacoes_alheias_retornam_404_sem_mudar_dados(self):
        titulo = self.alheio.titulo
        casos = [
            (f"/processos/{self.alheio.pk}/editar/", self._payload(self.cliente, "Invadido")),
            (f"/processos/{self.alheio.pk}/arquivar/", {}),
            (f"/processos/{self.alheio.pk}/reabrir/", {}),
            (
                f"/processos/{self.alheio.pk}/movimentacoes/nova/",
                {"tipo": "andamento", "data": "2026-08-19T10:00", "descricao": "Invadida"},
            ),
            (f"/processos/{self.alheio.pk}/partes/nova/", {"nome": "Invadida", "tipo": "autor"}),
        ]
        for url, dados in casos:
            with self.subTest(url=url):
                resposta = self.client.post(url, dados, HTTP_HOST=self.http_host)
                self.assertEqual(resposta.status_code, 404)

        self.alheio.refresh_from_db()
        self.assertEqual(self.alheio.titulo, titulo)
        self.assertEqual(self.alheio.status, "ativo")
        self.assertEqual(self.alheio.movimentacoes.count(), 0)
        self.assertEqual(self.alheio.partes.count(), 0)


class TestProcessosAdministradorEIntegridade(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0005_processos_admin_integridade"

    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.elegivel = self._user("responsavel_elegivel")
        self._autorizar(self.elegivel, NIVEL_SOMENTE_SEUS)
        self.inelegivel = self._user("responsavel_inelegivel")
        self.inativo = self._user("responsavel_inativo", is_active=False)
        self.cliente = self._cliente(self.admin)
        self.processo = self._processo(self.elegivel, self.cliente, "Processo administrável")
        self.client.force_login(self.admin)

    def test_admin_muta_processo_alheio_e_reatribui_a_elegivel(self):
        resposta = self.client.post(
            f"/processos/{self.processo.pk}/editar/",
            self._payload(
                self.cliente,
                titulo="Reatribuído",
                responsavel=self.admin.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.admin.pk)

    def test_admin_usa_todos_por_padrao_pode_reduzir_e_so_ve_elegiveis_no_form(self):
        todos = self.client.get("/processos/", HTTP_HOST=self.http_host)
        self.assertEqual(todos.context["escopo_atual"], NIVEL_TODOS)
        self.assertIn(self.processo, list(todos.context["processos"]))

        proprios = self.client.get(
            "/processos/", {"escopo": NIVEL_SOMENTE_SEUS}, HTTP_HOST=self.http_host
        )
        self.assertNotIn(self.processo, list(proprios.context["processos"]))

        novo = self.client.get("/processos/novo/", HTTP_HOST=self.http_host)
        responsaveis = novo.context["form"].fields["responsavel"].queryset
        self.assertIn(self.admin, responsaveis)
        self.assertIn(self.elegivel, responsaveis)
        self.assertNotIn(self.inelegivel, responsaveis)
        self.assertNotIn(self.inativo, responsaveis)

    def test_admin_nao_atribui_usuario_inativo_nem_sem_acesso_efetivo(self):
        for usuario in (self.inativo, self.inelegivel):
            with self.subTest(usuario=usuario.username):
                resposta = self.client.post(
                    f"/processos/{self.processo.pk}/editar/",
                    self._payload(self.cliente, responsavel=usuario.pk),
                    HTTP_HOST=self.http_host,
                )
                self.assertEqual(resposta.status_code, 200)
                self.assertFalse(resposta.context["form"].is_valid())
                self.processo.refresh_from_db()
                self.assertEqual(self.processo.responsavel_id, self.elegivel.pk)

    def test_responsavel_obrigatorio_e_protegido_contra_exclusao(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Processo.objects.create(titulo="Sem responsável")

        with self.assertRaises(ProtectedError):
            self.elegivel.delete()
        self.assertTrue(Processo.objects.filter(pk=self.processo.pk).exists())
