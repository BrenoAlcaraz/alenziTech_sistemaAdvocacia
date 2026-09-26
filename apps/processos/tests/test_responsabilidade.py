"""Responsabilidade atribuída (PDR-0039): `criado_por` + N responsáveis.

Quem atribui: Administrador e habilitação `processos_atribuir_responsavel`
(qualquer usuário), gerente de equipe (subordinados). Responsáveis e quem
criou enxergam e editam; bandeira na lista só para o atribuído; filtro
"Responsabilidade"; avisos e prazos vão para os responsáveis.
"""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Equipe, HabilitacaoPapel, MembroEquipe, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.agenda.models import ItemAgenda
from apps.atividade.models import LogAtividade
from apps.notificacoes.models import Notificacao
from apps.processos.acompanhamento import _notificar_processo
from apps.processos.models import MovimentacaoProcessual, Processo
from apps.processos.services import (
    atribuir_responsaveis,
    destinatarios_do_processo,
    filtrar_processos_do_usuario,
    remover_responsaveis,
    transferir_processos_de_usuarios_sem_acesso,
    usuarios_atribuiveis_por,
)

from .test_escopo import ProcessosEscopoBase


class ResponsabilidadeBase(ProcessosEscopoBase):
    def setUp(self):
        super().setUp()
        self.admin = self._admin()
        self.gerente = self._user("gerente_resp")
        self.subordinado = self._user("subordinado_resp")
        self.estranho = self._user("estranho_resp")
        for usuario in (self.gerente, self.subordinado, self.estranho):
            self._autorizar(usuario, NIVEL_SOMENTE_SEUS)
        equipe = Equipe.objects.create(nome="Contencioso")
        MembroEquipe.objects.create(equipe=equipe, usuario=self.gerente, eh_gerente=True, ativo=True)
        MembroEquipe.objects.create(equipe=equipe, usuario=self.subordinado, eh_gerente=False, ativo=True)
        self.cliente = self._cliente(self.admin)
        self.processo = self._processo(self.admin, self.cliente, "PROCESSO")

    def _get(self, url):
        return self.client.get(url, HTTP_HOST=self.http_host)

    def _post(self, url, dados=None):
        return self.client.post(url, dados or {}, HTTP_HOST=self.http_host)

    def _url_atribuir(self, processo=None):
        return f"/processos/{(processo or self.processo).pk}/responsaveis/atribuir/"


class TestQuemPodeAtribuir(ResponsabilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "resp_quem_atribui"

    def test_admin_atribui_para_qualquer_usuario_e_mais_de_um(self):
        self.client.force_login(self.admin)
        self._post(self._url_atribuir(), {"usuarios": [self.subordinado.pk, self.estranho.pk]})
        self.assertEqual(
            set(self.processo.responsaveis.values_list("pk", flat=True)),
            {self.subordinado.pk, self.estranho.pk},
        )
        self.assertEqual(LogAtividade.objects.filter(tipo="processo_responsavel_atribuido").count(), 2)

    def test_habilitacao_equivale_ao_admin(self):
        papel = UsuarioPapel.objects.get(usuario=self.estranho).papel
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_ATRIBUIR_RESPONSAVEL, ativo=True,
        )
        self.assertIn(self.gerente, usuarios_atribuiveis_por(self.estranho))

    def test_gerente_atribui_so_para_subordinados(self):
        self.assertEqual(list(usuarios_atribuiveis_por(self.gerente)), [self.subordinado])
        self.processo.responsaveis.add(self.gerente)
        self.client.force_login(self.gerente)
        self._post(self._url_atribuir(), {"usuarios": [self.subordinado.pk]})
        self.assertTrue(self.processo.responsaveis.filter(pk=self.subordinado.pk).exists())
        resposta = self._post(self._url_atribuir(), {"usuarios": [self.estranho.pk]})
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(self.processo.responsaveis.filter(pk=self.estranho.pk).exists())

    def test_gerente_nao_remove_quem_nao_poderia_atribuir(self):
        self.processo.responsaveis.add(self.gerente, self.estranho)
        self.client.force_login(self.gerente)
        resposta = self._post(f"/processos/{self.processo.pk}/responsaveis/{self.estranho.pk}/remover/")
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(self.processo.responsaveis.filter(pk=self.estranho.pk).exists())

    def test_usuario_comum_nao_ve_card_nem_atribui(self):
        self.processo.responsaveis.add(self.estranho)
        self.client.force_login(self.estranho)
        conteudo = self._get(f"/processos/{self.processo.pk}/").content.decode()
        self.assertNotIn("data-card-atribuir-responsabilidade", conteudo)
        self.assertEqual(self._post(self._url_atribuir(), {"usuarios": [self.estranho.pk]}).status_code, 403)

    def test_card_aparece_para_admin(self):
        self.client.force_login(self.admin)
        conteudo = self._get(f"/processos/{self.processo.pk}/").content.decode()
        self.assertIn("data-card-atribuir-responsabilidade", conteudo)
        self.assertIn("Atribuir responsável(is)", conteudo)

    def test_remover_responsavel(self):
        self.processo.responsaveis.add(self.subordinado)
        self.client.force_login(self.admin)
        self._post(f"/processos/{self.processo.pk}/responsaveis/{self.subordinado.pk}/remover/")
        self.assertFalse(self.processo.responsaveis.exists())
        self.assertTrue(LogAtividade.objects.filter(tipo="processo_responsavel_removido").exists())


