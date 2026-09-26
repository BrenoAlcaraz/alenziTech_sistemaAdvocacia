"""
Honorário sucumbencial calculado (PDR-0029): valor-base por percentual ou
valor fixo, correção por devedor/índice com taxa informada à mão, êxito
contratual e total sempre recalculado.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase
from django.utils import timezone

from apps.accounts.models import PapelAcesso, PerfilUsuario, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import MODULO_FINANCEIRO, NIVEL_DADOS_TODOS
from apps.clientes.models import Cliente
from apps.financeiro.forms import HonorarioForm
from apps.financeiro.models import Honorario
from apps.financeiro.services import _somar_meses, calcular_honorario_sucumbencial
from apps.processos.models import Processo


class HonorarioSucumbencialBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        dominio = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = dominio.domain if dominio else "localhost"
        self.user = User.objects.create_user(username="hon_suc", password="testpass")
        PerfilUsuario.objects.filter(user=self.user).update(is_admin_escritorio=True)
        papel = PapelAcesso.objects.create(nome="Papel Hon Suc", ativo=True)
        UsuarioPapel.objects.create(usuario=self.user, papel=papel, ativo=True)
        PermissaoPapel.objects.create(
            papel=papel, modulo=MODULO_FINANCEIRO, ativo=True, nivel=NIVEL_DADOS_TODOS,
        )
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(nome_razao_social="CLIENTE H", tipo="PF", responsavel=self.user)
        self.processo = Processo.objects.create(criado_por=self.user, titulo="Proc H")
        self.processo.clientes.add(self.cliente)
        self.hoje = timezone.localdate()

    def _atras(self, meses):
        return _somar_meses(self.hoje, -meses)

    def _honorario(self, **kw):
        dados = {
            "tipo": "sucumbencial", "valor_estimado": Decimal("1"), "forma_condenacao": "percentual",
            "percentual": Decimal("10"), "valor_condenacao": Decimal("100000"), "devedor_tipo": "pessoa",
            "indice_correcao": "inpc", "taxa_indice_mensal": Decimal("0.5"),
            "data_correcao": self._atras(6), "data_juros": self._atras(3),
            "processo": self.processo, "cliente": self.cliente,
        }
        dados.update(kw)
        return Honorario.objects.create(**dados)


class TestCalculo(HonorarioSucumbencialBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_suc_calculo"

    def test_pessoa_corrige_pelo_indice_e_soma_juros_de_um_por_cento(self):
        # 10.000 + 0,5% × 6 meses + 1% × 3 meses
        calculo = calcular_honorario_sucumbencial(self._honorario(), self.hoje)
        self.assertEqual(calculo["sucumbencia"], Decimal("10600.00"))
        self.assertEqual(calculo["exito"], Decimal("0.00"))
        self.assertEqual(calculo["total"], Decimal("10600.00"))

    def test_ente_estatal_usa_so_a_taxa_sem_juros(self):
        h = self._honorario(
            devedor_tipo="ente_estatal", indice_correcao="selic", taxa_indice_mensal=Decimal("1"),
            data_correcao=self._atras(12), data_juros=None,
        )
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("11200.00"))

    def test_valor_fixo_como_base(self):
        h = self._honorario(forma_condenacao="fixo", percentual=None, valor_condenacao=None,
                            valor_fixo=Decimal("5000"), taxa_indice_mensal=Decimal("0"), data_juros=None)
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("5000.00"))

    def test_exito_incide_sobre_o_valor_ganho_ja_corrigido(self):
        h = self._honorario(
            exito_percentual=Decimal("20"), exito_valor_ganho=Decimal("50000"),
            exito_data_correcao=self._atras(6),
        )
        calculo = calcular_honorario_sucumbencial(h, self.hoje)
        # ganho corrigido = 50.000 + 0,5%×6 + 1%×6 = 54.500 → 20% = 10.900
        self.assertEqual(calculo["exito"], Decimal("10900.00"))
        self.assertEqual(calculo["total"], Decimal("21500.00"))

    def test_sem_data_nao_ha_correcao(self):
        h = self._honorario(data_correcao=None, data_juros=None)
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("10000.00"))

    def test_o_total_cresce_com_o_tempo_sem_editar_nada(self):
        h = self._honorario()
        depois = calcular_honorario_sucumbencial(h, _somar_meses(self.hoje, 2))["total"]
        antes = calcular_honorario_sucumbencial(h, self.hoje)["total"]
        self.assertGreater(depois, antes)


class TestFormulario(HonorarioSucumbencialBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_suc_form"

    def _dados(self, **kw):
        dados = {
            "tipo": "sucumbencial", "processo": self.processo.pk, "forma_condenacao": "percentual",
            "percentual": "10", "valor_condenacao": "100000", "devedor_tipo": "pessoa",
            "indice_correcao": "inpc", "taxa_indice_mensal": "0.5",
            "data_correcao": self._atras(6).isoformat(), "data_juros": self._atras(3).isoformat(),
        }
        dados.update(kw)
        return dados

    def test_sucumbencial_valido_grava_total_como_valor_estimado_e_deriva_cliente(self):
        form = HonorarioForm(data=self._dados())
        self.assertTrue(form.is_valid(), form.errors)
        h = form.save()
        self.assertEqual(h.valor_estimado, Decimal("10600.00"))
        self.assertEqual(h.cliente, self.cliente)

    def test_sucumbencial_exige_processo(self):
        form = HonorarioForm(data=self._dados(processo=""))
        self.assertFalse(form.is_valid())
        self.assertIn("processo", form.errors)

    def test_percentual_exige_valor_da_causa(self):
        form = HonorarioForm(data=self._dados(valor_condenacao=""))
        self.assertFalse(form.is_valid())
        self.assertIn("valor_condenacao", form.errors)

    def test_pessoa_exige_data_de_juros_e_indice(self):
        form = HonorarioForm(data=self._dados(data_juros="", indice_correcao=""))
        self.assertFalse(form.is_valid())
        self.assertIn("data_juros", form.errors)
        self.assertIn("indice_correcao", form.errors)

    def test_ente_estatal_fixa_selic_e_descarta_juros(self):
        form = HonorarioForm(data=self._dados(devedor_tipo="ente_estatal", indice_correcao="", data_juros=""))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["indice_correcao"], "selic")
        self.assertIsNone(form.cleaned_data["data_juros"])

    def test_sucumbencia_nova_nao_grava_exito_embutido(self):
        form = HonorarioForm(data=self._dados(exito_percentual="20", exito_valor_ganho="1"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["exito_percentual"])

    def test_exito_embutido_de_registro_anterior_e_preservado_ao_editar(self):
        h = self._honorario(
            exito_percentual=Decimal("20"), exito_valor_ganho=Decimal("50000"),
            exito_data_correcao=self._atras(6),
        )
        form = HonorarioForm(data=self._dados(), instance=h)
        self.assertTrue(form.is_valid(), form.errors)
        h = form.save()
        self.assertEqual(h.exito_percentual, Decimal("20"))
        self.assertEqual(h.exito_valor_ganho, Decimal("50000"))

    def test_tipo_simples_continua_exigindo_valor_estimado_e_ignora_calculo(self):
        form = HonorarioForm(data={"tipo": "contratual", "percentual": "10"})
        self.assertFalse(form.is_valid())
        self.assertIn("valor_estimado", form.errors)
        form = HonorarioForm(data={"tipo": "contratual", "valor_estimado": "900", "percentual": "10"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["percentual"])


class TestTelas(HonorarioSucumbencialBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_suc_telas"

    def test_formulario_novo_abre(self):
        r = self.client.get("/financeiro/honorarios/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Forma da sucumbência")

    def test_lista_mostra_total_recalculado_e_pendente(self):
        h = self._honorario()
        h.valor_recebido = Decimal("600")
        h.save()
        r = self.client.get("/financeiro/honorarios/", HTTP_HOST=self.http_host)
        item = r.context["honorarios"][0]
        self.assertEqual(item.valor_total_exibido, Decimal("10600.00"))
        self.assertEqual(item.valor_pendente_hoje, Decimal("10000.00"))

    def test_confirmar_recebimento_vem_preenchido_com_o_total_calculado(self):
        h = self._honorario()
        r = self.client.get(
            f"/financeiro/honorarios/{h.pk}/confirmar-recebimento/", HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.context["form"].initial["valor_efetivo"], Decimal("10600.00"))
