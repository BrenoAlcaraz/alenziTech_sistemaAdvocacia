"""
Grupo automático de Chat por Equipe — specs/chat-grupo-automatico-por-
equipe.md: criar uma Equipe cria o grupo correspondente e a lista de
participantes fica sincronizada com os membros efetivos da equipe.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, MembroEquipe
from apps.chat.models import Conversa


class GrupoPorEquipeBase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_grupo_por_equipe"

    def setUp(self):
        super().setUp()
        self.ana = User.objects.create_user("ana_eq", password="testpass")
        self.bruno = User.objects.create_user("bruno_eq", password="testpass")


class TestCriacaoDaEquipeGeraGrupo(GrupoPorEquipeBase):
    def test_criar_equipe_cria_grupo_de_chat_correspondente(self):
        equipe = Equipe.objects.create(nome="Equipe Cível")

        conversa = Conversa.objects.get(equipe=equipe)
        self.assertEqual(conversa.tipo, Conversa.TIPO_GRUPO)
        self.assertEqual(conversa.titulo, "Equipe Cível")
        self.assertEqual(conversa.participantes.count(), 0)

    def test_renomear_equipe_atualiza_titulo_do_grupo(self):
        equipe = Equipe.objects.create(nome="Nome antigo")
        equipe.nome = "Nome novo"
        equipe.save()

        conversa = Conversa.objects.get(equipe=equipe)
        self.assertEqual(conversa.titulo, "Nome novo")


class TestSincronizacaoDeMembros(GrupoPorEquipeBase):
    def setUp(self):
        super().setUp()
        self.equipe = Equipe.objects.create(nome="Equipe Trabalhista")
        self.conversa = Conversa.objects.get(equipe=self.equipe)

    def test_adicionar_membro_entra_no_grupo(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)

        self.assertIn(self.ana, self.conversa.participantes.all())

    def test_remover_membro_sai_do_grupo(self):
        membro = MembroEquipe.objects.create(
            usuario=self.ana, equipe=self.equipe, ativo=True
        )
        membro.delete()

        self.assertNotIn(self.ana, self.conversa.participantes.all())

    def test_membro_inativo_nao_fica_no_grupo(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=False)

        self.assertNotIn(self.ana, self.conversa.participantes.all())

    def test_sair_do_grupo_manualmente_nao_remove_da_equipe(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        self.conversa.participantes.remove(self.ana)

        self.assertTrue(
            MembroEquipe.objects.filter(usuario=self.ana, equipe=self.equipe).exists()
        )

    def test_grupo_reflete_apenas_membros_efetivos(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.bruno, equipe=self.equipe, ativo=True)

        self.assertEqual(
            set(self.conversa.participantes.values_list("pk", flat=True)),
            {self.ana.pk, self.bruno.pk},
        )
