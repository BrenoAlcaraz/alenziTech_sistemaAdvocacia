"""
Acompanhamento DataJud (specs/sincronizacao-andamentos-datajud-djen.md):
movimento da lista de códigos relevantes vira andamento sugerido sem
prazo; código fora da lista ou de publicação não gera nada; mudança de
vara/grau informada pelo DataJud atualiza o processo e avisa; diferença
só de escrita não.
"""

from datetime import date, datetime, timezone as dt_timezone
from unittest import mock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_PROCESSOS, NIVEL_TODOS
from apps.notificacoes.models import Notificacao
from apps.processos import datajud
from apps.processos.acompanhamento import executar_acompanhamento, sincronizar_datajud
from apps.processos.datajud import ErroDatajud, Movimento, RegistroDatajud, alias_do_tribunal, buscar_processo
from apps.processos.djen import ErroDjen
from apps.processos.forms import AndamentoSugeridoForm
from apps.processos.models import AcompanhamentoProcesso, MovimentacaoProcessual, MovimentoDatajud, Processo

NUMERO = "4001054-83.2026.8.26.0595"
HOJE = date(2026, 10, 2)
VARA = "1ª VARA CÍVEL DE SERRA NEGRA"


def movimento(codigo, nome="Movimento", dia=1, complementos=()):
    return Movimento(
        codigo=codigo, nome=nome, data_hora=datetime(2026, 10, dia, 12, tzinfo=dt_timezone.utc),
        complementos=tuple(complementos),
    )


def registro(*movimentos, grau="G1", orgao=VARA):
    return RegistroDatajud(grau=grau, orgao_julgador=orgao, movimentos=tuple(movimentos))


# Ponto de partida: o processo já existia no DataJud com a distribuição.
DISTRIBUICAO = movimento(26, "Distribuição", dia=1)


class TestClienteDatajud(SimpleTestCase):
    def test_tribunal_deduzido_do_numero(self):
        self.assertEqual(alias_do_tribunal("40010548320268260595"), "tjsp")
        self.assertEqual(alias_do_tribunal("00000000020268070001"), "tjdft")
        self.assertEqual(alias_do_tribunal("00000000020265020001"), "trt2")
        self.assertEqual(alias_do_tribunal("00000000020264010001"), "trf1")
        self.assertIsNone(alias_do_tribunal("00000000020261000001"))  # STF

    @override_settings(DATAJUD_API_KEY="chave")
    def test_le_resposta_real_e_ignora_movimento_sem_codigo(self):
        resposta = {"hits": {"hits": [{"_source": {
            "grau": "G2",
            "orgaoJulgador": {"codigo": 70857, "nome": "10ª CÂMARA DE DIREITO PRIVADO"},
            "movimentos": [
                {"codigo": 92, "dataHora": "2024-12-03T00:00:00.000Z", "nome": "Publicação"},
                {"dataHora": "2025-11-15T09:38:31.000Z", "orgaoJulgador": {}},
                {"codigo": 60, "dataHora": "2024-12-04T10:00:00.000Z", "nome": "Expedição de documento",
                 "complementosTabelados": [{"descricao": "tipo_de_documento", "nome": "Alvará"}]},
            ],
        }}]}}
        with mock.patch.object(datajud, "_post", return_value=resposta) as post:
            registros = buscar_processo("40010548320268260595")

        self.assertEqual(post.call_args.args[0], "tjsp")
        [unico] = registros
        self.assertEqual((unico.grau, unico.orgao_julgador), ("G2", "10ª CÂMARA DE DIREITO PRIVADO"))
        self.assertEqual([m.codigo for m in unico.movimentos], [92, 60])
        self.assertEqual(unico.movimentos[1].complementos, ("Alvará",))

    @override_settings(DATAJUD_API_KEY="chave")
    def test_erro_de_sobrecarga_em_json_e_falha(self):
        with mock.patch.object(datajud, "_post", return_value={"error": {"type": "es_rejected_execution_exception"}}):
            with self.assertRaises(ErroDatajud):
                buscar_processo("40010548320268260595")

    @override_settings(DATAJUD_API_KEY="")
    def test_sem_chave_configurada_e_falha(self):
        with self.assertRaises(ErroDatajud):
            buscar_processo("40010548320268260595")


class DatajudBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.dono = User.objects.create_user("dono_datajud", password="testpass")
        self.processo = Processo.objects.create(
            responsavel=self.dono, titulo="Processo DataJud", numero=NUMERO, vara="1a vara civel",
        )

    def _sincronizar(self, *registros):
        return sincronizar_datajud(self.processo, buscar=mock.Mock(return_value=list(registros)))

    def _ja_acompanhado(self):
        self._sincronizar(registro(DISTRIBUICAO))
        Notificacao.objects.all().delete()

    def _sugeridos(self):
        return MovimentacaoProcessual.objects.filter(processo=self.processo, fonte="datajud", sugerido=True)

    def _avisos(self):
        return list(Notificacao.objects.filter(destinatario=self.dono).values_list("mensagem", flat=True))


