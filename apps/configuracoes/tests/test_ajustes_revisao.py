"""
Ajustes da revisão de 2026-09-19 em Configurações: logo e cores do
escritório, excluir usuário, papel de acesso na criação de usuário e foto
de perfil visível aos colegas.
"""

import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django_tenants.test.cases import TenantTestCase
from PIL import Image

from apps.accounts.forms import CriarUsuarioEscritorioForm
from apps.accounts.models import Equipe, MembroEquipe, PapelAcesso, PerfilUsuario, UsuarioPapel
from apps.processos.models import Processo
from apps.notificacoes.models import Notificacao
from apps.saas_tenants.cores import (
    OPACIDADE_TEXTO_INATIVO, contraste, cores_predominantes, hex_para_rgb, misturar, tema,
)
from apps.saas_tenants.models import ConfiguracaoVisual

_MEDIA_TMP = tempfile.mkdtemp(prefix="lawsystem_test_config_ajustes_")


def tearDownModule():
    shutil.rmtree(_MEDIA_TMP, ignore_errors=True)


def _png(cor=(200, 30, 30), tamanho=(40, 40), fundo=None):
    imagem = Image.new("RGBA", tamanho, fundo or (0, 0, 0, 0))
    for x in range(10, 30):
        for y in range(10, 30):
            imagem.putpixel((x, y), (*cor, 255))
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return SimpleUploadedFile("logo.png", buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=_MEDIA_TMP)
class ConfigBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.admin = User.objects.create_user("admin_cfg", password="testpass")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.comum = User.objects.create_user("comum_cfg", password="testpass")
        self.client.force_login(self.admin)


class TestCores(TenantTestCase):
    def test_cor_predominante_do_logo_ignora_transparencia_e_branco(self):
        cores = cores_predominantes(_png((200, 30, 30), fundo=(255, 255, 255, 255)))
        self.assertEqual(len(cores), 1)
        self.assertEqual(hex_para_rgb(cores[0]), (200, 30, 30))

    def test_duas_cores_distintas_viram_principal_e_destaque(self):
        imagem = Image.new("RGB", (40, 40), (20, 60, 160))
        for x in range(20, 40):
            for y in range(40):
                imagem.putpixel((x, y), (220, 180, 20))
        buffer = io.BytesIO()
        imagem.save(buffer, format="PNG")
        cores = cores_predominantes(io.BytesIO(buffer.getvalue()))
        self.assertEqual(len(cores), 2)

    def test_cor_principal_clara_mantem_texto_da_barra_lateral_legivel(self):
        branco = (255, 255, 255)
        for cor in ("#ffe066", "#ffff00", "#00ffff", "#ffffff", "#7fff00", "#ff66cc"):
            with self.subTest(cor=cor):
                t = tema(cor, "#8B7355")
                principal = hex_para_rgb(t["primaria_hex"])
                hover = tuple(int(c) for c in t["primaria_hover_rgb"].split())
                inativo = misturar(branco, principal, OPACIDADE_TEXTO_INATIVO)
                self.assertGreaterEqual(contraste(inativo, principal), 4.5)
                self.assertGreaterEqual(contraste(branco, hover), 4.5)

    def test_cor_de_destaque_clara_fica_legivel_como_texto(self):
        for cor in ("#c9a227", "#ffe066", "#8B7355"):
            with self.subTest(cor=cor):
                destaque = hex_para_rgb(tema("#1a1a1a", cor)["secundaria_hex"])
                for fundo in ("#ffffff", "#f5f3ef", "#ede8e0"):
                    self.assertGreaterEqual(contraste(destaque, hex_para_rgb(fundo)), 4.5)

    def test_cor_ja_escura_nao_e_alterada(self):
        self.assertEqual(tema("#0a2540", "#5a4632")["primaria_hex"], "#0a2540")
        self.assertEqual(tema("#0a2540", "#5a4632")["secundaria_hex"], "#5a4632")

    def test_cor_invalida_cai_no_padrao(self):
        self.assertEqual(tema("azul", "")["primaria_rgb"], "26 26 26")


