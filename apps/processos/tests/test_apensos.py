from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context, tenant_context

from apps.accounts.permissoes_constants import NIVEL_SOMENTE_SEUS, NIVEL_TODOS
from apps.processos.forms import AdicionarApensoForm
from apps.processos.models import Processo, VinculoProcessoApenso
from apps.processos.services import (
    vincular_processos_apensos,
    vinculos_apensos_do,
)
from apps.processos.tests.test_escopo import ProcessosEscopoBase
from apps.saas_tenants.models import Escritorio


class TestApensosProcessos(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0007_apensos"

    def setUp(self):
        super().setUp()
        self.user = self._user("dono_apensos")
        self.outro = self._user("outro_dono_apensos")
        self._autorizar(self.user, NIVEL_TODOS)
        self.cliente_a = self._cliente(self.user, "Cliente A")
        self.cliente_b = self._cliente(self.outro, "Cliente B")
        self.a = self._processo(self.user, self.cliente_a, "Processo A")
        self.b = self._processo(self.outro, self.cliente_b, "Processo B")
        self.c = self._processo(self.user, self.cliente_a, "Processo C")
        Processo.objects.filter(pk=self.b.pk).update(
            numero="0000002-00.2026.8.00.0002",
            vara_juizo="2ª Vara Cível",
        )
        self.b.refresh_from_db()
        self.arquivado = self._processo(
            self.user,
            self.cliente_a,
            "Processo Arquivado",
            status="arquivado",
        )
        self.client.force_login(self.user)

    def _post_adicionar(self, origem, alvo):
        return self.client.post(
            f"/processos/{origem.pk}/apensos/adicionar/",
            {"processo_apenso": alvo},
            HTTP_HOST=self.http_host,
        )

    def _post_remover(self, origem, vinculo):
        return self.client.post(
            f"/processos/{origem.pk}/apensos/{vinculo.pk}/remover/",
            HTTP_HOST=self.http_host,
        )

    def test_servico_e_consulta_sao_simetricos_idempotentes_e_nao_transitivos(self):
        vinculo_ab, criado = vincular_processos_apensos(self.a, self.b)
        repetido, criado_repetido = vincular_processos_apensos(self.b, self.a)
        vincular_processos_apensos(self.b, self.c)

        self.assertTrue(criado)
        self.assertFalse(criado_repetido)
        self.assertEqual(vinculo_ab.pk, repetido.pk)
        self.assertEqual(VinculoProcessoApenso.objects.count(), 2)
        self.assertEqual(vinculos_apensos_do(self.a).get().outro_processo(self.a), self.b)
        self.assertEqual(
            {v.outro_processo(self.b) for v in vinculos_apensos_do(self.b)},
            {self.a, self.c},
        )
        self.assertFalse(vinculos_apensos_do(self.a).filter(
            processo_menor_id=min(self.a.pk, self.c.pk),
            processo_maior_id=max(self.a.pk, self.c.pk),
        ).exists())

    def test_autorrelacao_e_duplicidade_sao_protegidas_no_form_servico_e_banco(self):
        form = AdicionarApensoForm(
            {"processo_apenso": self.a.pk},
            processo_origem=self.a,
            processos_queryset=Processo.objects.all(),
        )
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValueError):
            vincular_processos_apensos(self.a, self.a)
        with self.assertRaises(ValidationError):
            VinculoProcessoApenso(
                processo_menor=self.a,
                processo_maior=self.a,
            ).save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoProcessoApenso.objects.bulk_create([
                VinculoProcessoApenso(
                    processo_menor_id=self.a.pk,
                    processo_maior_id=self.a.pk,
                )
            ])

        vincular_processos_apensos(self.a, self.c)
        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoProcessoApenso.objects.bulk_create([
                VinculoProcessoApenso(
                    processo_menor_id=min(self.a.pk, self.c.pk),
                    processo_maior_id=max(self.a.pk, self.c.pk),
                )
            ])
        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoProcessoApenso.objects.bulk_create([
                VinculoProcessoApenso(
                    processo_menor_id=max(self.a.pk, self.c.pk),
                    processo_maior_id=min(self.a.pk, self.c.pk),
                )
            ])

    def test_vincular_e_remover_preservam_dados_e_os_dois_processos(self):
        estado_a = Processo.objects.values().get(pk=self.a.pk)
        estado_c = Processo.objects.values().get(pk=self.c.pk)
        partes_a = set(self.a.partes.values_list("pk", flat=True))
        partes_c = set(self.c.partes.values_list("pk", flat=True))

        vinculo, _ = vincular_processos_apensos(self.a, self.c)
        vinculo.delete()

        self.assertEqual(Processo.objects.values().get(pk=self.a.pk), estado_a)
        self.assertEqual(Processo.objects.values().get(pk=self.c.pk), estado_c)
        self.assertEqual(set(self.a.partes.values_list("pk", flat=True)), partes_a)
        self.assertEqual(set(self.c.partes.values_list("pk", flat=True)), partes_c)
        self.assertEqual(VinculoProcessoApenso.objects.count(), 0)

    def test_excluir_processo_remove_apenas_o_vinculo_por_cascata(self):
        vincular_processos_apensos(self.a, self.c)
        c_pk = self.c.pk
        self.a.delete()
        self.assertTrue(Processo.objects.filter(pk=c_pk).exists())
        self.assertEqual(VinculoProcessoApenso.objects.count(), 0)

    def test_aba_vazia_contador_cards_navegacao_e_seletor(self):
        for aba in ("andamentos", "prazos", "documentos", "partes"):
            with self.subTest(aba=aba):
                existente = self.client.get(
                    f"/processos/{self.a.pk}/?aba={aba}",
                    HTTP_HOST=self.http_host,
                )
                self.assertEqual(existente.status_code, 200)

        vazia = self.client.get(
            f"/processos/{self.a.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        self.assertEqual(vazia.context["apensos_total"], 0)
        self.assertContains(vazia, "Nenhum processo referenciado como apenso.")

        vincular_processos_apensos(self.a, self.c)
        resposta = self.client.get(
            f"/processos/{self.a.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        self.assertContains(resposta, "Processo C")
        self.assertContains(resposta, f"/processos/{self.c.pk}/?aba=apensos")
        self.assertEqual(resposta.context["apensos_total"], 1)
        candidatos = resposta.context["form_apenso"].fields["processo_apenso"].queryset
        self.assertNotIn(self.a, candidatos)
        self.assertNotIn(self.b, candidatos)
        self.assertNotIn(self.c, candidatos)
        self.assertIn(self.arquivado, candidatos)

    def test_todos_le_apenso_alheio_mas_nao_pode_criar_ou_remover_relacao(self):
        vinculo, _ = vincular_processos_apensos(self.a, self.b)
        detalhe = self.client.get(
            f"/processos/{self.a.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        self.assertContains(detalhe, "Processo B")
        self.assertContains(detalhe, "0000002-00.2026.8.00.0002")
        self.assertContains(detalhe, "Cliente B")
        self.assertContains(detalhe, "outro_dono_apensos")
        self.assertContains(detalhe, f"/processos/{self.b.pk}/?aba=apensos")
        self.assertNotContains(detalhe, f"/apensos/{vinculo.pk}/remover/")
        self.assertEqual(self._post_adicionar(self.a, self.b.pk).status_code, 404)
        self.assertEqual(self._post_remover(self.a, vinculo).status_code, 404)
        self.assertTrue(VinculoProcessoApenso.objects.filter(pk=vinculo.pk).exists())

    def test_somente_seus_oculta_todo_conteudo_e_contagem_do_apenso_alheio(self):
        restrito = self._user("restrito_apensos")
        self._autorizar(restrito, NIVEL_SOMENTE_SEUS)
        proprio = self._processo(restrito, self.cliente_a, "Origem restrita")
        vincular_processos_apensos(proprio, self.b)
        self.client.force_login(restrito)

        resposta = self.client.get(
            f"/processos/{proprio.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        self.assertEqual(resposta.context["apensos_total"], 0)
        self.assertNotContains(resposta, "Processo B")
        self.assertNotContains(resposta, "0000002-00.2026.8.00.0002")
        self.assertNotContains(resposta, "Cliente B")
        self.assertNotContains(resposta, "outro_dono_apensos")
        self.assertNotContains(resposta, f"/processos/{self.b.pk}/?aba=apensos")
        self.assertContains(resposta, "Nenhum processo referenciado como apenso.")

    def test_dono_dos_dois_cria_idempotentemente_e_remove_pelos_dois_lados(self):
        primeira = self._post_adicionar(self.a, self.c.pk)
        segunda = self._post_adicionar(self.c, self.a.pk)
        self.assertEqual(primeira.status_code, 302)
        self.assertEqual(segunda.status_code, 302)
        self.assertEqual(VinculoProcessoApenso.objects.count(), 1)
        vinculo = VinculoProcessoApenso.objects.get()

        removida = self._post_remover(self.c, vinculo)
        self.assertEqual(removida.status_code, 302)
        self.assertFalse(VinculoProcessoApenso.objects.exists())
        self.assertEqual(
            Processo.objects.filter(pk__in=[self.a.pk, self.c.pk]).count(),
            2,
        )

    def test_admin_pode_relacionar_e_remover_processos_de_outros_responsaveis(self):
        admin = self._admin("admin_apensos")
        self._autorizar(admin, NIVEL_TODOS)
        self.client.force_login(admin)
        detalhe_inicial = self.client.get(
            f"/processos/{self.a.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        candidatos = detalhe_inicial.context["form_apenso"].fields[
            "processo_apenso"
        ].queryset
        self.assertIn(self.b, candidatos)
        self.assertIn(self.arquivado, candidatos)
        resposta = self._post_adicionar(self.a, self.b.pk)
        self.assertEqual(resposta.status_code, 302)
        vinculo = VinculoProcessoApenso.objects.get()
        detalhe = self.client.get(
            f"/processos/{self.a.pk}/?aba=apensos", HTTP_HOST=self.http_host
        )
        self.assertContains(detalhe, f"/apensos/{vinculo.pk}/remover/")
        self.assertEqual(self._post_remover(self.b, vinculo).status_code, 302)
        self.assertFalse(VinculoProcessoApenso.objects.exists())

    def test_idor_origem_alvo_vinculo_trocado_e_ids_inexistentes_nao_mutam(self):
        vinculo_bc, _ = vincular_processos_apensos(self.b, self.c)
        casos = [
            self._post_adicionar(self.b, self.c.pk),
            self._post_adicionar(self.a, self.b.pk),
            self._post_adicionar(self.a, 99999999),
            self._post_remover(self.a, vinculo_bc),
        ]
        self.assertTrue(all(resposta.status_code == 404 for resposta in casos))
        self.assertEqual(list(VinculoProcessoApenso.objects.all()), [vinculo_bc])

    def test_sem_permissao_de_modulo_recebe_403_nas_rotas_de_mutacao(self):
        sem_acesso = self._user("sem_acesso_apensos")
        self.client.force_login(sem_acesso)
        vinculo, _ = vincular_processos_apensos(self.a, self.c)
        adicionar = self._post_adicionar(self.a, self.c.pk)
        remover = self._post_remover(self.a, vinculo)
        self.assertEqual(adicionar.status_code, 403)
        self.assertEqual(remover.status_code, 403)
        self.assertTrue(VinculoProcessoApenso.objects.filter(pk=vinculo.pk).exists())


class TestApensosTenantIsolation(ProcessosEscopoBase):
    @classmethod
    def _fixture_setup(cls):
        return TransactionTestCase._fixture_setup.__func__(cls)

    def _fixture_teardown(self):
        return TransactionTestCase._fixture_teardown(self)

    @classmethod
    def get_test_schema_name(cls):
        return "wi0007_apensos_tenant"

    def test_seletor_e_post_nao_resolvem_processo_de_outro_tenant(self):
        user = self._user("dono_tenant_origem")
        self._autorizar(user, NIVEL_TODOS)
        cliente = self._cliente(user, "Cliente tenant origem")
        origem = self._processo(user, cliente, "Origem tenant atual")
        outro_tenant = Escritorio(
            schema_name="wi0007_apensos_externo",
            nome="Tenant externo WI-0007",
            slug="wi0007-apensos-externo",
        )
        with schema_context("public"):
            outro_tenant.save()
        try:
            with tenant_context(outro_tenant):
                remoto_user = User.objects.create_user("dono_remoto")
                from apps.clientes.models import Cliente

                remoto_cliente = Cliente.objects.create(
                    nome_razao_social="Cliente remoto secreto",
                    tipo="PF",
                    responsavel=remoto_user,
                )
                for indice in range(20):
                    remoto = Processo.objects.create(
                        titulo=f"Processo remoto secreto {indice}",
                        cliente=remoto_cliente,
                        responsavel=remoto_user,
                    )
                remoto_pk = remoto.pk

            self.client.force_login(user)
            detalhe = self.client.get(
                f"/processos/{origem.pk}/?aba=apensos", HTTP_HOST=self.http_host
            )
            self.assertNotContains(detalhe, "Processo remoto secreto")
            resposta = self.client.post(
                f"/processos/{origem.pk}/apensos/adicionar/",
                {"processo_apenso": remoto_pk},
                HTTP_HOST=self.http_host,
            )
            self.assertEqual(resposta.status_code, 404)
            self.assertFalse(VinculoProcessoApenso.objects.exists())
        finally:
            with schema_context("public"):
                outro_tenant.delete(force_drop=True)
