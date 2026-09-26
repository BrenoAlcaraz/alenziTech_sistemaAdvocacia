"""Conversão de quem tinha mais de um papel ativo (migration 0007)."""

import importlib

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    PapelAcesso,
    PerfilUsuario,
    PermissaoPapel,
    PermissaoUsuario,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    CODIGO_PRESET_LIMITADO,
    MODULO_CLIENTES,
    MODULO_PROCESSOS,
)
from apps.processos.models import Processo

migracao = importlib.import_module("apps.accounts.migrations.0007_papel_unico_por_usuario")


class TestConversaoPapelUnico(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "papel_unico_migracao"

    def setUp(self):
        super().setUp()
        # Recria o estado anterior à constraint; o DDL volta no rollback do teste.
        constraint = next(
            c for c in UsuarioPapel._meta.constraints
            if c.name == "uniq_usuariopapel_um_ativo_por_usuario"
        )
        with connection.schema_editor() as editor:
            editor.remove_constraint(UsuarioPapel, constraint)

        self.admin = User.objects.create_user(username="admin_conv", password="x")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.limitado = PapelAcesso.objects.get(codigo_preset=CODIGO_PRESET_LIMITADO)
        self.papel_a = PapelAcesso.objects.create(nome="Conv A")
        self.papel_b = PapelAcesso.objects.create(nome="Conv B")
        PermissaoPapel.objects.create(
            papel=self.papel_a, modulo=MODULO_PROCESSOS, ativo=True, nivel="todos"
        )

    def _user(self, username, *papeis):
        user = User.objects.create_user(username=username, password="x")
        for papel in papeis:
            UsuarioPapel.objects.create(usuario=user, papel=papel, ativo=True)
        return user

    def _papeis_ativos(self, user):
        return list(
            UsuarioPapel.objects.filter(usuario=user, ativo=True).values_list("papel_id", flat=True)
        )

    def test_quem_tem_varios_papeis_vai_para_limitado(self):
        multi = self._user("multi", self.papel_a, self.papel_b)
        unico = self._user("unico", self.papel_a)

        migracao.unificar_papeis(django_apps, None)

        self.assertEqual(self._papeis_ativos(multi), [self.limitado.pk])
        self.assertEqual(self._papeis_ativos(unico), [self.papel_a.pk])

    def test_ajuste_individual_e_preservado(self):
        multi = self._user("multi_ajuste", self.papel_a, self.papel_b)
        PermissaoUsuario.objects.create(
            usuario=multi, modulo=MODULO_CLIENTES, ativo=True, nivel="todos"
        )

        migracao.unificar_papeis(django_apps, None)

        self.assertTrue(
            PermissaoUsuario.objects.filter(usuario=multi, modulo=MODULO_CLIENTES, ativo=True).exists()
        )

    def test_quem_perde_processos_tem_processos_transferidos(self):
        multi = self._user("multi_processos", self.papel_a, self.papel_b)
        unico = self._user("unico_processos", self.papel_a)
        do_multi = Processo.objects.create(criado_por=multi, titulo="Do multi")
        do_unico = Processo.objects.create(criado_por=unico, titulo="Do unico")
        do_multi.responsaveis.add(multi)
        do_unico.responsaveis.add(unico)

        migracao.unificar_papeis(django_apps, None)

        self.assertEqual(list(do_multi.responsaveis.all()), [self.admin])
        self.assertEqual(list(do_unico.responsaveis.all()), [unico])