class TestIdentidadeVisual(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_identidade"

    def test_logo_novo_define_as_cores_do_sistema(self):
        r = self.client.post(
            "/configuracoes/identidade-visual/", {"logo": _png((200, 30, 30))},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        config = ConfiguracaoVisual.objects.get(escritorio=self.tenant)
        self.assertTrue(config.logo)
        self.assertEqual(hex_para_rgb(config.cor_primaria), (200, 30, 30))

    def test_manter_cores_preserva_as_atuais_ao_trocar_o_logo(self):
        ConfiguracaoVisual.objects.create(escritorio=self.tenant, cor_primaria="#123456")
        self.client.post(
            "/configuracoes/identidade-visual/", {"logo": _png((200, 30, 30)), "manter_cores": "on"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(ConfiguracaoVisual.objects.get(escritorio=self.tenant).cor_primaria, "#123456")

    def test_cores_podem_ser_ajustadas_a_mao(self):
        self.client.post(
            "/configuracoes/identidade-visual/",
            {"cor_primaria": "#0a2540", "cor_secundaria": "#c9a227"}, HTTP_HOST=self.http_host,
        )
        config = ConfiguracaoVisual.objects.get(escritorio=self.tenant)
        self.assertEqual((config.cor_primaria, config.cor_secundaria), ("#0a2540", "#c9a227"))

    def test_cor_invalida_e_recusada(self):
        r = self.client.post(
            "/configuracoes/identidade-visual/", {"cor_primaria": "vermelho"}, HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)

    def test_arquivo_que_nao_e_imagem_e_recusado(self):
        r = self.client.post(
            "/configuracoes/identidade-visual/",
            {"logo": SimpleUploadedFile("x.png", b"nao e imagem", content_type="image/png")},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)

    def test_remover_logo(self):
        self.client.post("/configuracoes/identidade-visual/", {"logo": _png()}, HTTP_HOST=self.http_host)
        self.client.post(
            "/configuracoes/identidade-visual/", {"remover_logo": "on"}, HTTP_HOST=self.http_host,
        )
        self.assertFalse(ConfiguracaoVisual.objects.get(escritorio=self.tenant).logo)

    def test_so_administrador_altera(self):
        self.client.force_login(self.comum)
        r = self.client.post(
            "/configuracoes/identidade-visual/", {"cor_primaria": "#000000"}, HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)

    def test_paginas_carregam_o_tema_e_o_logo_na_barra_lateral(self):
        self.client.post("/configuracoes/identidade-visual/", {"logo": _png()}, HTTP_HOST=self.http_host)
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertContains(r, "--cor-primaria-rgb:")
        self.assertContains(r, "Logo do escritório")

    def test_identidade_visual_mostra_a_cor_ajustada(self):
        ConfiguracaoVisual.objects.create(escritorio=self.tenant, cor_primaria="#ffe066")
        r = self.client.get("/configuracoes/identidade-visual/", HTTP_HOST=self.http_host)
        self.assertContains(r, "data-cores-aplicadas")
        self.assertContains(r, tema("#ffe066", "")["primaria_hex"])

    def test_identidade_visual_sem_ajuste_nao_mostra_cor_aplicada(self):
        ConfiguracaoVisual.objects.create(
            escritorio=self.tenant, cor_primaria="#0a2540", cor_secundaria="#5a4632",
        )
        r = self.client.get("/configuracoes/identidade-visual/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "data-cores-aplicadas")


class TestAcessibilidadeDoShell(ConfigBase):
    """Estrutura acessível comum a todas as telas (base_auth, barra lateral, cabeçalho)."""

    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_a11y"

    def test_pular_para_o_conteudo_e_o_primeiro_link(self):
        r = self.client.get("/processos/", HTTP_HOST=self.http_host)
        html = r.content.decode()
        corpo = html[html.index("<body"):]
        self.assertEqual(corpo.index("<a "), corpo.index('<a href="#conteudo"'))
        self.assertContains(r, 'id="conteudo"')

    def test_item_ativo_da_barra_lateral_tem_aria_current(self):
        r = self.client.get("/processos/", HTTP_HOST=self.http_host)
        html = r.content.decode()
        self.assertEqual(html.count('sidebar-item-active" aria-current="page"'), 1)

    def test_sino_anuncia_a_contagem_de_nao_lidas(self):
        Notificacao.objects.create(destinatario=self.admin, mensagem="a")
        Notificacao.objects.create(destinatario=self.admin, mensagem="b")
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertContains(r, 'aria-label="Notificações, 2 não lidas"')

    def test_sino_sem_notificacoes(self):
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertContains(r, 'aria-label="Notificações, nenhuma não lida"')


class TestExcluirUsuario(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_excluir"

    def _excluir(self, usuario, senha="testpass"):
        dados = {} if senha is None else {"senha": senha}
        return self.client.post(
            f"/configuracoes/usuarios/{usuario.pk}/excluir/", dados, HTTP_HOST=self.http_host,
        )

    def test_inativa_o_usuario_e_passa_os_processos_ao_administrador(self):
        alvo = User.objects.create_user("alvo_cfg", password="testpass")
        processo = Processo.objects.create(criado_por=alvo, titulo="Do alvo")
        processo.responsaveis.add(alvo)
        equipe = Equipe.objects.create(nome="Equipe Exclusao")
        MembroEquipe.objects.create(usuario=alvo, equipe=equipe, ativo=True)
        r = self._excluir(alvo)
        self.assertEqual(r.status_code, 302)
        alvo.refresh_from_db()
        self.assertFalse(alvo.is_active)
        processo.refresh_from_db()
        self.assertEqual(list(processo.responsaveis.values_list("pk", flat=True)), [self.admin.pk])
        self.assertFalse(MembroEquipe.objects.filter(usuario=alvo).exists())

    def test_sem_senha_nao_exclui(self):
        alvo = User.objects.create_user("alvo_sem_senha", password="outra-senha-1")
        self._excluir(alvo, senha=None)
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)

    def test_senha_errada_nao_exclui_e_avisa_sem_detalhar(self):
        alvo = User.objects.create_user("alvo_senha_errada", password="outra-senha-1")
        r = self._excluir(alvo, senha="errada")
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)
        self.assertEqual(r.status_code, 302)
        mensagens = [str(m) for m in r.wsgi_request._messages]
        self.assertEqual(mensagens, ["Senha incorreta. Nenhum usuário foi excluído."])

    def test_senha_do_usuario_excluido_nao_vale(self):
        alvo = User.objects.create_user("alvo_senha_dele", password="outra-senha-1")
        self._excluir(alvo, senha="outra-senha-1")
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)

    def test_senha_correta_nao_afeta_os_demais_usuarios(self):
        alvo = User.objects.create_user("alvo_isolado", password="outra-senha-1")
        outro = User.objects.create_user("outro_isolado", password="outra-senha-1")
        self._excluir(alvo)
        outro.refresh_from_db()
        self.assertTrue(outro.is_active)

    def test_usuario_excluido_some_da_lista(self):
        alvo = User.objects.create_user("alvo_lista_cfg", password="testpass")
        self._excluir(alvo)
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "@alvo_lista_cfg")

    def test_nao_exclui_a_si_mesmo(self):
        self._excluir(self.admin)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_usuario_comum_nao_exclui(self):
        alvo = User.objects.create_user("alvo2_cfg", password="testpass")
        self.client.force_login(self.comum)
        self.assertEqual(self._excluir(alvo).status_code, 403)
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)

    def test_get_nao_exclui(self):
        alvo = User.objects.create_user("alvo3_cfg", password="testpass")
        r = self.client.get(f"/configuracoes/usuarios/{alvo.pk}/excluir/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)
        alvo.refresh_from_db()
        self.assertTrue(alvo.is_active)

    def test_tela_pede_a_senha_para_excluir(self):
        User.objects.create_user("alvo4_cfg", password="testpass")
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertContains(r, "/excluir/")
        self.assertContains(r, 'name="senha"')


class TestNovoUsuarioComPapel(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_novo_usuario"

    def _dados(self, **kw):
        dados = {
            "username": "novo.usuario", "email": "novo@ex.com", "nome_completo": "Novo",
            "password1": "S3nha-forte-123", "password2": "S3nha-forte-123",
        }
        dados.update(kw)
        return dados

    def test_formulario_oferece_os_papeis_ativos(self):
        papel = PapelAcesso.objects.create(nome="Advogado Assoc", ativo=True)
        inativo = PapelAcesso.objects.create(nome="Inativo", ativo=False)
        form = CriarUsuarioEscritorioForm()
        self.assertIn(papel, form.fields["papel"].queryset)
        self.assertNotIn(inativo, form.fields["papel"].queryset)

    def test_formulario_nao_tem_tipo_de_conta_e_preseleciona_limitado(self):
        form = CriarUsuarioEscritorioForm()
        self.assertNotIn("grupo", form.fields)
        limitado = PapelAcesso.objects.get(codigo_preset="limitado")
        self.assertEqual(form.fields["papel"].initial, limitado.pk)
        self.assertIsNone(form.fields["papel"].empty_label)

    def test_tela_nao_mostra_tipo_de_conta(self):
        r = self.client.get("/configuracoes/usuarios/novo/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Tipo de conta")
        self.assertContains(r, "Papel de acesso")

    def test_papel_escolhido_e_atribuido_ao_novo_usuario(self):
        papel = PapelAcesso.objects.create(nome="Estagiário", ativo=True)
        form = CriarUsuarioEscritorioForm(data=self._dados(papel=papel.pk))
        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()
        self.assertTrue(UsuarioPapel.objects.filter(usuario=usuario, papel=papel, ativo=True).exists())

    def test_papel_e_obrigatorio(self):
        form = CriarUsuarioEscritorioForm(data=self._dados())
        self.assertFalse(form.is_valid())
        self.assertIn("papel", form.errors)

    def test_papel_inativo_e_recusado(self):
        inativo = PapelAcesso.objects.create(nome="Inativo 2", ativo=False)
        form = CriarUsuarioEscritorioForm(data=self._dados(papel=inativo.pk))
        self.assertFalse(form.is_valid())
        self.assertIn("papel", form.errors)


class TestFotoVisivelAosColegas(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_foto"

    def _dar_foto(self, usuario):
        perfil, _ = PerfilUsuario.objects.get_or_create(user=usuario)
        perfil.avatar = _png()
        perfil.save()

    def test_colega_ve_a_foto_de_outro_usuario(self):
        self._dar_foto(self.comum)
        r = self.client.get(f"/configuracoes/usuarios/{self.comum.pk}/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_sem_foto_devolve_404(self):
        r = self.client.get(f"/configuracoes/usuarios/{self.comum.pk}/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_exige_login(self):
        self._dar_foto(self.comum)
        self.client.logout()
        r = self.client.get(f"/configuracoes/usuarios/{self.comum.pk}/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)

    def test_usuario_inativo_nao_expoe_foto(self):
        self._dar_foto(self.comum)
        self.comum.is_active = False
        self.comum.save()
        r = self.client.get(f"/configuracoes/usuarios/{self.comum.pk}/foto/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)

    def test_lista_de_usuarios_mostra_a_foto(self):
        self._dar_foto(self.comum)
        r = self.client.get("/configuracoes/", HTTP_HOST=self.http_host)
        self.assertContains(r, f"/configuracoes/usuarios/{self.comum.pk}/foto/")

    def test_mensagem_do_chat_mostra_a_foto_do_autor(self):
        from apps.chat.models import Conversa, Mensagem

        self._dar_foto(self.comum)
        sala = Conversa.objects.create(tipo=Conversa.TIPO_GLOBAL, titulo="Sala Geral")
        Mensagem.objects.create(conversa=sala, autor=self.comum, conteudo="oi")
        from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
        from apps.accounts.permissoes_constants import MODULO_CHAT

        papel = PapelAcesso.objects.create(nome="Chat", ativo=True)
        UsuarioPapel.objects.create(usuario=self.admin, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_CHAT, ativo=True, nivel="")
        r = self.client.get("/chat/global/", HTTP_HOST=self.http_host)
        self.assertContains(r, f"/configuracoes/usuarios/{self.comum.pk}/foto/")


class TestVoltarGlobal(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_voltar"

    def test_tela_secundaria_traz_o_botao_voltar_global(self):
        r = self.client.get("/configuracoes/perfil/editar/", HTTP_HOST=self.http_host)
        self.assertContains(r, "data-voltar-global")

    def test_paginas_raiz_dos_modulos_nao_trazem_voltar(self):
        for url in ("/", "/configuracoes/"):
            with self.subTest(url=url):
                r = self.client.get(url, HTTP_HOST=self.http_host)
                self.assertEqual(r.status_code, 200)
                self.assertNotContains(r, "data-voltar-global")


class TestMenuDoUsuario(ConfigBase):
    @classmethod
    def get_test_schema_name(cls):
        return "config_ajustes_menu_usuario"

    def test_configuracoes_e_sair_ficam_no_menu_do_usuario_e_nao_na_sidebar(self):
        r = self.client.get("/", HTTP_HOST=self.http_host)
        html = r.content.decode()
        sidebar = html[html.index('id="sidebar"'):html.index("</nav>")]
        self.assertNotIn("/configuracoes/", sidebar)
        self.assertNotIn("/logout/", sidebar)
        menu = html[html.index('aria-label="Menu do usuário"'):html.index("</header>")]
        self.assertIn('href="/configuracoes/"', menu)
        self.assertIn('href="/logout/"', menu)
        self.assertIn("Sair do sistema", menu)
        self.assertIn("ADM", menu)
