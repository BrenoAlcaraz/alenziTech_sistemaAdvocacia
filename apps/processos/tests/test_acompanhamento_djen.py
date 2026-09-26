"""
Acompanhamento DJEN (PDR-0037, specs/sincronizacao-andamentos-datajud-djen.md):
publicação vira andamento "Intimação" sugerido com prazo calculado ou "a
definir"; só prazo de nosso cliente vai para a Agenda; primeira consulta
só avisa; o job é idempotente e isola falhas; confirmar/rejeitar/editar.
"""

from datetime import date, datetime
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.agenda.models import ItemAgenda
from apps.notificacoes.models import Notificacao
from apps.processos.acompanhamento import (
    executar_acompanhamento,
    processos_acompanhados,
    situacao_do_acompanhamento,
)
from apps.processos.djen import Advogado, Comunicacao, ErroDjen
from apps.processos.models import (
    AcompanhamentoProcesso,
    ComunicacaoDjen,
    ExecucaoAcompanhamento,
    MovimentacaoProcessual,
    ParteProcesso,
    Processo,
)

NUMERO = "4001054-83.2026.8.26.0595"
HOJE = date(2026, 10, 2)
TEXTO_15_DIAS = "<p>Intime-se para, no prazo de 15 (quinze) dias, manifestar-se.</p>"
NOSSA_OAB = Advogado(nome="Dono", oab="0123456", uf="SP")
OAB_ALHEIA = Advogado(nome="Outro", oab="999999", uf="RJ")


def sem_datajud(numero):
    """DataJud fora destes testes (coberto em test_acompanhamento_datajud)."""
    return None


def comunicacao(id, *, texto=TEXTO_15_DIAS, data=date(2026, 10, 1), destinatarios=("FULANO",),
                advogados=(NOSSA_OAB,), ativo=True):
    return Comunicacao(
        id=id, hash=f"h{id}", data_disponibilizacao=data, tipo="Intimação", texto=texto,
        link=f"https://djen.exemplo/{id}", ativo=ativo, orgao="1ª Vara",
        destinatarios=tuple(destinatarios), advogados=tuple(advogados),
    )


class AcompanhamentoBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.dono = User.objects.create_user("dono_djen", password="testpass")
        PerfilUsuario.objects.filter(user=self.dono).update(oab_numero="123.456", oab_uf="sp")
        self.processo = Processo.objects.create(responsavel=self.dono, titulo="Processo DJEN", numero=NUMERO)

    def _ja_acompanhado(self, processo=None, desde=date(2026, 9, 30)):
        AcompanhamentoProcesso.objects.create(processo=processo or self.processo, djen_consultado_ate=desde)

    def _rodar(self, comunicacoes, hoje=HOJE):
        buscar = mock.Mock(return_value=list(comunicacoes))
        return executar_acompanhamento(hoje, buscar=buscar, buscar_datajud=sem_datajud), buscar

    def _andamentos(self):
        return MovimentacaoProcessual.objects.filter(processo=self.processo, sugerido=True)