class TestMovimentosDatajud(DatajudBase):
    @classmethod
    def get_test_schema_name(cls):
        return "datajud_movimentos"

    def test_primeira_vez_encontrado_so_registra_ponto_de_partida(self):
        criados = self._sincronizar(registro(DISTRIBUICAO, movimento(219, "Procedência")))

        self.assertEqual(criados, 0)
        self.assertFalse(self._sugeridos().exists())
        acompanhamento = AcompanhamentoProcesso.objects.get(processo=self.processo)
        self.assertTrue(acompanhamento.datajud_encontrado)
        self.assertEqual((acompanhamento.datajud_orgao_julgador, acompanhamento.datajud_grau), (VARA, "G1"))
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.vara, "1a vara civel")  # ponto de partida não altera o processo
        self.assertEqual(self._avisos(), [])

    def test_codigo_da_lista_gera_andamento_sugerido_sem_prazo(self):
        self._ja_acompanhado()
        despacho = movimento(11010, "Mero expediente", dia=2)

        # Repetido pelo DataJud (mesmo código e data) e duas execuções.
        self._sincronizar(registro(DISTRIBUICAO, despacho, despacho, movimento(219, "Procedência", dia=3)))
        self._sincronizar(registro(DISTRIBUICAO, despacho, movimento(219, "Procedência", dia=3)))

        andamentos = self._sugeridos().order_by("data")
        self.assertEqual(
            [(a.tipo, a.descricao) for a in andamentos],
            [("despacho", "Despacho: Mero expediente"), ("sentenca", "Sentença: Procedência")],
        )
        for andamento in andamentos:
            self.assertIsNone(andamento.data_prazo)
            self.assertFalse(andamento.prazo_a_definir)
        self.assertEqual(len(self._avisos()), 1)
        self.assertIn("2 andamento(s) sugerido(s) (DataJud)", self._avisos()[0])

    def test_codigo_fora_da_lista_ou_de_publicacao_nao_gera_nada(self):
        self._ja_acompanhado()

        self._sincronizar(registro(
            DISTRIBUICAO,
            movimento(51, "Conclusão", dia=2),
            movimento(123, "Remessa", dia=2),
            movimento(11383, "Ato ordinatório", dia=2),
            movimento(92, "Publicação", dia=3),
            movimento(1061, "Disponibilização no Diário da Justiça Eletrônico", dia=3),
            movimento(60, "Expedição de documento", dia=3, complementos=["Certidão"]),
        ))

        self.assertFalse(self._sugeridos().exists())
        self.assertEqual(self._avisos(), [])

    def test_codigo_mapeado_para_tipo_do_catalogo_ou_andamento(self):
        self._ja_acompanhado()

        self._sincronizar(
            registro(DISTRIBUICAO, movimento(12749, "de Instrução", dia=2)),
            registro(movimento(239, "Não-Provimento", dia=3), grau="G2", orgao=VARA),
            registro(movimento(60, "Expedição de documento", dia=4, complementos=["Alvará"]), orgao=VARA),
        )

        self.assertEqual(
            list(self._sugeridos().order_by("data").values_list("tipo", "descricao")),
            [
                ("andamento", "Audiência: de Instrução"),
                ("acordao", "Acórdão: Não-Provimento"),
                ("andamento", "Expedição de alvará: Expedição de documento (Alvará)"),
            ],
        )

    def test_baixa_e_arquivamento_geram_andamento_sem_mudar_status(self):
        self._ja_acompanhado()

        self._sincronizar(registro(
            DISTRIBUICAO, movimento(22, "Baixa Definitiva", dia=2), movimento(246, "Definitivo", dia=2),
        ))

        self.assertEqual(
            set(self._sugeridos().values_list("tipo", flat=True)), {"andamento", "arquivamento"},
        )
        self.processo.refresh_from_db()
        self.assertEqual(self.processo.status, "ativo")

    def test_area_penal_usa_o_catalogo_penal(self):
        self.processo.area_direito = "CRIMINAL"
        self.processo.save()
        self._ja_acompanhado()

        self._sincronizar(registro(DISTRIBUICAO, movimento(246, "Definitivo", dia=2)))

        self.assertEqual(self._sugeridos().get().tipo, "arquivamento_inquerito")

    def test_andamento_rejeitado_nao_volta(self):
        self._ja_acompanhado()
        sentenca = movimento(219, "Procedência", dia=2)
        self._sincronizar(registro(DISTRIBUICAO, sentenca))
        self._sugeridos().get().delete()

        self._sincronizar(registro(DISTRIBUICAO, sentenca))

        self.assertFalse(self._sugeridos().exists())
        self.assertTrue(MovimentoDatajud.objects.filter(processo=self.processo, chave=sentenca.chave).exists())

    def test_editar_sugerido_sem_equivalente_mantem_tipo_e_nao_pede_prazo(self):
        self._ja_acompanhado()
        self._sincronizar(registro(DISTRIBUICAO, movimento(22, "Baixa Definitiva", dia=2)))
        andamento = self._sugeridos().get()

        form = AndamentoSugeridoForm(
            {"tipo": "andamento", "descricao": "Baixa definitiva", "prazo_de": "nosso_cliente"},
            instance=andamento, processo=self.processo,
        )

        self.assertTrue(form.is_valid(), form.errors)
        andamento = form.save()
        self.assertEqual(andamento.tipo, "andamento")
        self.assertFalse(andamento.prazo_a_definir)


