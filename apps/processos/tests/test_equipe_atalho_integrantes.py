"""
Equipe como atalho de seleção em Processos (PDR-0028): a lista de
conferência envia só pessoas; nada da equipe fica gravado. Autorização é
a mesma `gerir_habilitar_usuario_processos` de sempre (PDR-0014).
"""

import json

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import (
    Equipe,
    HabilitacaoPapel,
    MembroEquipe,
    PapelAcesso,
    PermissaoPapel,
    UsuarioPapel,
)
from apps.accounts.permissoes_constants import (
    HAB_GERIR_HABILITAR_USUARIO_PROCESSOS,
    MODULO_GERIR,
    MODULO_PROCESSOS,
    NIVEL_SOMENTE_SEUS,
    NIVEL_TODOS,
)
from apps.processos.models import Processo


class EquipeAtalhoIntegrantesBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"

    def _user(self, username, *, com_processos=True, nivel=NIVEL_SOMENTE_SEUS):
        user = User.objects.create_user(username=username, password="testpass")
        if com_processos:
            papel = PapelAcesso.objects.create(nome=f"Papel Processos {username}")
            UsuarioPapel.objects.create(usuario=user, papel=papel)
            PermissaoPapel.objects.create(
                papel=papel, modulo=MODULO_PROCESSOS,
                ativo=True, nivel=nivel,
            )
        return user

    def _gestor(self, username="gestor_equipe_atalho"):
        user = self._user(username, nivel=NIVEL_TODOS)
        papel = PapelAcesso.objects.create(nome=f"Papel Gerir {username}")
        UsuarioPapel.objects.create(usuario=user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR, ativo=True, nivel="",
        )
        HabilitacaoPapel.objects.create(
            papel=papel, modulo=MODULO_GERIR,
            item=HAB_GERIR_HABILITAR_USUARIO_PROCESSOS, ativo=True,
        )
        return user

    def _equipe(self, nome, *membros, ativo=True):
        equipe = Equipe.objects.create(nome=nome, ativo=ativo)
        for membro in membros:
            MembroEquipe.objects.create(usuario=membro, equipe=equipe, ativo=True)
        return equipe

    def _adicionar(self, processo, equipe, usuarios):
        return self.client.post(
            f"/processos/{processo.pk}/integrantes/equipe/adicionar/",
            {"equipe": equipe.pk, "usuarios": [u.pk for u in usuarios]},
            HTTP_HOST=self.http_host,
        )