class TestSelecaoDeProcessos(AcompanhamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "djen_selecao"

    def test_acompanha_so_numero_cnj_valido_fora_de_arquivado_e_segredo(self):
        Processo.objects.create(responsavel=self.dono, titulo="Arq", numero=NUMERO, status="arquivado")
        Processo.objects.create(responsavel=self.dono, titulo="Seg", numero=NUMERO, segredo_justica=True)
        Processo.objects.create(responsavel=self.dono, titulo="Inválido", numero="123")
        suspenso = Processo.objects.create(responsavel=self.dono, titulo="Susp", numero=NUMERO, status="suspenso")

        self.assertEqual(set(processos_acompanhados()), {self.processo, suspenso})

    def test_segredo_de_justica_mostra_aviso_fixo(self):
        self.processo.segredo_justica = True
        self.processo.save()
        self.client.force_login(self.dono)
        papel = PapelAcesso.objects.create(nome="Papel DJEN")
        UsuarioPapel.objects.create(usuario=self.dono, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)

        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Acompanhamento automático indisponível (segredo de justiça). Acompanhe manualmente.")


class TestPrimeiraConsulta(AcompanhamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "djen_primeira"

    def test_nao_importa_historico_e_so_avisa_publicacao_recente(self):
        _, buscar = self._rodar([comunicacao(1)])

        numero, inicio, fim = buscar.call_args.args
        self.assertEqual((numero, inicio, fim), ("40010548320268260595", date(2026, 9, 17), HOJE))
        self.assertFalse(self._andamentos().exists())
        self.assertTrue(ComunicacaoDjen.objects.get(hash="h1").anterior_ao_acompanhamento)
        self.assertEqual(Notificacao.objects.filter(destinatario=self.dono).count(), 1)

        # Segunda execução no mesmo dia: nada novo.
        self._rodar([comunicacao(1)])
        self.assertFalse(self._andamentos().exists())
        self.assertEqual(Notificacao.objects.filter(destinatario=self.dono).count(), 1)


class TestPublicacaoViraAndamentoSugerido(AcompanhamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "djen_andamento"

    def test_intimacao_ao_escritorio_gera_prazo_calculado_na_agenda(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1)])

        andamento = self._andamentos().get()
        self.assertEqual(andamento.tipo, "intimacao")
        self.assertEqual(andamento.fonte, "djen")
        self.assertEqual(andamento.data_prazo, date(2026, 10, 26))
        self.assertTrue(andamento.prazo_calculado)
        self.assertEqual(andamento.prazo_de, "nosso_cliente")
        item = ItemAgenda.objects.get(movimentacao_origem=andamento)
        self.assertEqual(item.responsavel, self.dono)
        self.assertTrue(item.sugerido)
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.prazo_proximo, date(2026, 10, 26))
        self.assertEqual(AcompanhamentoProcesso.objects.get().djen_consultado_ate, HOJE)

    def test_intimacao_so_a_outra_parte_nao_vai_para_a_agenda(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, advogados=[OAB_ALHEIA])])

        andamento = self._andamentos().get()
        self.assertEqual(andamento.prazo_de, "outra_parte")
        self.assertEqual(andamento.data_prazo, date(2026, 10, 26))
        self.assertFalse(ItemAgenda.objects.exists())
        self.processo.refresh_from_db()
        self.assertIsNone(self.processo.prazo_proximo)

    def test_casos_de_prazo_a_definir_sem_item_na_agenda(self):
        penal = Processo.objects.create(
            responsavel=self.dono, titulo="Penal", numero="0000001-68.2026.8.26.0100", area_direito="CRIMINAL",
        )
        self._ja_acompanhado()
        self._ja_acompanhado(penal)
        casos = {
            self.processo: [
                comunicacao(1, texto="Cite-se."),
                comunicacao(2, texto="Réplica em 15 dias; após, 10 dias ao réu."),
                comunicacao(3, texto="Cumpra-se em 48 horas."),
                comunicacao(4, advogados=[]),
            ],
            penal: [comunicacao(5)],
        }
        buscar = mock.Mock(side_effect=lambda numero, *_: next(
            v for p, v in casos.items() if p.numero.replace("-", "").replace(".", "") == numero
        ))
        executar_acompanhamento(HOJE, buscar=buscar, buscar_datajud=sem_datajud)

        andamentos = MovimentacaoProcessual.objects.filter(sugerido=True)
        self.assertEqual(andamentos.count(), 5)
        self.assertTrue(all(a.prazo_a_definir and a.data_prazo is None for a in andamentos))
        sem_advogado = andamentos.get(link__endswith="/4")
        self.assertEqual(sem_advogado.prazo_de, "nosso_cliente")
        self.assertFalse(ItemAgenda.objects.exists())

    def test_dias_corridos_e_prazo_em_dobro(self):
        ParteProcesso.objects.create(processo=self.processo, papel="reu", nome="Município de São Paulo", prazo_em_dobro=True)
        self._ja_acompanhado()
        self._rodar([
            comunicacao(1, texto="Prazo de 3 dias corridos.", data=date(2026, 10, 1)),
            comunicacao(2, destinatarios=["MUNICIPIO DE SAO PAULO"], data=date(2026, 9, 30)),
        ])

        corridos = self._andamentos().get(link__endswith="/1")
        self.assertEqual(corridos.data_prazo, date(2026, 10, 5))
        dobrado = self._andamentos().get(link__endswith="/2")
        self.assertTrue(dobrado.prazo_dobrado)
        self.assertEqual((dobrado.prazo_dias, dobrado.prazo_dias_dobrado), (15, 30))
        # Disponibilizada 30/09 → publicada 01/10 → 30 dias úteis.
        self.assertEqual(dobrado.data_prazo, date(2026, 11, 16))

    def test_publicacoes_identicas_por_destinatario_viram_um_andamento(self):
        self._ja_acompanhado()
        self._rodar([
            comunicacao(1, destinatarios=["FULANO"]),
            comunicacao(2, destinatarios=["BELTRANO"]),
        ])

        andamento = self._andamentos().get()
        self.assertIn("FULANO", andamento.destinatarios)
        self.assertIn("BELTRANO", andamento.destinatarios)
        self.assertEqual(ComunicacaoDjen.objects.filter(movimentacao=andamento).count(), 2)

    def test_publicacao_cancelada_antes_de_importar_e_ignorada(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, ativo=False)])
        self.assertFalse(self._andamentos().exists())


