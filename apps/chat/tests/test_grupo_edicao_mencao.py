"""
Revisão de 2026-09-19 no Chat: editar grupo (nome e integrantes) e chamar
alguém com @ (notificação de menção e destaque na mensagem).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_CHAT
from apps.chat.mencoes import destacar_mencoes, usernames_mencionados
from apps.chat.models import Conversa
from apps.notificacoes.models import Notificacao


class ChatBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.ana = self._user("ana")
        self.bruno = self._user("bruno")
        self.carla = self._user("carla")
        self.duda = self._user("duda")
        self.client.force_login(self.ana)

    def _user(self, username):
        user = User.objects.create_user(username=username, password="testpass", first_name=username.title())
        papel = PapelAcesso.objects.create(nome=f"Papel Chat {username}", ativo=True)
        UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, tipo_conta=None, modulo=MODULO_CHAT, ativo=True, nivel="")
        return user

    def _grupo(self, *participantes, titulo="Grupo X"):
        grupo = Conversa.objects.create(tipo=Conversa.TIPO_GRUPO, titulo=titulo)
        grupo.participantes.set(participantes)
        return grupo

    def _enviar(self, grupo, texto):
        return self.client.post(f"/chat/{grupo.pk}/", {"conteudo": texto}, HTTP_HOST=self.http_host)


class TestEditarGrupo(ChatBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_editar_grupo"

    def _editar(self, grupo, titulo, participantes):
        return self.client.post(
            f"/chat/{grupo.pk}/editar/",
            {"titulo": titulo, "participantes": [u.pk for u in participantes]},
            HTTP_HOST=self.http_host,
        )

    def test_altera_nome_e_integrantes_mantendo_quem_edita(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        r = self._editar(grupo, "Novo nome", [self.bruno, self.duda])
        self.assertEqual(r.status_code, 302)
        grupo.refresh_from_db()
        self.assertEqual(grupo.titulo, "Novo nome")
        self.assertEqual(
            set(grupo.participantes.values_list("username", flat=True)), {"ana", "bruno", "duda"},
        )

    def test_quem_foi_adicionado_e_notificado(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        self._editar(grupo, "G", [self.bruno, self.carla, self.duda])
        self.assertTrue(Notificacao.objects.filter(destinatario=self.duda).exists())
        self.assertFalse(Notificacao.objects.filter(destinatario=self.bruno).exists())

    def test_exige_ao_menos_dois_integrantes_alem_de_quem_edita(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        r = self._editar(grupo, "G", [self.bruno])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(grupo.participantes.count(), 3)

    def test_quem_nao_participa_recebe_404(self):
        grupo = self._grupo(self.bruno, self.carla, self.duda)
        self.assertEqual(self._editar(grupo, "Invasão", [self.bruno, self.carla]).status_code, 404)
        grupo.refresh_from_db()
        self.assertEqual(grupo.titulo, "Grupo X")

    def test_grupo_de_equipe_nao_e_editavel_aqui(self):
        equipe = Equipe.objects.create(nome="Equipe Chat")
        grupo = Conversa.objects.get(equipe=equipe)
        grupo.participantes.add(self.ana)
        self.assertEqual(self._editar(grupo, "Outro", [self.bruno, self.carla]).status_code, 404)

    def test_conversa_individual_nao_e_editavel(self):
        individual = Conversa.objects.create(tipo=Conversa.TIPO_INDIVIDUAL)
        individual.participantes.set([self.ana, self.bruno])
        self.assertEqual(self._editar(individual, "X", [self.bruno, self.carla]).status_code, 404)

    def test_grupo_avulso_mostra_botao_e_grupo_de_equipe_nao(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        r = self.client.get(f"/chat/{grupo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Editar grupo")
        equipe = Equipe.objects.create(nome="Equipe Sem Botao")
        g_equipe = Conversa.objects.get(equipe=equipe)
        g_equipe.participantes.add(self.ana)
        r = self.client.get(f"/chat/{g_equipe.pk}/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Editar grupo")


class TestMencao(ChatBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_mencao"

    def test_extrai_usernames_ignorando_email(self):
        self.assertEqual(usernames_mencionados("oi @Bruno e @carla. fale com a@b.com"), {"bruno", "carla"})

    def test_destaca_mencao_e_escapa_html(self):
        html = destacar_mencoes("<b>oi</b> @bruno")
        self.assertIn("&lt;b&gt;", html)
        self.assertIn('<span class="font-semibold underline">@bruno</span>', html)

    def test_mencionado_recebe_aviso_de_mencao_e_os_demais_o_generico(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        self._enviar(grupo, "@bruno olha isso")
        bruno = Notificacao.objects.filter(destinatario=self.bruno)
        self.assertEqual(bruno.count(), 1)
        self.assertIn("chamou você", bruno.first().mensagem)
        carla = Notificacao.objects.get(destinatario=self.carla)
        self.assertIn("Nova mensagem", carla.mensagem)

    def test_mencionar_quem_nao_esta_no_grupo_nao_notifica(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        self._enviar(grupo, "@duda venha")
        self.assertFalse(Notificacao.objects.filter(destinatario=self.duda).exists())

    def test_autor_nao_se_notifica_ao_se_mencionar(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        self._enviar(grupo, "@ana lembrete")
        self.assertFalse(Notificacao.objects.filter(destinatario=self.ana).exists())

    def test_sala_global_notifica_so_o_mencionado(self):
        self.client.post("/chat/global/", {"conteudo": "@duda ola"}, HTTP_HOST=self.http_host)
        self.assertTrue(Notificacao.objects.filter(destinatario=self.duda).exists())
        self.assertFalse(Notificacao.objects.filter(destinatario=self.bruno).exists())

    def test_mensagem_renderiza_a_mencao_em_destaque(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        self._enviar(grupo, "@bruno ola")
        r = self.client.get(f"/chat/{grupo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, '<span class="font-semibold underline">@bruno</span>', html=False)

    def test_pagina_expoe_participantes_para_autocompletar(self):
        grupo = self._grupo(self.ana, self.bruno, self.carla)
        r = self.client.get(f"/chat/{grupo.pk}/", HTTP_HOST=self.http_host)
        self.assertEqual(
            {p["username"] for p in r.context["mencionaveis"]}, {"bruno", "carla"},
        )
