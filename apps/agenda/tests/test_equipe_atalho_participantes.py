"""
Equipe como atalho de seleção na Agenda (PDR-0028): a lista de
conferência envia só pessoas; cada uma vira ParticipanteCompromisso
individual e passa pela confirmação de presença de sempre (PDR-0020).
Autorização é a mesma de `adicionar_participante` (edição do
compromisso), sem habilitação nova.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, MembroEquipe, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_AGENDA, NIVEL_TODOS
from apps.agenda.models import Compromisso, ParticipanteCompromisso


class TestEquipeAtalhoParticipantes(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_agenda_atalho"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.responsavel = self._user("responsavel_agenda_atalho")
        self.membro_a = self._user("membro_a_agenda_atalho")
        self.membro_b = self._user("membro_b_agenda_atalho")
        self.fora = self._user("fora_agenda_atalho")
        self.equipe = Equipe.objects.create(nome="Equipe Agenda")
        MembroEquipe.objects.create(usuario=self.membro_a, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=self.equipe, ativo=True)
        self.compromisso = Compromisso.objects.create(
            titulo="Compromisso Atalho",
            data_hora_inicio="2026-09-10T10:00:00Z",
            responsavel=self.responsavel,
        )
        self.client.force_login(self.responsavel)

    def _user(self, username, *, com_agenda=True):
        user = User.objects.create_user(username=username, password="testpass")
        if com_agenda:
            papel = PapelAcesso.objects.create(nome=f"Papel Agenda {username}")
            UsuarioPapel.objects.create(usuario=user, papel=papel)
            PermissaoPapel.objects.create(
                papel=papel, tipo_conta=None, modulo=MODULO_AGENDA, ativo=True, nivel=NIVEL_TODOS,
            )
        return user

    def _adicionar(self, equipe, usuarios):
        return self.client.post(
            f"/agenda/{self.compromisso.pk}/participantes/equipe/adicionar/",
            {"equipe": equipe.pk, "usuarios": [u.pk for u in usuarios]},
            HTTP_HOST=self.http_host,
        )

    def _participantes(self):
        return set(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso)
            .values_list("usuario__username", flat=True)
        )

    def test_desmarcar_um_membro_convida_todos_menos_ele_como_pendentes(self):
        r = self._adicionar(self.equipe, [self.membro_a])
        self.assertRedirects(r, f"/agenda/{self.compromisso.pk}/editar/", fetch_redirect_response=False)
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.membro_a
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_PENDENTE)
        self.assertEqual(self._participantes(), {"membro_a_agenda_atalho"})

    def test_membro_confirma_presenca_normalmente(self):
        self._adicionar(self.equipe, [self.membro_a])
        self.client.force_login(self.membro_a)
        r = self.client.post(
            f"/agenda/{self.compromisso.pk}/confirmar-presenca/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        participacao = ParticipanteCompromisso.objects.get(
            compromisso=self.compromisso, usuario=self.membro_a
        )
        self.assertEqual(participacao.status, ParticipanteCompromisso.STATUS_CONFIRMADO)

    def test_nada_fica_ligado_a_equipe_depois(self):
        self._adicionar(self.equipe, [self.membro_a, self.membro_b])
        novo = self._user("novo_agenda_atalho")
        MembroEquipe.objects.create(usuario=novo, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.filter(usuario=self.membro_a, equipe=self.equipe).delete()
        self.assertEqual(
            self._participantes(), {"membro_a_agenda_atalho", "membro_b_agenda_atalho"}
        )

    def test_varias_equipes_sem_duplicar_nem_renotificar(self):
        outra = Equipe.objects.create(nome="Outra Equipe Agenda")
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=outra, ativo=True)
        MembroEquipe.objects.create(usuario=self.fora, equipe=outra, ativo=True)
        self._adicionar(self.equipe, [self.membro_a, self.membro_b])
        self._adicionar(outra, [self.membro_b, self.fora])
        self.assertEqual(
            ParticipanteCompromisso.objects.filter(compromisso=self.compromisso).count(), 3
        )

    def test_responsavel_nao_vira_participante_mesmo_estando_na_equipe(self):
        MembroEquipe.objects.create(usuario=self.responsavel, equipe=self.equipe, ativo=True)
        r = self._adicionar(self.equipe, [self.responsavel])
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self._participantes(), set())

    def test_usuario_fora_da_equipe_informada_e_rejeitado(self):
        r = self._adicionar(self.equipe, [self.membro_a, self.fora])
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self._participantes(), set())

    def test_sem_acesso_ao_modulo_e_negado_mesmo_com_post_direto(self):
        sem_acesso = self._user("sem_acesso_agenda_atalho", com_agenda=False)
        self.client.force_login(sem_acesso)
        r = self._adicionar(self.equipe, [self.membro_a])
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._participantes(), set())

    def test_edicao_mostra_lista_de_conferencia_sem_equipes_convidadas(self):
        r = self.client.get(f"/agenda/{self.compromisso.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Adicionar pessoa")
        self.assertContains(r, "Adicionar equipe")
        self.assertContains(r, "Adicionar selecionados")
        self.assertNotContains(r, "Equipes convidadas")

    def test_criacao_mostra_botao_da_equipe(self):
        r = self.client.get("/agenda/novo/", HTTP_HOST=self.http_host)
        self.assertContains(r, 'data-equipe-atalho-id="%d"' % self.equipe.pk)
        self.assertContains(r, 'id="participantes-lista"')

    def test_criacao_sem_equipe_cadastrada_mostra_aviso(self):
        self.equipe.ativo = False
        self.equipe.save()
        r = self.client.get("/agenda/novo/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Nenhuma equipe cadastrada ainda")

    def test_criacao_so_recebe_pessoas_individuais(self):
        r = self.client.post(
            "/agenda/novo/",
            {
                "titulo": "Compromisso por atalho",
                "tipo": "reuniao",
                "data_hora_inicio": "2026-09-20T10:00",
                "participantes": [self.membro_a.pk, self.membro_b.pk],
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        compromisso = Compromisso.objects.get(titulo="Compromisso por atalho")
        self.assertEqual(
            set(compromisso.participacoes.values_list("usuario__username", flat=True)),
            {"membro_a_agenda_atalho", "membro_b_agenda_atalho"},
        )