class TestIdempotenciaEIsolamento(AcompanhamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "djen_idempotencia"

    def test_rodar_duas_vezes_nao_duplica_nada(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1)])
        self._rodar([comunicacao(1), comunicacao(2, destinatarios=["BELTRANO"])])

        self.assertEqual(self._andamentos().count(), 1)
        self.assertEqual(ItemAgenda.objects.count(), 1)
        self.assertEqual(ComunicacaoDjen.objects.count(), 2)
        self.assertEqual(Notificacao.objects.filter(destinatario=self.dono).count(), 2)

    def test_andamento_rejeitado_nao_volta(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1)])
        self._andamentos().get().delete()

        self._rodar([comunicacao(1)])
        self.assertFalse(self._andamentos().exists())

    def test_falha_num_processo_nao_interrompe_os_demais_e_aparece_na_faixa(self):
        outro = Processo.objects.create(responsavel=self.dono, titulo="Outro", numero="0000001-68.2026.8.26.0100")
        self._ja_acompanhado()
        self._ja_acompanhado(outro)

        def buscar(numero, *_):
            if numero == "40010548320268260595":
                raise ErroDjen("fora do ar")
            return [comunicacao(9)]

        execucao = executar_acompanhamento(HOJE, buscar=buscar, buscar_datajud=sem_datajud)

        self.assertEqual(execucao.falhas, 1)
        self.assertTrue(MovimentacaoProcessual.objects.filter(processo=outro, sugerido=True).exists())
        self.assertTrue(situacao_do_acompanhamento(execucao.iniciada_em)["falhou_hoje"])

    def test_faixa_mostra_ultima_atualizacao_sem_falha(self):
        execucao, _ = self._rodar([])
        situacao = situacao_do_acompanhamento(execucao.iniciada_em)
        self.assertEqual(situacao["ultima_atualizacao"], execucao.concluida_em)
        self.assertFalse(situacao["falhou_hoje"])

    def test_sem_execucao_hoje_depois_das_7h_e_falha(self):
        ExecucaoAcompanhamento.objects.create(
            iniciada_em=timezone.make_aware(datetime(2026, 10, 1, 6)),
            concluida_em=timezone.make_aware(datetime(2026, 10, 1, 6, 5)),
        )
        self.assertTrue(situacao_do_acompanhamento(timezone.make_aware(datetime(2026, 10, 2, 8)))["falhou_hoje"])
        self.assertFalse(situacao_do_acompanhamento(timezone.make_aware(datetime(2026, 10, 2, 6)))["falhou_hoje"])

    def test_comando_roda_no_schema_de_cada_escritorio_e_isola_falha(self):
        schemas = []

        def executar(hoje):
            schemas.append(connection.schema_name)
            raise RuntimeError("falha do escritório")

        with mock.patch("apps.processos.management.commands.acompanhar_processos.executar_acompanhamento", executar):
            call_command("acompanhar_processos", stdout=mock.Mock(), stderr=mock.Mock())

        self.assertIn(self.tenant.schema_name, schemas)
        self.assertNotIn("public", schemas)


