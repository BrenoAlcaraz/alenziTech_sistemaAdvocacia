"""
Avisos complementares do acompanhamento (specs/sincronizacao-andamentos-datajud-djen.md):
"prazo a definir" cobrado 1× por dia até ser resolvido; publicação
cancelada no DJEN depois de importada só avisa; número CNJ citado e não
cadastrado vira sugestão na aba Apensos. Rodar o job de novo não repete
aviso.
"""

from datetime import date, timedelta

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import HAB_PROCESSOS_CRIAR, MODULO_PROCESSOS, NIVEL_TODOS
from apps.notificacoes.models import Notificacao
from apps.processos.acompanhamento import numeros_cnj_no_texto
from apps.processos.models import ComunicacaoDjen, MovimentacaoProcessual, NumeroCnjCitado, Processo
from apps.processos.tests.test_acompanhamento_djen import (
    HOJE,
    NUMERO,
    AcompanhamentoBase,
    comunicacao,
)

AMANHA = HOJE + timedelta(days=1)
SEM_PRAZO = "<p>Vista às partes.</p>"
CITADO = "1000001-51.2026.8.26.0100"


class AvisosBase(AcompanhamentoBase):
    def _avisos(self, trecho):
        return Notificacao.objects.filter(destinatario=self.dono, mensagem__contains=trecho).count()

    def _logar(self, *, pode_criar=False):
        papel = PapelAcesso.objects.create(nome="Papel avisos")
        UsuarioPapel.objects.create(usuario=self.dono, papel=papel, ativo=True)
        PermissaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, ativo=True, nivel=NIVEL_TODOS)
        if pode_criar:
            HabilitacaoPapel.objects.create(papel=papel, modulo=MODULO_PROCESSOS, item=HAB_PROCESSOS_CRIAR, ativo=True)
        self.client.force_login(self.dono)

    def _detalhe(self, aba="andamentos"):
        return self.client.get(f"/processos/{self.processo.pk}/?aba={aba}", HTTP_HOST=self.http_host)


class TestCobrancaDePrazoADefinir(AvisosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "avisos_prazo"

    def test_cobra_uma_vez_por_dia_ate_ser_resolvido(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, texto=SEM_PRAZO)])
        # No dia da importação o aviso do andamento sugerido já cobra.
        self._rodar([comunicacao(1, texto=SEM_PRAZO)])
        self.assertEqual(self._avisos("Prazo a definir"), 0)
        self.assertEqual(self._avisos("prazo a definir"), 1)

        self._rodar([], hoje=AMANHA)
        self._rodar([], hoje=AMANHA)
        self.assertEqual(self._avisos("Prazo a definir"), 1)

        andamento = self._andamentos().get()
        andamento.data_prazo = date(2026, 10, 20)
        andamento.prazo_a_definir = False
        andamento.save()
        self._rodar([], hoje=AMANHA + timedelta(days=1))
        self.assertEqual(self._avisos("Prazo a definir"), 1)

    def test_confirmar_sem_informar_data_nao_resolve(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, texto=SEM_PRAZO)])
        self._andamentos().update(sugerido=False)

        self._rodar([], hoje=AMANHA)
        self.assertEqual(self._avisos("Prazo a definir"), 1)

    def test_processo_arquivado_nao_e_cobrado(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, texto=SEM_PRAZO)])
        Processo.objects.filter(pk=self.processo.pk).update(status="arquivado")

        self._rodar([], hoje=AMANHA)
        self.assertEqual(self._avisos("Prazo a definir"), 0)


class TestPublicacaoCancelada(AvisosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "avisos_cancelada"

    def test_cancelada_depois_de_importada_so_avisa_uma_vez(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, destinatarios=("A",)), comunicacao(2, destinatarios=("B",))])
        andamento = self._andamentos().get()

        canceladas = [comunicacao(1, destinatarios=("A",), ativo=False), comunicacao(2, destinatarios=("B",), ativo=False)]
        _, buscar = self._rodar(canceladas, hoje=AMANHA)
        self._rodar(canceladas, hoje=AMANHA + timedelta(days=1))

        # A consulta volta o bastante para enxergar o cancelamento.
        self.assertEqual(buscar.call_args.args[1], AMANHA - timedelta(days=30))
        self.assertTrue(MovimentacaoProcessual.objects.filter(pk=andamento.pk).exists())
        self.assertEqual(ComunicacaoDjen.objects.filter(cancelada_em=AMANHA).count(), 2)
        self.assertEqual(self._avisos("foi cancelada no DJEN"), 1)

        self._logar()
        self.assertContains(self._detalhe(), "Publicação cancelada no DJEN depois de importada")

    def test_janela_de_cancelamento_nao_importa_publicacao_antiga(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, data=date(2026, 9, 20))])
        self.assertFalse(self._andamentos().exists())

    def test_cancelada_nunca_importada_e_ignorada(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, ativo=False)])
        self.assertEqual(self._avisos("cancelada"), 0)


class TestNumeroCnjCitado(AvisosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "avisos_citado"

    def test_extrai_numeros_validos_com_e_sem_mascara(self):
        texto = f"Apenso ao {CITADO}, ref. 10000015120268260100 e {NUMERO}; inválido 1000001-52.2026.8.26.0100."
        self.assertEqual(numeros_cnj_no_texto(texto), ["10000015120268260100", "40010548320268260595"])

    def test_sugere_citado_nao_cadastrado_sem_criar_vinculo(self):
        # Arquivado: continua cadastrado, mas fora do job (o mock serviria a ele a mesma publicação).
        cadastrado = Processo.objects.create(
            responsavel=self.dono, titulo="Outro", numero="1000002-36.2026.8.26.0100", status="arquivado",
        )
        texto = f"<p>Recurso {CITADO} e incidente {cadastrado.numero} do processo {NUMERO}.</p>"
        self._ja_acompanhado()
        self._rodar([comunicacao(1, texto=texto)])
        self._rodar([comunicacao(1, texto=texto)])

        self.assertEqual(list(NumeroCnjCitado.objects.values_list("numero", flat=True)), ["10000015120268260100"])
        self.assertFalse(self.processo.vinculos_apensos_como_menor.exists())
        self.assertFalse(self.processo.vinculos_apensos_como_maior.exists())

        self._logar(pode_criar=True)
        r = self._detalhe("apensos")
        self.assertContains(r, f"Número {CITADO} citado, não cadastrado")
        self.assertContains(r, "/processos/novo/?numero=1000001-51.2026.8.26.0100")

        r = self.client.get(f"/processos/novo/?numero={CITADO}", HTTP_HOST=self.http_host)
        self.assertContains(r, f'value="{CITADO}"')

        # Depois de cadastrado, a sugestão some.
        Processo.objects.create(responsavel=self.dono, titulo="Recurso", numero="10000015120268260100")
        self.assertNotContains(self._detalhe("apensos"), "citado, não cadastrado")

    def test_sem_permissao_de_criar_nao_mostra_atalho(self):
        self._ja_acompanhado()
        self._rodar([comunicacao(1, texto=f"<p>Recurso {CITADO}.</p>")])
        self._logar()
        r = self._detalhe("apensos")
        self.assertContains(r, f"Número {CITADO} citado, não cadastrado")
        self.assertNotContains(r, "cadastrar e vincular")
