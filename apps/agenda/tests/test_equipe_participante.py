"""
Testes de vínculo dinâmico de Equipe como participante do Compromisso
(specs/grupo-integrante-participante-dinamico.md) — reaproveita o mesmo
motor de apps/accounts/vinculo_equipe.py (testado em
apps/accounts/tests/test_vinculo_equipe.py). Aqui cobre a integração
real via view + sinal de MembroEquipe: cada membro entra como
ParticipanteCompromisso individual e passa pela confirmação de sempre
(PDR-0020) — a equipe não pula a confirmação; responsável nunca vira
participante; mesma autorização de `adicionar_participante` de hoje
(sem habilitação nova).
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, MembroEquipe, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS
from apps.agenda.models import Compromisso, ParticipanteCompromisso


class EquipeParticipanteBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_acesso_agenda(self, user, *, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Agenda {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=nivel,
        )

    def _compromisso(self, *, responsavel, **kwargs):
        defaults = {"titulo": "Compromisso Equipe Participante", "data_hora_inicio": "2026-09-10T10:00:00Z"}
        defaults.update(kwargs)
        return Compromisso.objects.create(responsavel=responsavel, **defaults)


class TestAdicionarERemoverEquipeParticipante(EquipeParticipanteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "equipe_participante_add_remove"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_equipe_participante")
        self._dar_acesso_agenda(self.responsavel)
        self.membro_a = self._user("membro_a_equipe_participante")
        self.membro_b = self._user("membro_b_equipe_participante")
        self.equipe = Equipe.objects.create(nome="Equipe Agenda Participante")
        MembroEquipe.objects.create(usuario=self.membro_a, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=self.equipe, ativo=True)
        self.compromisso = self._compromisso(responsavel=self.responsavel)
        self.client.force_login(self.responsavel)

    def test_adicionar_equipe_convida_todos_os_membros_atuais_como_pendentes(self):
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertRedirects(r, f"/agenda/{self.compromisso.pk}/editar/", fetch_redirect_response=False)
        for membro in (self.membro_a, self.membro_b):
            participacao = ParticipanteCompromisso.objects.get(compromisso=self.compromisso, usuario=membro)
            self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_PENDENTE)

    def test_membro_pode_confirmar_presenca_normalmente(self):
        self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self._dar_acesso_agenda(self.membro_a)
        self.client.force_login(self.membro_a)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        participacao = ParticipanteCompromisso.objects.get(compromisso=self.compromisso, usuario=self.membro_a)
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_CONFIRMADO)

    def test_remover_equipe_desfaz_participacao_de_todos_os_membros(self):
        self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/{self.equipe.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=self.membro_a).exists()
        )
        self.assertFalse(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=self.membro_b).exists()
        )

    def test_responsavel_nao_vira_participante_mesmo_estando_na_equipe(self):
        MembroEquipe.objects.create(usuario=self.responsavel, equipe=self.equipe, ativo=True)
        self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertFalse(
            ParticipanteCompromisso.objects.filter(
                compromisso=self.compromisso, usuario=self.responsavel
            ).exists()
        )


class TestSincronizacaoDinamicaViaCompromisso(EquipeParticipanteBase):
    @classmethod
    def get_test_schema_name(cls):
        return "equipe_participante_sincronizacao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_sync_participante")
        self._dar_acesso_agenda(self.responsavel)
        self.equipe = Equipe.objects.create(nome="Equipe Sincronização Agenda")
        self.compromisso = self._compromisso(responsavel=self.responsavel)
        self.client.force_login(self.responsavel)
        self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": self.equipe.pk},
            HTTP_HOST=self.http_host,
        )

    def test_novo_membro_e_convidado_automaticamente(self):
        novo = self._user("novo_membro_sync_participante")
        MembroEquipe.objects.create(usuario=novo, equipe=self.equipe, ativo=True)

        self.assertTrue(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=novo).exists()
        )

    def test_membro_que_sai_perde_a_participacao(self):
        saindo = self._user("saindo_membro_sync_participante")
        vinculo = MembroEquipe.objects.create(usuario=saindo, equipe=self.equipe, ativo=True)
        self.assertTrue(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=saindo).exists()
        )

        vinculo.delete()

        self.assertFalse(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=saindo).exists()
        )

    def test_membro_com_confirmacao_ja_dada_que_sai_perde_a_participacao(self):
        """Saída de equipe remove mesmo se o membro já tinha confirmado
        presença — a materialização por equipe é a única justificativa."""
        saindo = self._user("confirmado_sync_participante")
        vinculo = MembroEquipe.objects.create(usuario=saindo, equipe=self.equipe, ativo=True)
        ParticipanteCompromisso.objects.filter(
            compromisso=self.compromisso, usuario=saindo
        ).update(status=ParticipanteCompromisso.STATUS_CONFIRMADO)

        vinculo.delete()

        self.assertFalse(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso, usuario=saindo).exists()
        )