class TestFormularioDoProcesso(ResponsabilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "resp_formulario"

    def test_quem_nao_atribui_nao_ve_campo_e_vira_criador(self):
        self.client.force_login(self.estranho)
        resposta = self._get("/processos/novo/")
        self.assertNotIn("atribuir_responsaveis", resposta.context["form"].fields)
        self.assertNotIn("responsavel", resposta.context["form"].fields)
        self._post("/processos/novo/", self._payload(self.cliente, titulo="Novo", numero="999"))
        criado = Processo.objects.get(numero="999")
        self.assertEqual(criado.criado_por, self.estranho)
        self.assertFalse(criado.responsaveis.exists())

    def test_admin_atribui_no_formulario_de_novo(self):
        self.client.force_login(self.admin)
        self._post("/processos/novo/", self._payload(
            self.cliente, titulo="Novo", numero="998", atribuir_responsaveis=[self.subordinado.pk],
        ))
        criado = Processo.objects.get(numero="998")
        self.assertEqual(criado.criado_por, self.admin)
        self.assertEqual(list(criado.responsaveis.all()), [self.subordinado])

    def test_edicao_do_gerente_preserva_responsaveis_fora_do_seu_conjunto(self):
        self.processo.responsaveis.add(self.gerente, self.estranho, self.subordinado)
        self.client.force_login(self.gerente)
        # Gerente desmarca o subordinado; estranho não está no seu conjunto.
        self._post(f"/processos/{self.processo.pk}/editar/", self._payload(self.cliente, titulo="Editado"))
        self.assertEqual(
            set(self.processo.responsaveis.values_list("pk", flat=True)),
            {self.gerente.pk, self.estranho.pk},
        )


class TestEscopoEMarcacoes(ResponsabilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "resp_escopo"

    def test_somente_seus_inclui_criador_e_responsavel(self):
        criado = self._processo(self.estranho, None, "CRIADO")
        atribuido = self._processo(self.admin, None, "ATRIBUIDO")
        atribuido.responsaveis.add(self.estranho)
        visiveis = set(filtrar_processos_do_usuario(Processo.objects.all(), self.estranho))
        self.assertEqual(visiveis, {criado, atribuido})

    def test_responsavel_edita_o_processo(self):
        self.processo.responsaveis.add(self.estranho)
        self.client.force_login(self.estranho)
        resposta = self._post(f"/processos/{self.processo.pk}/editar/", self._payload(self.cliente, titulo="Editado"))
        self.assertEqual(resposta.status_code, 302)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.titulo, "EDITADO")

    def test_bandeira_so_para_o_atribuido_e_etiqueta_para_todos(self):
        self.processo.responsaveis.add(self.subordinado)
        self.client.force_login(self.subordinado)
        self.assertIn("data-bandeira-responsavel", self._get("/processos/").content.decode())
        self.client.force_login(self.admin)
        self.assertNotIn("data-bandeira-responsavel", self._get("/processos/").content.decode())
        detalhe = self._get(f"/processos/{self.processo.pk}/").content.decode()
        self.assertIn("data-responsaveis", detalhe)
        self.assertIn(self.subordinado.username, detalhe)

    def test_filtro_de_responsabilidade(self):
        outro = self._processo(self.admin, None, "OUTRO")
        self.processo.responsaveis.add(self.admin)
        self.client.force_login(self.admin)

        def titulos(query):
            return {p.titulo for p in self._get(f"/processos/?{query}").context["processos"]}

        self.assertEqual(titulos("responsabilidade=minha"), {"PROCESSO"})
        self.assertEqual(titulos("responsabilidade=nenhum"), {outro.titulo})
        self.assertEqual(titulos(f"responsabilidade={self.admin.pk}"), {"PROCESSO"})

    def test_fila_sem_responsavel_ativo(self):
        inativo = self._user("inativo_resp", is_active=False)
        com_inativo = self._processo(self.admin, None, "COM INATIVO")
        com_inativo.responsaveis.add(inativo)
        ativo = self._processo(self.admin, None, "COM ATIVO")
        ativo.responsaveis.add(self.subordinado)
        self.client.force_login(self.admin)
        processos = self._get("/processos/?fila=sem_responsavel").context["processos"]
        self.assertEqual({p.titulo for p in processos}, {"PROCESSO", "COM INATIVO"})


class TestAvisosEPrazos(ResponsabilidadeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "resp_avisos_prazos"

    def _andamento_com_prazo(self):
        return MovimentacaoProcessual.objects.create(
            processo=self.processo, descricao="Intimação", tipo="intimacao",
            data_prazo=timezone.localdate() + timedelta(days=10),
        )

    def test_avisos_vao_para_todos_os_responsaveis(self):
        self.processo.responsaveis.add(self.subordinado, self.estranho)
        _notificar_processo(self.processo, "aviso")
        self.assertEqual(
            set(Notificacao.objects.filter(mensagem="aviso").values_list("destinatario_id", flat=True)),
            {self.subordinado.pk, self.estranho.pk},
        )

    def test_sem_responsavel_o_aviso_vai_para_quem_criou(self):
        self.assertEqual(destinatarios_do_processo(self.processo), [self.admin])

    def test_prazo_gerado_primeiro_responsavel_e_demais_participantes(self):
        atribuir_responsaveis(self.processo, [self.subordinado, self.estranho], por=self.admin)
        item = ItemAgenda.objects.get(movimentacao_origem=self._andamento_com_prazo())
        self.assertEqual(item.responsavel, self.subordinado)
        self.assertEqual(list(item.participacoes.values_list("usuario_id", flat=True)), [self.estranho.pk])

    def test_prazo_em_aberto_acompanha_a_mudanca_de_responsaveis(self):
        atribuir_responsaveis(self.processo, [self.subordinado], por=self.admin)
        andamento = self._andamento_com_prazo()
        remover_responsaveis(self.processo, [self.subordinado])
        atribuir_responsaveis(self.processo, [self.estranho, self.gerente], por=self.admin)
        item = ItemAgenda.objects.get(movimentacao_origem=andamento)
        self.assertEqual(item.responsavel, self.estranho)
        self.assertEqual(list(item.participacoes.values_list("usuario_id", flat=True)), [self.gerente.pk])

    def test_perda_de_acesso_tira_o_responsavel_e_poe_o_admin(self):
        self.processo.responsaveis.add(self.estranho)
        PermissaoPapel.objects.filter(papel=UsuarioPapel.objects.get(usuario=self.estranho).papel).update(ativo=False)
        transferir_processos_de_usuarios_sem_acesso([self.estranho.pk])
        self.assertEqual(list(self.processo.responsaveis.all()), [self.admin])