class TestAdicionarEquipeComoAtalho(EquipeAtalhoIntegrantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_processos_atalho"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_atalho")
        self.gestor = self._gestor()
        self.ana = self._user("ana_atalho")
        self.beto = self._user("beto_atalho")
        self.caio = self._user("caio_atalho")
        self.equipe = self._equipe("Contabilidade", self.ana, self.beto)
        self.processo = Processo.objects.create(
            titulo="Processo Atalho", responsavel=self.responsavel, status="ativo"
        )
        self.client.force_login(self.gestor)

    def test_desmarcar_um_membro_inclui_todos_menos_ele(self):
        r = self._adicionar(self.processo, self.equipe, [self.ana])
        self.assertRedirects(
            r, f"/processos/{self.processo.pk}/", fetch_redirect_response=False
        )
        self.assertEqual(list(self.processo.integrantes_habilitados.all()), [self.ana])

    def test_nada_fica_ligado_a_equipe_depois(self):
        self._adicionar(self.processo, self.equipe, [self.ana, self.beto])
        novo = self._user("novo_atalho")
        MembroEquipe.objects.create(usuario=novo, equipe=self.equipe, ativo=True)
        MembroEquipe.objects.filter(usuario=self.ana, equipe=self.equipe).delete()
        MembroEquipe.objects.filter(usuario=self.beto, equipe=self.equipe).update(ativo=False)
        self.assertEqual(
            set(self.processo.integrantes_habilitados.all()), {self.ana, self.beto}
        )

    def test_varias_equipes_sem_duplicar(self):
        outra = self._equipe("Cível", self.beto, self.caio)
        self._adicionar(self.processo, self.equipe, [self.ana, self.beto])
        self._adicionar(self.processo, outra, [self.beto, self.caio])
        self.assertEqual(
            sorted(self.processo.integrantes_habilitados.values_list("username", flat=True)),
            ["ana_atalho", "beto_atalho", "caio_atalho"],
        )

    def test_remocao_individual_nao_reaparece(self):
        self._adicionar(self.processo, self.equipe, [self.ana, self.beto])
        self.client.post(
            f"/processos/{self.processo.pk}/integrantes/{self.ana.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(list(self.processo.integrantes_habilitados.all()), [self.beto])

    def test_nao_altera_responsavel_principal(self):
        self._adicionar(self.processo, self.equipe, [self.ana])
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.responsavel_id, self.responsavel.pk)

    def test_sem_selecao_nao_faz_nada(self):
        r = self._adicionar(self.processo, self.equipe, [])
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.processo.integrantes_habilitados.exists())

    def test_usuario_fora_da_equipe_informada_e_rejeitado(self):
        r = self._adicionar(self.processo, self.equipe, [self.ana, self.caio])
        self.assertEqual(r.status_code, 404)
        self.assertFalse(self.processo.integrantes_habilitados.exists())

    def test_membro_inativo_da_equipe_e_rejeitado(self):
        MembroEquipe.objects.filter(usuario=self.beto, equipe=self.equipe).update(ativo=False)
        r = self._adicionar(self.processo, self.equipe, [self.beto])
        self.assertEqual(r.status_code, 404)

    def test_equipe_inativa_e_rejeitada(self):
        self.equipe.ativo = False
        self.equipe.save()
        r = self._adicionar(self.processo, self.equipe, [self.ana])
        self.assertEqual(r.status_code, 404)

    def test_usuario_sem_acesso_a_processos_e_rejeitado(self):
        sem_acesso = self._user("sem_acesso_atalho", com_processos=False)
        MembroEquipe.objects.create(usuario=sem_acesso, equipe=self.equipe, ativo=True)
        r = self._adicionar(self.processo, self.equipe, [sem_acesso])
        self.assertEqual(r.status_code, 404)

    def test_sem_habilitacao_e_negado_mesmo_com_post_direto(self):
        self.client.force_login(self.responsavel)
        r = self._adicionar(self.processo, self.equipe, [self.ana])
        self.assertEqual(r.status_code, 403)
        self.assertFalse(self.processo.integrantes_habilitados.exists())

    def test_url_de_remover_equipe_nao_existe_mais(self):
        r = self.client.post(
            f"/processos/{self.processo.pk}/integrantes/equipe/{self.equipe.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 404)


class TestDetalheIntegrantesEquipeAtalho(EquipeAtalhoIntegrantesBase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0028_processos_detalhe"

    def setUp(self):
        super().setUp()
        self.responsavel = self._user("responsavel_detalhe_atalho")
        self.gestor = self._gestor("gestor_detalhe_atalho")
        self.ana = self._user("ana_detalhe_atalho")
        self.processo = Processo.objects.create(
            titulo="Processo Detalhe Atalho", responsavel=self.responsavel, status="ativo"
        )
        self.client.force_login(self.gestor)

    def _detalhe(self):
        return self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)

    def test_rotulos_e_ausencia_de_equipes_vinculadas(self):
        self._equipe("Contabilidade", self.ana)
        r = self._detalhe()
        self.assertContains(r, "Adicionar pessoa")
        self.assertContains(r, "Adicionar equipe")
        self.assertContains(r, "Adicionar selecionados")
        self.assertNotContains(r, "Equipes vinculadas")

    def test_sem_equipe_cadastrada_mostra_aviso(self):
        self.assertContains(self._detalhe(), "Nenhuma equipe cadastrada ainda")

    def test_equipe_inativa_nao_e_oferecida(self):
        self._equipe("Equipe Antiga", self.ana, ativo=False)
        r = self._detalhe()
        self.assertContains(r, "Nenhuma equipe cadastrada ainda")
        self.assertNotContains(r, "Equipe Antiga")

    def test_dados_da_lista_trazem_membros_e_presentes(self):
        equipe = self._equipe("Contabilidade", self.ana)
        self.processo.integrantes_habilitados.add(self.ana)
        r = self._detalhe()
        dados = r.context["equipe_atalho"]
        self.assertEqual(dados["presentes"], [self.ana.pk])
        self.assertEqual(
            dados["equipes"][str(equipe.pk)]["membros"],
            [{"id": self.ana.pk, "nome": "ana_detalhe_atalho"}],
        )
        json.dumps(dados)

    def test_usuario_sem_habilitacao_nao_ve_a_lista(self):
        self._equipe("Contabilidade", self.ana)
        self.client.force_login(self.responsavel)
        r = self._detalhe()
        self.assertNotContains(r, "Adicionar equipe")
