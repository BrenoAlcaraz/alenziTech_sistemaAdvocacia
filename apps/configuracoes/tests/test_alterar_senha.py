from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase


class TestAlterarSenha(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0008_config_alterar_senha"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.usuario = User.objects.create_user("usuario_senha", password="senha-antiga-123")

    def _post_alterar_senha(self, old_password, new_password1, new_password2):
        return self.client.post(
            "/configuracoes/perfil/alterar-senha/",
            {
                "old_password": old_password,
                "new_password1": new_password1,
                "new_password2": new_password2,
            },
            HTTP_HOST=self.http_host,
        )

    def test_troca_senha_com_sucesso_mantem_sessao_ativa(self):
        self.client.force_login(self.usuario)

        resposta = self._post_alterar_senha(
            "senha-antiga-123", "senha-nova-456", "senha-nova-456"
        )

        self.assertRedirects(
            resposta, "/configuracoes/", fetch_redirect_response=False
        )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("senha-nova-456"))

        resposta_autenticada = self.client.get(
            "/configuracoes/", HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta_autenticada.status_code, 200)

    def test_senha_atual_incorreta_bloqueia_troca(self):
        self.client.force_login(self.usuario)

        resposta = self._post_alterar_senha(
            "senha-errada", "senha-nova-456", "senha-nova-456"
        )

        self.assertEqual(resposta.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("senha-antiga-123"))

    def test_confirmacao_divergente_bloqueia_troca(self):
        self.client.force_login(self.usuario)

        resposta = self._post_alterar_senha(
            "senha-antiga-123", "senha-nova-456", "senha-diferente-789"
        )

        self.assertEqual(resposta.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("senha-antiga-123"))

    def test_usuario_nao_autenticado_e_redirecionado_para_login(self):
        resposta = self.client.get(
            "/configuracoes/perfil/alterar-senha/", HTTP_HOST=self.http_host
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login/", resposta.url)
