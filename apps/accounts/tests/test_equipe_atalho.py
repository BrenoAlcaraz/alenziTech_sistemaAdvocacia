"""
Equipe como atalho de seleção (PDR-0028): helper compartilhado
(`apps/accounts/equipe_atalho.py`) e ausência do vínculo dinâmico de
Equipe (EquipeVinculada/VinculoIntegrante).
"""

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.equipe_atalho import SelecionarMembrosEquipeForm, dados_para_js
from apps.accounts.models import Equipe, MembroEquipe


class TestHelperEquipeAtalho(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_accounts_helper"

    def setUp(self):
        super().setUp()
        self.ana = User.objects.create_user("ana_helper", password="x", first_name="Ana", last_name="Silva")
        self.beto = User.objects.create_user("beto_helper", password="x")
        self.inativo = User.objects.create_user("inativo_helper", password="x", is_active=False)
        self.equipe = Equipe.objects.create(nome="Contabilidade")
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.beto, equipe=self.equipe, ativo=False)
        MembroEquipe.objects.create(usuario=self.inativo, equipe=self.equipe, ativo=True)

    def test_dados_trazem_so_membros_ativos_e_elegiveis(self):
        dados = dados_para_js(User.objects.all(), presentes=[self.ana.pk])
        self.assertEqual(
            dados["equipes"],
            {str(self.equipe.pk): {"nome": "Contabilidade", "membros": [{"id": self.ana.pk, "nome": "Ana Silva"}]}},
        )
        self.assertEqual(dados["presentes"], [self.ana.pk])

    def test_dados_filtram_por_universo_elegivel(self):
        dados = dados_para_js(User.objects.filter(pk=self.beto.pk))
        self.assertEqual(dados["equipes"][str(self.equipe.pk)]["membros"], [])

    def test_equipe_inativa_fica_de_fora(self):
        self.equipe.ativo = False
        self.equipe.save()
        self.assertEqual(dados_para_js(User.objects.all())["equipes"], {})

    def test_form_aceita_membro_ativo_e_rejeita_quem_nao_e(self):
        universo = User.objects.filter(is_active=True)
        valido = SelecionarMembrosEquipeForm(
            {"equipe": self.equipe.pk, "usuarios": [self.ana.pk]}, usuarios_elegiveis=universo
        )
        self.assertTrue(valido.is_valid())
        for intruso in (self.beto, self.inativo):
            invalido = SelecionarMembrosEquipeForm(
                {"equipe": self.equipe.pk, "usuarios": [intruso.pk]},
                usuarios_elegiveis=User.objects.all(),
            )
            self.assertFalse(invalido.is_valid(), intruso.username)

    def test_form_rejeita_usuario_fora_do_universo_elegivel(self):
        form = SelecionarMembrosEquipeForm(
            {"equipe": self.equipe.pk, "usuarios": [self.ana.pk]},
            usuarios_elegiveis=User.objects.exclude(pk=self.ana.pk),
        )
        self.assertFalse(form.is_valid())

    def test_mecanismo_de_vinculo_dinamico_nao_existe_mais(self):
        nomes = {modelo.__name__ for modelo in django_apps.get_app_config("accounts").get_models()}
        self.assertNotIn("EquipeVinculada", nomes)
        self.assertNotIn("VinculoIntegrante", nomes)
