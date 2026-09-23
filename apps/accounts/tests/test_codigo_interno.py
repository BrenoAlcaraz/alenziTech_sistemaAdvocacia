"""
Código interno U/ADM de Usuário (specs/codigos-internos-processo-cliente-usuario.md).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.codigo_interno import codigo_usuario, numero_do_codigo, rotulo_usuario


class TestCodigoInternoUsuario(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "codigo_interno_usuario"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _promover_admin(self, user):
        # Mesmo caminho do provisionamento: o perfil nasce comum (signal)
        # e só depois é marcado como Administrador.
        perfil = user.perfil
        perfil.is_admin_escritorio = True
        perfil.save()

    def test_administrador_e_adm_e_nao_consome_numero(self):
        admin = self._user("admin_codigo")
        self._promover_admin(admin)
        comum = self._user("comum_codigo")

        self.assertEqual(codigo_usuario(admin), "ADM")
        self.assertIsNone(admin.perfil.numero_interno)
        self.assertEqual(codigo_usuario(comum), "U1")

    def test_usuarios_comuns_recebem_codigos_sequenciais(self):
        self.assertEqual(
            [codigo_usuario(self._user(f"u{i}")) for i in range(1, 4)],
            ["U1", "U2", "U3"],
        )

    def test_desativacao_mantem_codigo(self):
        user = self._user("desativado_codigo")
        user.is_active = False
        user.save()
        user.perfil.refresh_from_db()
        self.assertEqual(codigo_usuario(user), "U1")

    def test_rotulo_de_seletor_inclui_codigo(self):
        user = self._user("rotulo_codigo")
        user.first_name, user.last_name = "Ana", "Souza"
        self.assertEqual(rotulo_usuario(user), "U1 · Ana Souza (@rotulo_codigo)")

    def test_formato_de_codigo_na_busca(self):
        self.assertEqual(numero_do_codigo("P12", "P"), 12)
        self.assertEqual(numero_do_codigo(" p12 ", "P"), 12)
        for termo in ("12", "P", "P12a", "C12", "P 12"):
            with self.subTest(termo=termo):
                self.assertIsNone(numero_do_codigo(termo, "P"))
