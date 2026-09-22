"""
Convite de delegação (specs/delegacao-por-convite-agenda-tarefas.md,
issue #28): mecanismo compartilhado (`apps/accounts/delegacao.py` e
`ConviteDelegacao`) reaproveitado por Tarefas e Agenda.
"""

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django_tenants.test.cases import TenantTestCase

from apps.accounts.delegacao import (
    aceitar_convite,
    criar_convite_delegacao,
    delegacao_exige_convite,
    recusar_convite,
)
from apps.accounts.models import ConviteDelegacao, Equipe, MembroEquipe, PerfilUsuario


class TestDecisaoDelegacaoExigeConvite(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "delegacao_decisao"

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user("admin_delegacao", password="x")
        PerfilUsuario.objects.filter(user=self.admin).update(is_admin_escritorio=True)
        self.admin._state.fields_cache.pop("perfil", None)

        self.gerente = User.objects.create_user("gerente_delegacao", password="x")
        self.gerente_par = User.objects.create_user("gerente_par_delegacao", password="x")
        self.subordinado = User.objects.create_user("subordinado_delegacao", password="x")
        self.estranho = User.objects.create_user("estranho_delegacao", password="x")
        self.usuario_comum = User.objects.create_user("comum_delegacao", password="x")

        self.equipe = Equipe.objects.create(nome="Equipe A")
        MembroEquipe.objects.create(usuario=self.gerente, equipe=self.equipe, eh_gerente=True, ativo=True)
        MembroEquipe.objects.create(usuario=self.gerente_par, equipe=self.equipe, eh_gerente=True, ativo=True)
        MembroEquipe.objects.create(usuario=self.subordinado, equipe=self.equipe, eh_gerente=False, ativo=True)

    def test_admin_delega_direto_para_qualquer_um(self):
        self.assertFalse(delegacao_exige_convite(self.admin, self.estranho))
        self.assertFalse(delegacao_exige_convite(self.admin, self.subordinado))

    def test_gerente_delega_direto_para_subordinado_da_propria_equipe(self):
        self.assertFalse(delegacao_exige_convite(self.gerente, self.subordinado))

    def test_gerente_para_gerente_da_mesma_equipe_exige_convite(self):
        self.assertTrue(delegacao_exige_convite(self.gerente, self.gerente_par))

    def test_gerente_para_usuario_fora_da_equipe_exige_convite(self):
        self.assertTrue(delegacao_exige_convite(self.gerente, self.estranho))

    def test_usuario_comum_para_qualquer_um_exige_convite(self):
        self.assertTrue(delegacao_exige_convite(self.usuario_comum, self.estranho))
        self.assertTrue(delegacao_exige_convite(self.usuario_comum, self.subordinado))

    def test_subordinado_inativo_na_equipe_nao_conta_como_direto(self):
        MembroEquipe.objects.filter(usuario=self.subordinado, equipe=self.equipe).update(ativo=False)
        self.assertTrue(delegacao_exige_convite(self.gerente, self.subordinado))

    def test_equipe_inativa_nao_conta_como_direto(self):
        self.equipe.ativo = False
        self.equipe.save()
        self.assertTrue(delegacao_exige_convite(self.gerente, self.subordinado))


class TestFluxoConvite(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "delegacao_fluxo"

    def setUp(self):
        super().setUp()
        self.delegante = User.objects.create_user("delegante_fluxo", password="x")
        self.destinatario = User.objects.create_user("destinatario_fluxo", password="x")
        self.terceiro = User.objects.create_user("terceiro_fluxo", password="x")
        # Qualquer instância de model serve como `item` genérico do convite
        # nestes testes de mecanismo compartilhado — Tarefa/Compromisso
        # concretos entram nas issues #29/#30.
        self.item = Equipe.objects.create(nome="Item de teste")

    def _criar_convite(self):
        return criar_convite_delegacao(self.delegante, self.destinatario, self.item)

    def test_convite_nasce_pendente_vinculado_ao_item(self):
        convite = self._criar_convite()
        self.assertEqual(convite.status, ConviteDelegacao.STATUS_PENDENTE)
        self.assertEqual(convite.item, self.item)
        self.assertEqual(convite.delegante, self.delegante)
        self.assertEqual(convite.destinatario, self.destinatario)

    def test_destinatario_aceita(self):
        convite = self._criar_convite()
        aceitar_convite(convite, self.destinatario)
        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteDelegacao.STATUS_ACEITO)
        self.assertIsNotNone(convite.respondido_em)

    def test_destinatario_recusa_sem_justificativa(self):
        convite = self._criar_convite()
        recusar_convite(convite, self.destinatario)
        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteDelegacao.STATUS_RECUSADO)
        self.assertEqual(convite.justificativa_recusa, "")

    def test_destinatario_recusa_com_justificativa(self):
        convite = self._criar_convite()
        recusar_convite(convite, self.destinatario, justificativa="Sem capacidade essa semana.")
        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteDelegacao.STATUS_RECUSADO)
        self.assertEqual(convite.justificativa_recusa, "Sem capacidade essa semana.")

    def test_outro_usuario_nao_pode_responder_convite_alheio(self):
        convite = self._criar_convite()
        with self.assertRaises(PermissionDenied):
            aceitar_convite(convite, self.terceiro)
        with self.assertRaises(PermissionDenied):
            recusar_convite(convite, self.terceiro)
        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteDelegacao.STATUS_PENDENTE)

    def test_delegante_nao_pode_responder_o_proprio_convite_que_enviou(self):
        convite = self._criar_convite()
        with self.assertRaises(PermissionDenied):
            aceitar_convite(convite, self.delegante)

    def test_convite_ja_respondido_nao_pode_ser_respondido_de_novo(self):
        convite = self._criar_convite()
        aceitar_convite(convite, self.destinatario)
        with self.assertRaises(ValidationError):
            aceitar_convite(convite, self.destinatario)
        with self.assertRaises(ValidationError):
            recusar_convite(convite, self.destinatario)