class TestDadosDoProcessoNoTribunal(DatajudBase):
    @classmethod
    def get_test_schema_name(cls):
        return "datajud_dados"

    def test_mudanca_de_vara_e_grau_atualiza_e_avisa(self):
        self._ja_acompanhado()

        self._sincronizar(
            registro(DISTRIBUICAO),
            registro(movimento(26, "Distribuição", dia=5), grau="G2", orgao="10ª CÂMARA DE DIREITO PRIVADO"),
        )

        self.processo.refresh_from_db()
        self.assertEqual(self.processo.vara, "10ª CÂMARA DE DIREITO PRIVADO")
        self.assertEqual(self.processo.instancia, "2ª Instância")
        [aviso] = self._avisos()
        self.assertIn("alterados no tribunal (DataJud)", aviso)
        self.assertIn("10ª CÂMARA DE DIREITO PRIVADO", aviso)

    def test_diferenca_so_de_escrita_nao_conta(self):
        self._ja_acompanhado()

        self._sincronizar(registro(DISTRIBUICAO, orgao="  1ª vara cível de   Serra Negra"))

        self.processo.refresh_from_db()
        # O usuário digitou diferente do DataJud; o DataJud não mudou.
        self.assertEqual(self.processo.vara, "1a vara civel")
        self.assertEqual(self._avisos(), [])


class TestNaoEncontradoEIsolamento(DatajudBase):
    @classmethod
    def get_test_schema_name(cls):
        return "datajud_isolamento"

    def _entrar(self):
        from apps.saas_tenants.models import Dominio
        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        papel = PapelAcesso.objects.create(nome="Papel DataJud")
        UsuarioPapel.objects.create(usuario=self.dono, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        self.client.force_login(self.dono)
        return dominio.domain if dominio else "localhost"

    def test_nao_encontrado_mostra_nota_e_busca_continua(self):
        host = self._entrar()
        self._sincronizar()

        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=host)
        self.assertContains(r, "Processo não encontrado no DataJud.")
        self.assertContains(r, "A busca continua nos dias seguintes.")

        # Encontrado depois: ponto de partida, sem histórico, e a nota some.
        self._sincronizar(registro(DISTRIBUICAO, movimento(219, "Procedência")))
        self.assertFalse(self._sugeridos().exists())
        r = self.client.get(f"/processos/{self.processo.pk}/", HTTP_HOST=host)
        self.assertNotContains(r, "Processo não encontrado no DataJud.")

    def test_tribunal_fora_do_datajud_nao_consulta(self):
        criados = sincronizar_datajud(self.processo, buscar=mock.Mock(return_value=None))

        self.assertEqual(criados, 0)
        self.assertFalse(AcompanhamentoProcesso.objects.filter(processo=self.processo).exists())

    def test_falha_de_uma_fonte_nao_interrompe_a_outra(self):
        def djen_fora_do_ar(*_):
            raise ErroDjen("fora do ar")

        execucao = executar_acompanhamento(
            HOJE, buscar=djen_fora_do_ar, buscar_datajud=mock.Mock(return_value=[registro(DISTRIBUICAO)]),
        )

        self.assertEqual(execucao.falhas, 1)
        self.assertIn("(DJEN)", execucao.erro)
        acompanhamento = AcompanhamentoProcesso.objects.get(processo=self.processo)
        self.assertTrue(acompanhamento.datajud_encontrado)
        # O DJEN continua sem ponto de partida: a próxima execução faz a
        # primeira consulta dele.
        self.assertIsNone(acompanhamento.djen_consultado_ate)

    def test_falha_do_datajud_e_contada(self):
        def datajud_fora_do_ar(_):
            raise ErroDatajud("fora do ar")

        execucao = executar_acompanhamento(HOJE, buscar=mock.Mock(return_value=[]), buscar_datajud=datajud_fora_do_ar)

        self.assertEqual(execucao.falhas, 1)
        self.assertIn("(DataJud)", execucao.erro)
        self.assertIsNotNone(AcompanhamentoProcesso.objects.get(processo=self.processo).djen_consultado_ate)
