"""
Testes de múltiplos participantes e escolha de responsável em Tarefas
(specs/tarefas-multiplos-participantes.md).

Cobre: criar com vários atribuídos exige escolher o responsável entre
eles; os demais entram como `participantes` (não como responsável);
visibilidade da tarefa passa a incluir quem é participante; conclusão
continua exclusiva do responsável; gestão de participantes e de Equipe
como atalho de seleção (PDR-0028)
exige a mesma `tarefas_atribuir_outros` de sempre, sem habilitação
nova.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import Equipe, HabilitacaoPapel, MembroEquipe, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import (
    HAB_TAREFAS_ATRIBUIR_OUTROS,
    MODULO_TAREFAS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.tarefas.models import Tarefa


class MultiplosParticipantesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username):
        return User.objects.create_user(username=username, password="testpass")

    def _dar_modulo_tarefas(self, user, *, atribuir_outros=False, nivel=NIVEL_TODOS):
        papel = PapelAcesso.objects.create(nome=f"Papel Tarefas {user.username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_TAREFAS, ativo=True, nivel=nivel,
        )
        if atribuir_outros:
            HabilitacaoPapel.objects.create(
                papel=papel, modulo=MODULO_TAREFAS,
                item=HAB_TAREFAS_ATRIBUIR_OUTROS, ativo=True,
            )
        return papel


class TestCriarComMultiplosAtribuidos(MultiplosParticipantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_multi_criar"

    def setUp(self):
        super().setUp()
        self.criador = self._user("criador_multi_participantes")
        self._dar_modulo_tarefas(self.criador, atribuir_outros=True)
        self.bob = self._user("bob_multi_participantes")
        self.carol = self._user("carol_multi_participantes")
        self.client.force_login(self.criador)

    def _payload(self, **overrides):
        payload = {"titulo": "Tarefa Multi", "prioridade": "media"}
        payload.update(overrides)
        return payload

    def test_tres_atribuidos_permite_escolher_o_responsavel(self):
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(
                atribuidos=[self.criador.pk, self.bob.pk, self.carol.pk],
                destinatario=self.bob.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Tarefa Multi")
        self.assertEqual(tarefa.responsavel_id, self.bob.pk)
        self.assertEqual(
            set(tarefa.participantes.values_list("pk", flat=True)),
            {self.criador.pk, self.carol.pk},
        )

    def test_uma_unica_tarefa_nao_tres_copias(self):
        self.client.post(
            "/tarefas/nova/",
            self._payload(
                atribuidos=[self.criador.pk, self.bob.pk, self.carol.pk],
                destinatario=self.bob.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(Tarefa.objects.filter(titulo="Tarefa Multi").count(), 1)

    def test_multiplos_atribuidos_sem_escolher_responsavel_reporta_erro(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[self.bob.pk, self.carol.pk]),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("destinatario", r.context["form"].errors)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_um_unico_atribuido_e_o_responsavel(self):
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[self.bob.pk], destinatario=self.bob.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Tarefa Multi")
        self.assertEqual(tarefa.responsavel_id, self.bob.pk)
        self.assertEqual(tarefa.participantes.count(), 0)

    def test_responsavel_fora_dos_atribuidos_reporta_erro(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[self.bob.pk], destinatario=self.carol.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("destinatario", r.context["form"].errors)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_responsavel_e_obrigatorio_mesmo_com_um_atribuido(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[self.bob.pk]),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("destinatario", r.context["form"].errors)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_atribuidos_e_obrigatorio(self):
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(destinatario=self.bob.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("atribuidos", r.context["form"].errors)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_formulario_novo_vem_com_usuario_logado_preselecionado(self):
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        form = r.context["form"]
        self.assertEqual(form["atribuidos"].value(), [self.criador.pk])
        self.assertEqual(form["destinatario"].value(), self.criador.pk)
        self.assertIsNone(form.fields["destinatario"].empty_label)
        self.assertNotContains(r, "Eu mesmo")

    def test_sem_atribuir_outros_formulario_lista_so_o_proprio_usuario(self):
        sem_habilitacao = self._user("sem_habilitacao_listas")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.client.force_login(sem_habilitacao)
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        form = r.context["form"]
        for nome in ("atribuidos", "destinatario"):
            opcoes = [valor for valor, _ in form.fields[nome].widget.choices]
            self.assertEqual(opcoes, [sem_habilitacao.pk])

    def test_sem_atribuir_outros_criar_para_si_mesmo_e_permitido(self):
        sem_habilitacao = self._user("sem_habilitacao_si_mesmo")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.client.force_login(sem_habilitacao)
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[sem_habilitacao.pk], destinatario=sem_habilitacao.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Tarefa.objects.get(titulo="Tarefa Multi").responsavel_id, sem_habilitacao.pk)

    def test_responsavel_adulterado_fora_dos_atribuidos_sem_habilitacao_e_rejeitado(self):
        sem_habilitacao = self._user("sem_habilitacao_adulterado")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.client.force_login(sem_habilitacao)
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(atribuidos=[sem_habilitacao.pk], destinatario=self.bob.pk),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("destinatario", r.context["form"].errors)
        self.assertEqual(Tarefa.objects.count(), antes)

    def test_sem_atribuir_outros_atribuir_a_terceiro_e_negado(self):
        sem_habilitacao = self._user("sem_habilitacao_multi")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.client.force_login(sem_habilitacao)
        antes = Tarefa.objects.count()
        r = self.client.post(
            "/tarefas/nova/",
            self._payload(
                atribuidos=[sem_habilitacao.pk, self.bob.pk],
                destinatario=self.bob.pk,
            ),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Tarefa.objects.count(), antes)


class TestBotaoAtribuirATodos(MultiplosParticipantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_multi_atribuir_todos"

    def test_form_novo_lista_todos_os_usuarios_ativos_no_campo_atribuidos(self):
        criador = self._user("criador_atribuir_todos")
        self._dar_modulo_tarefas(criador, atribuir_outros=True)
        outro = self._user("outro_atribuir_todos")
        self.client.force_login(criador)
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        opcoes = set(r.context["form"].fields["atribuidos"].queryset.values_list("pk", flat=True))
        self.assertIn(criador.pk, opcoes)
        self.assertIn(outro.pk, opcoes)
        self.assertContains(r, "Atribuir a todos")


class TestVisibilidadeDeParticipante(MultiplosParticipantesBase):
    """Um usuário que é só participante (não responsável) consegue ver a
    tarefa, mas não aparece como quem a concluiu."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_multi_visibilidade"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_visibilidade_multi")
        self._dar_modulo_tarefas(self.responsavel)
        self.participante = self._user("participante_visibilidade_multi")
        self._dar_modulo_tarefas(self.participante, nivel=NIVEL_SOMENTE_SEUS)
        self.tarefa = Tarefa.objects.create(
            titulo="Tarefa Visibilidade Multi", responsavel=self.responsavel,
        )
        self.tarefa.participantes.add(self.participante)

    def test_participante_ve_a_tarefa_no_quadro(self):
        self.client.force_login(self.participante)
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Tarefa Visibilidade Multi")

    def test_participante_ve_a_tarefa_na_lista(self):
        self.client.force_login(self.participante)
        r = self.client.get("/tarefas/lista/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Tarefa Visibilidade Multi")

    def test_participante_nao_consegue_concluir(self):
        self.client.force_login(self.participante)
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 404)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "a_fazer")

    def test_responsavel_consegue_concluir_normalmente(self):
        self.client.force_login(self.responsavel)
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/concluir/", HTTP_HOST=self.http_host
        )
        self.assertEqual(r.status_code, 302)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.status, "concluida")

    def test_estranho_sem_ser_participante_nem_responsavel_nao_ve(self):
        estranho = self._user("estranho_visibilidade_multi")
        self._dar_modulo_tarefas(estranho, nivel=NIVEL_SOMENTE_SEUS)
        self.client.force_login(estranho)
        r = self.client.get("/tarefas/", HTTP_HOST=self.http_host)
        self.assertNotContains(r, "Tarefa Visibilidade Multi")


