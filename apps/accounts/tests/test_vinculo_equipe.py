"""
Motor de vínculo dinâmico de Equipe como integrante/participante/
atribuído (specs/grupo-integrante-participante-dinamico.md) —
apps/accounts/vinculo_equipe.py.

Testado diretamente contra `Processo.integrantes_habilitados` (M2M real
já existente) como "alvo" de exemplo — o mesmo motor é reaproveitado
por apps/processos/signals.py e apps/agenda/signals.py, cobertos por
testes próprios de autorização/UI em cada app.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, MembroEquipe
from apps.accounts.vinculo_equipe import (
    desvincular_equipe,
    equipes_vinculadas,
    registrar_vinculo_individual,
    remover_pessoa,
    remover_vinculo_individual,
    vincular_equipe,
)
from apps.clientes.models import Cliente
from apps.processos.models import Processo


def _adicionar(processo, usuario):
    processo.integrantes_habilitados.add(usuario)


def _remover(processo, usuario):
    processo.integrantes_habilitados.remove(usuario)


class VinculoEquipeBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.ana = User.objects.create_user("ana_vinculo", password="testpass")
        self.bruno = User.objects.create_user("bruno_vinculo", password="testpass")
        self.responsavel = User.objects.create_user("resp_vinculo", password="testpass")
        self.cliente = Cliente.objects.create(
            responsavel=self.responsavel, nome_razao_social="Cliente Vínculo", tipo="PF",
        )
        self.processo = Processo.objects.create(
            responsavel=self.responsavel, titulo="Processo Vínculo",
        )
        self.equipe = Equipe.objects.create(nome="Equipe Vínculo")


class TestVincularEquipeMaterializaMembrosAtuais(VinculoEquipeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "vinculo_equipe_materializa"

    def test_vincula_equipe_adiciona_membros_efetivos_atuais(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.bruno, equipe=self.equipe, ativo=True)

        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

        self.assertIn(self.ana, self.processo.integrantes_habilitados.all())
        self.assertIn(self.bruno, self.processo.integrantes_habilitados.all())

    def test_membro_inativo_nao_e_materializado(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=False)

        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

        self.assertNotIn(self.ana, self.processo.integrantes_habilitados.all())

    def test_equipe_sem_membros_fica_vinculada_mesmo_assim(self):
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

        self.assertIn(self.equipe, equipes_vinculadas(self.processo))

    def test_vincular_duas_vezes_e_idempotente(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

        self.assertEqual(
            self.processo.integrantes_habilitados.filter(pk=self.ana.pk).count(), 1
        )


class TestSincronizacaoDinamicaDeMembros(VinculoEquipeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "vinculo_equipe_sincronizacao"

    def setUp(self):
        super().setUp()
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

    def test_novo_membro_da_equipe_passa_a_integrar_automaticamente(self):
        from apps.accounts.vinculo_equipe import sincronizar_membro_em_alvos

        membro = MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        sincronizar_membro_em_alvos(
            Processo, self.equipe, membro.usuario, ativo=True,
            aplicar_adicao=_adicionar, aplicar_remocao=_remover,
        )

        self.assertIn(self.ana, self.processo.integrantes_habilitados.all())

    def test_membro_que_sai_da_equipe_perde_o_vinculo(self):
        from apps.accounts.vinculo_equipe import sincronizar_membro_em_alvos

        membro = MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        sincronizar_membro_em_alvos(
            Processo, self.equipe, membro.usuario, ativo=True,
            aplicar_adicao=_adicionar, aplicar_remocao=_remover,
        )
        membro.delete()
        sincronizar_membro_em_alvos(
            Processo, self.equipe, self.ana, ativo=False,
            aplicar_adicao=_adicionar, aplicar_remocao=_remover,
        )

        self.assertNotIn(self.ana, self.processo.integrantes_habilitados.all())


class TestDesvincularEquipe(VinculoEquipeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "vinculo_equipe_desvincular"

    def test_desvincular_remove_quem_so_estava_pela_equipe(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)

        desvincular_equipe(self.processo, self.equipe, aplicar_remocao=_remover)

        self.assertNotIn(self.ana, self.processo.integrantes_habilitados.all())
        self.assertNotIn(self.equipe, equipes_vinculadas(self.processo))

    def test_desvincular_nao_afeta_quem_foi_adicionado_individualmente(self):
        """Um usuário adicionado individualmente (fora da equipe) não é
        afetado por entrar/sair de uma equipe."""
        self.processo.integrantes_habilitados.add(self.ana)
        registrar_vinculo_individual(self.processo, self.ana)

        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)
        desvincular_equipe(self.processo, self.equipe, aplicar_remocao=_remover)

        self.assertIn(self.ana, self.processo.integrantes_habilitados.all())

    def test_desvincular_uma_equipe_nao_afeta_outra_que_tambem_tem_o_usuario(self):
        outra_equipe = Equipe.objects.create(nome="Outra Equipe")
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.ana, equipe=outra_equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)
        vincular_equipe(self.processo, outra_equipe, aplicar_adicao=_adicionar)

        desvincular_equipe(self.processo, self.equipe, aplicar_remocao=_remover)

        self.assertIn(self.ana, self.processo.integrantes_habilitados.all())


class TestVinculoIndividualERemocaoDePessoa(VinculoEquipeBase):
    @classmethod
    def get_test_schema_name(cls):
        return "vinculo_equipe_individual"

    def test_remover_vinculo_individual_nao_mexe_em_materializacao_por_equipe(self):
        from apps.accounts.models import VinculoIntegrante
        from django.contrib.contenttypes.models import ContentType

        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)
        self.processo.integrantes_habilitados.add(self.ana)
        registrar_vinculo_individual(self.processo, self.ana)

        remover_vinculo_individual(self.processo, self.ana)

        ct = ContentType.objects.get_for_model(Processo)
        self.assertTrue(
            VinculoIntegrante.objects.filter(
                content_type=ct, object_id=self.processo.pk, usuario=self.ana, equipe=self.equipe,
            ).exists()
        )
        self.assertFalse(
            VinculoIntegrante.objects.filter(
                content_type=ct, object_id=self.processo.pk, usuario=self.ana, equipe=None,
            ).exists()
        )

    def test_remover_pessoa_limpa_vinculo_individual_e_por_equipe(self):
        MembroEquipe.objects.create(usuario=self.ana, equipe=self.equipe, ativo=True)
        vincular_equipe(self.processo, self.equipe, aplicar_adicao=_adicionar)
        self.processo.integrantes_habilitados.add(self.ana)
        registrar_vinculo_individual(self.processo, self.ana)

        self.processo.integrantes_habilitados.remove(self.ana)
        remover_pessoa(self.processo, self.ana)

        from apps.accounts.models import VinculoIntegrante
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Processo)
        self.assertFalse(
            VinculoIntegrante.objects.filter(
                content_type=ct, object_id=self.processo.pk, usuario=self.ana,
            ).exists()
        )