class TestAcoesSobreSugerido(AcompanhamentoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "djen_acoes"

    def setUp(self):
        super().setUp()
        for usuario in [self.dono]:
            papel = PapelAcesso.objects.create(nome=f"Papel {usuario.username}")
            UsuarioPapel.objects.create(usuario=usuario, papel=papel, ativo=True)
            PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self._ja_acompanhado()
        self._rodar([comunicacao(1)])
        self.andamento = self._andamentos().get()
        self.url = f"/processos/{self.processo.pk}/andamentos/{self.andamento.pk}"
        self.client.force_login(self.dono)

    def test_detalhe_mostra_selo_fonte_e_aviso_de_calculo(self):
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Sugerido")
        self.assertContains(r, "Fonte: DJEN")
        self.assertContains(r, "Calculado automaticamente, sem considerar feriado local ou suspensão do tribunal — confirme.")

    def test_confirmar_tira_o_selo(self):
        r = self.client.post(f"{self.url}/confirmar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302)
        self.andamento.refresh_from_db()
        self.assertFalse(self.andamento.sugerido)
        self.assertTrue(ItemAgenda.objects.filter(movimentacao_origem=self.andamento).exists())

    def test_rejeitar_apaga_andamento_prazo_e_item_da_agenda(self):
        self.client.post(f"{self.url}/rejeitar/", HTTP_HOST=self.http_host)
        self.assertFalse(MovimentacaoProcessual.objects.filter(pk=self.andamento.pk).exists())
        self.assertFalse(ItemAgenda.objects.exists())
        self.processo.refresh_from_db()
        self.assertIsNone(self.processo.prazo_proximo)

    def test_editar_reclassifica_para_outra_parte_e_tira_da_agenda(self):
        r = self.client.get(f"{self.url}/editar/", HTTP_HOST=self.http_host)
        self.assertContains(r, "Editar andamento sugerido")
        # Anexar documento segue a habilitação própria, que este usuário não tem.
        self.assertNotContains(r, "Anexar o documento real")
        self.client.post(f"{self.url}/editar/", {
            "tipo": "intimacao", "descricao": "Intimação", "data_prazo": "2026-10-27", "prazo_de": "outra_parte",
        }, HTTP_HOST=self.http_host)

        self.andamento.refresh_from_db()
        self.assertEqual(self.andamento.prazo_de, "outra_parte")
        self.assertFalse(self.andamento.prazo_calculado)
        self.assertTrue(self.andamento.sugerido)
        self.assertFalse(ItemAgenda.objects.exists())

    def test_quem_nao_e_responsavel_nem_admin_nao_altera(self):
        estranho = User.objects.create_user("estranho_djen", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel estranho")
        UsuarioPapel.objects.create(usuario=estranho, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self.client.force_login(estranho)

        for acao in ["confirmar", "rejeitar", "editar"]:
            with self.subTest(acao=acao):
                r = self.client.post(f"{self.url}/{acao}/", HTTP_HOST=self.http_host)
                self.assertEqual(r.status_code, 404)
        self.andamento.refresh_from_db()
        self.assertTrue(self.andamento.sugerido)

    def test_andamento_confirmado_nao_passa_pelas_acoes_de_sugerido(self):
        MovimentacaoProcessual.objects.filter(pk=self.andamento.pk).update(sugerido=False)
        r = self.client.post(f"{self.url}/rejeitar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 404)
        self.assertTrue(MovimentacaoProcessual.objects.filter(pk=self.andamento.pk).exists())