class TestGerenciarParticipantesNaEdicao(MultiplosParticipantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_multi_gerenciar_edicao"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_gerenciar_multi")
        self._dar_modulo_tarefas(self.responsavel, atribuir_outros=True)
        self.candidato = self._user("candidato_gerenciar_multi")
        self.tarefa = Tarefa.objects.create(
            titulo="Tarefa Gerenciar Multi", responsavel=self.responsavel,
        )
        self.client.force_login(self.responsavel)

    def test_adiciona_participante_individual(self):
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/participantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.candidato, self.tarefa.participantes.all())

    def test_remove_participante(self):
        self.tarefa.participantes.add(self.candidato)
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/participantes/{self.candidato.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.candidato, self.tarefa.participantes.all())

    def test_sem_atribuir_outros_e_negado(self):
        sem_habilitacao = self._user("sem_hab_gerenciar_multi")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.tarefa.responsavel = sem_habilitacao
        self.tarefa.save(update_fields=["responsavel"])
        self.client.force_login(sem_habilitacao)
        r = self.client.post(
            f"/tarefas/{self.tarefa.pk}/participantes/adicionar/",
            {"usuario": self.candidato.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(self.candidato, self.tarefa.participantes.all())


class TestEquipeComoAtalhoDaTarefa(MultiplosParticipantesBase):
    """Equipe como atalho de seleção (PDR-0028) aplicado a Tarefas: a
    equipe só marca pessoas; nada dela fica gravado."""

    @classmethod
    def get_test_schema_name(cls):
        return "tarefas_multi_equipe_atalho"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_equipe_tarefa")
        self._dar_modulo_tarefas(self.responsavel, atribuir_outros=True)
        self.membro_a = self._user("membro_a_equipe_tarefa")
        self.membro_b = self._user("membro_b_equipe_tarefa")
        self.fora = self._user("fora_equipe_tarefa")
        self.equipe = Equipe.objects.create(nome="Equipe Tarefa")
        MembroEquipe.objects.create(usuario=self.membro_a, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=self.equipe, ativo=True)
        self.tarefa = Tarefa.objects.create(
            titulo="Tarefa Equipe Participante", responsavel=self.responsavel,
        )
        self.client.force_login(self.responsavel)

    def _adicionar(self, equipe, usuarios, tarefa=None):
        tarefa = tarefa or self.tarefa
        return self.client.post(
            f"/tarefas/{tarefa.pk}/participantes/equipe/adicionar/",
            {"equipe": equipe.pk, "usuarios": [u.pk for u in usuarios]},
            HTTP_HOST=self.http_host,
        )

    def test_desmarcar_um_membro_inclui_todos_menos_ele(self):
        r = self._adicionar(self.equipe, [self.membro_a])
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(self.tarefa.participantes.all()), [self.membro_a])

    def test_nada_fica_ligado_a_equipe_depois(self):
        self._adicionar(self.equipe, [self.membro_a, self.membro_b])
        novo = self._user("novo_membro_equipe_tarefa")
        MembroEquipe.objects.create(usuario=novo, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.filter(usuario=self.membro_a, equipe=self.equipe).delete()
        self.assertEqual(
            set(self.tarefa.participantes.all()), {self.membro_a, self.membro_b}
        )

    def test_varias_equipes_sem_duplicar(self):
        outra = Equipe.objects.create(nome="Outra Equipe Tarefa")
        MembroEquipe.objects.create(usuario=self.membro_b, equipe=outra, ativo=True)
        MembroEquipe.objects.create(usuario=self.fora, equipe=outra, ativo=True)
        self._adicionar(self.equipe, [self.membro_a, self.membro_b])
        self._adicionar(outra, [self.membro_b, self.fora])
        self.assertEqual(self.tarefa.participantes.count(), 3)

    def test_responsavel_nao_vira_participante_mesmo_estando_na_equipe(self):
        MembroEquipe.objects.create(usuario=self.responsavel, equipe=self.equipe, ativo=True)
        self._adicionar(self.equipe, [self.responsavel, self.membro_a])
        self.assertNotIn(self.responsavel, self.tarefa.participantes.all())
        self.assertIn(self.membro_a, self.tarefa.participantes.all())

    def test_usuario_fora_da_equipe_informada_e_rejeitado(self):
        r = self._adicionar(self.equipe, [self.membro_a, self.fora])
        self.assertEqual(r.status_code, 404)
        self.assertFalse(self.tarefa.participantes.exists())

    def test_sem_habilitacao_e_negado_mesmo_com_post_direto(self):
        sem_habilitacao = self._user("sem_hab_equipe_tarefa")
        self._dar_modulo_tarefas(sem_habilitacao)
        self.client.force_login(sem_habilitacao)
        r = self._adicionar(self.equipe, [self.membro_a])
        self.assertEqual(r.status_code, 403)
        self.assertFalse(self.tarefa.participantes.exists())

    def test_edicao_mostra_lista_de_conferencia_sem_equipes_vinculadas(self):
        r = self.client.get(f"/tarefas/{self.tarefa.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Adicionar pessoa")
        self.assertContains(r, "Adicionar equipe")
        self.assertContains(r, "Adicionar selecionados")
        self.assertNotContains(r, "Equipes vinculadas")

    def test_criacao_mostra_botao_da_equipe(self):
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        self.assertContains(r, 'data-equipe-atalho-id="%d"' % self.equipe.pk)
        self.assertContains(r, "Equipe Tarefa")

    def test_criacao_sem_equipe_cadastrada_mostra_aviso(self):
        self.equipe.ativo = False
        self.equipe.save()
        r = self.client.get("/tarefas/nova/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Nenhuma equipe cadastrada ainda")

    def test_criacao_so_recebe_pessoas_individuais(self):
        r = self.client.post(
            "/tarefas/nova/",
            {
                "titulo": "Tarefa criada por atalho",
                "prioridade": "media",
                "atribuidos": [self.membro_a.pk, self.membro_b.pk],
                "destinatario": self.membro_a.pk,
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        tarefa = Tarefa.objects.get(titulo="Tarefa criada por atalho")
        self.assertEqual(tarefa.responsavel, self.membro_a)
        self.assertEqual(list(tarefa.participantes.all()), [self.membro_b])
