"""
Honorários — formulário contratual/sucumbência e IPCA (PDR-0032).

Contratual: valor (único, parcelado, recorrente) e/ou êxito; parcelado e
recorrente geram lançamentos pendentes vinculados; êxito é só anotação.
Sucumbência: forma fixo/percentual/misto sobre a condenação, intervalos de
juros e correção, IPCA e aviso de êxito "pelo ganho" do mesmo processo.
"""

from decimal import Decimal

from django.utils import timezone

from apps.financeiro.forms import HonorarioForm
from apps.financeiro.models import Honorario, LancamentoFinanceiro
from apps.financeiro.services import (
    _somar_meses,
    calcular_honorario_sucumbencial,
    contratos_de_exito_pelo_ganho,
    gerar_lancamentos_do_honorario,
)
from apps.processos.models import Processo

from .test_honorario_sucumbencial import HonorarioSucumbencialBase


class ContratualBase(HonorarioSucumbencialBase):
    def _dados(self, **kw):
        dados = {
            "tipo": "contratual", "modalidade": "valor", "valor_estimado": "6000",
            "classificacao": "unica", "data_prevista": self.hoje.isoformat(),
        }
        dados.update(kw)
        return dados

    def _dados_parcelado(self, **kw):
        return self._dados(**{"classificacao": "parcelado", "numero_parcelas": "3", **kw})

    def _contratual(self, **kw):
        dados = {
            "tipo": "contratual", "modalidade": "valor", "valor_estimado": Decimal("6000"),
            "classificacao": "parcelado", "numero_parcelas": 3, "data_prevista": self.hoje,
            "processo": self.processo, "cliente": self.cliente,
        }
        dados.update(kw)
        return Honorario.objects.create(**dados)

    def _exito(self, **kw):
        dados = {
            "tipo": "contratual", "modalidade": "exito", "valor_estimado": Decimal("0"),
            "exito_percentual": Decimal("20"), "exito_base": "ganho",
            "processo": self.processo, "cliente": self.cliente,
        }
        dados.update(kw)
        return Honorario.objects.create(**dados)


class TestTiposDoFormulario(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_tipos"

    def test_novo_oferece_so_contratual_e_sucumbencia(self):
        tipos = [valor for valor, _ in HonorarioForm().fields["tipo"].choices]
        self.assertEqual(tipos, ["contratual", "sucumbencial"])

    def test_nao_cria_exito_nem_outro(self):
        for legado in ("exito", "outro"):
            form = HonorarioForm(data={"tipo": legado, "valor_estimado": "100"})
            self.assertFalse(form.is_valid())
            self.assertIn("tipo", form.errors)

    def test_registro_legado_segue_editavel_no_modelo_simples(self):
        h = Honorario.objects.create(tipo="exito", valor_estimado=Decimal("800"))
        form = HonorarioForm(data={"tipo": "exito", "valor_estimado": "900"}, instance=h)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().valor_estimado, Decimal("900"))

    def test_telas_abrem_com_registros_legados(self):
        legados = [
            Honorario.objects.create(tipo="exito", valor_estimado=Decimal("800")),
            Honorario.objects.create(tipo="outro", valor_estimado=Decimal("50")),
            Honorario.objects.create(tipo="contratual", valor_estimado=Decimal("2000")),
        ]
        self.assertEqual(self.client.get("/financeiro/honorarios/", HTTP_HOST=self.http_host).status_code, 200)
        for h in legados:
            r = self.client.get(f"/financeiro/honorarios/{h.pk}/editar/", HTTP_HOST=self.http_host)
            self.assertEqual(r.status_code, 200)

    def test_contratual_legado_sem_modalidade_edita_como_valor_unico(self):
        h = Honorario.objects.create(tipo="contratual", valor_estimado=Decimal("2000"))
        form = HonorarioForm(data={"tipo": "contratual", "valor_estimado": "2500"}, instance=h)
        self.assertTrue(form.is_valid(), form.errors)
        h = form.save()
        self.assertEqual((h.modalidade, h.classificacao), ("valor", "unica"))


class TestFormularioContratual(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_form"

    def test_valor_unico_valido_e_data_opcional(self):
        form = HonorarioForm(data=self._dados(data_prevista=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_valor_exige_o_valor(self):
        form = HonorarioForm(data=self._dados(valor_estimado=""))
        self.assertFalse(form.is_valid())
        self.assertIn("valor_estimado", form.errors)

    def test_parcelado_exige_ao_menos_duas_parcelas_e_data(self):
        form = HonorarioForm(data=self._dados_parcelado(numero_parcelas="1", data_prevista=""))
        self.assertFalse(form.is_valid())
        self.assertIn("numero_parcelas", form.errors)
        self.assertIn("data_prevista", form.errors)

    def test_recorrente_exige_periodicidade_mensal_ou_anual_e_duracao(self):
        form = HonorarioForm(data=self._dados(classificacao="recorrente"))
        self.assertFalse(form.is_valid())
        self.assertIn("periodicidade", form.errors)
        self.assertIn("duracao_tipo", form.errors)

    def test_recorrente_por_quantidade_exige_a_quantidade(self):
        form = HonorarioForm(data=self._dados(
            classificacao="recorrente", periodicidade="mensal", duracao_tipo="quantidade",
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("duracao_quantidade", form.errors)

    def test_recorrente_por_data_final_exige_data_depois_do_primeiro_vencimento(self):
        form = HonorarioForm(data=self._dados(
            classificacao="recorrente", periodicidade="mensal", duracao_tipo="data_final",
            duracao_data_final=self.hoje.isoformat(),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("duracao_data_final", form.errors)

    def test_recorrente_indeterminado_e_valido(self):
        form = HonorarioForm(data=self._dados(
            classificacao="recorrente", periodicidade="anual", duracao_tipo="indeterminado",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_parcelado_descarta_campos_de_recorrencia(self):
        form = HonorarioForm(data=self._dados_parcelado(periodicidade="anual", duracao_tipo="indeterminado"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["periodicidade"], "")
        self.assertEqual(form.cleaned_data["duracao_tipo"], "")

    def test_exito_sem_processo_e_recusado(self):
        form = HonorarioForm(data={
            "tipo": "contratual", "modalidade": "exito", "exito_percentual": "20", "exito_base": "ganho",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("processo", form.errors)

    def test_valor_mais_exito_sem_processo_tambem_e_recusado(self):
        form = HonorarioForm(data=self._dados(modalidade="valor_exito", exito_percentual="20", exito_base="ganho"))
        self.assertFalse(form.is_valid())
        self.assertIn("processo", form.errors)

    def test_exito_exige_percentual_e_base(self):
        form = HonorarioForm(data={"tipo": "contratual", "modalidade": "exito", "processo": self.processo.pk})
        self.assertFalse(form.is_valid())
        self.assertIn("exito_percentual", form.errors)
        self.assertIn("exito_base", form.errors)

    def test_exito_percentual_entre_zero_e_cem(self):
        for invalido in ("0", "101"):
            form = HonorarioForm(data={
                "tipo": "contratual", "modalidade": "exito", "processo": self.processo.pk,
                "exito_percentual": invalido, "exito_base": "ganho",
            })
            self.assertFalse(form.is_valid())
            self.assertIn("exito_percentual", form.errors)

    def test_so_exito_nao_tem_valor_nem_pagamento_e_deriva_cliente(self):
        form = HonorarioForm(data={
            "tipo": "contratual", "modalidade": "exito", "processo": self.processo.pk,
            "exito_percentual": "30", "exito_base": "economia",
            "valor_estimado": "999", "classificacao": "parcelado", "numero_parcelas": "4",
        })
        self.assertTrue(form.is_valid(), form.errors)
        h = form.save()
        self.assertEqual(h.valor_estimado, Decimal("0"))
        self.assertEqual((h.classificacao, h.numero_parcelas), ("", None))
        self.assertEqual(h.cliente, self.cliente)

    def test_valor_mais_exito_guarda_as_duas_partes(self):
        form = HonorarioForm(data=self._dados_parcelado(
            modalidade="valor_exito", processo=self.processo.pk, exito_percentual="15", exito_base="ganho",
        ))
        self.assertTrue(form.is_valid(), form.errors)
        h = form.save()
        self.assertEqual((h.valor_estimado, h.exito_percentual, h.exito_base), (Decimal("6000"), Decimal("15"), "ganho"))

    def test_apenas_valor_descarta_o_exito(self):
        form = HonorarioForm(data=self._dados(exito_percentual="15", exito_base="ganho"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["exito_percentual"])


class TestLancamentosGerados(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_lanc"

    def test_parcelado_6000_em_3x_gera_3_pendentes_de_2000(self):
        h = self._contratual()
        gerar_lancamentos_do_honorario(h, responsavel=self.user)
        lancamentos = list(h.lancamentos.order_by("data_vencimento"))
        self.assertEqual([l.valor for l in lancamentos], [Decimal("2000.00")] * 3)
        self.assertEqual({l.status for l in lancamentos}, {"pendente"})
        self.assertEqual({(l.tipo, l.categoria) for l in lancamentos}, {("receita", "honorario")})
        self.assertEqual([l.data_vencimento for l in lancamentos], [_somar_meses(self.hoje, i) for i in range(3)])
        self.assertEqual({(l.cliente, l.processo, l.responsavel) for l in lancamentos},
                         {(self.cliente, self.processo, self.user)})

    def test_ultima_parcela_absorve_o_arredondamento(self):
        h = self._contratual(valor_estimado=Decimal("1000"))
        gerar_lancamentos_do_honorario(h)
        valores = [l.valor for l in h.lancamentos.order_by("data_vencimento")]
        self.assertEqual(valores, [Decimal("333.33"), Decimal("333.33"), Decimal("333.34")])
        self.assertEqual(sum(valores), Decimal("1000"))

    def test_recorrente_mensal_por_quantidade(self):
        h = self._contratual(
            valor_estimado=Decimal("500"), classificacao="recorrente", numero_parcelas=None,
            periodicidade="mensal", duracao_tipo="quantidade", duracao_quantidade=4,
        )
        gerar_lancamentos_do_honorario(h)
        lancamentos = list(h.lancamentos.order_by("data_vencimento"))
        self.assertEqual(len(lancamentos), 4)
        self.assertEqual({l.valor for l in lancamentos}, {Decimal("500.00")})

    def test_recorrente_por_data_final(self):
        h = self._contratual(
            valor_estimado=Decimal("500"), classificacao="recorrente", numero_parcelas=None,
            periodicidade="mensal", duracao_tipo="data_final", duracao_data_final=_somar_meses(self.hoje, 3),
        )
        gerar_lancamentos_do_honorario(h)
        self.assertEqual(h.lancamentos.count(), 4)

    def test_recorrente_indeterminado_gera_a_janela_de_ocorrencias_futuras(self):
        for periodicidade, esperado in (("mensal", 24), ("anual", 5)):
            h = self._contratual(
                valor_estimado=Decimal("500"), classificacao="recorrente", numero_parcelas=None,
                periodicidade=periodicidade, duracao_tipo="indeterminado",
            )
            gerar_lancamentos_do_honorario(h)
            self.assertEqual(h.lancamentos.count(), esperado, periodicidade)

    def test_valor_unico_e_exito_nao_geram_lancamento(self):
        unico = self._contratual(classificacao="unica", numero_parcelas=None)
        so_exito = self._exito()
        for h in (unico, so_exito):
            gerar_lancamentos_do_honorario(h)
            self.assertEqual(h.lancamentos.count(), 0)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 0)

    def test_valor_mais_exito_gera_so_a_parte_valor(self):
        h = self._contratual(modalidade="valor_exito", exito_percentual=Decimal("20"), exito_base="ganho")
        gerar_lancamentos_do_honorario(h)
        self.assertEqual(h.lancamentos.count(), 3)
        self.assertEqual(sum(l.valor for l in h.lancamentos.all()), Decimal("6000"))

    def test_gerar_e_idempotente(self):
        h = self._contratual()
        gerar_lancamentos_do_honorario(h)
        gerar_lancamentos_do_honorario(h)
        self.assertEqual(h.lancamentos.count(), 3)


class TestTelasContratual(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_telas"

    def _criar_pela_tela(self, **kw):
        r = self.client.post("/financeiro/honorarios/novo/", self._dados_parcelado(**kw), HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        return Honorario.objects.get()

    def test_criar_pela_tela_gera_os_lancamentos(self):
        h = self._criar_pela_tela(processo=self.processo.pk)
        self.assertEqual(h.lancamentos.count(), 3)
        self.assertEqual({l.responsavel for l in h.lancamentos.all()}, {self.user})

    def test_formulario_invalido_nao_grava_nada(self):
        r = self.client.post(
            "/financeiro/honorarios/novo/", self._dados_parcelado(numero_parcelas="1"), HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Honorario.objects.count(), 0)
        self.assertEqual(LancamentoFinanceiro.objects.count(), 0)

    def test_editar_sem_mudar_a_estrutura_nao_duplica_lancamentos(self):
        h = self._criar_pela_tela()
        r = self.client.post(
            f"/financeiro/honorarios/{h.pk}/editar/", self._dados_parcelado(observacoes="ok"), HTTP_HOST=self.http_host,
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(h.lancamentos.count(), 3)

    def test_editar_valor_ou_parcelas_depois_de_gerados_e_recusado(self):
        h = self._criar_pela_tela()
        for mudanca in ({"valor_estimado": "9000"}, {"numero_parcelas": "5"}, {"classificacao": "unica"}):
            r = self.client.post(
                f"/financeiro/honorarios/{h.pk}/editar/", self._dados_parcelado(**mudanca), HTTP_HOST=self.http_host,
            )
            self.assertEqual(r.status_code, 200, mudanca)
            self.assertTrue(r.context["form"].non_field_errors(), mudanca)
        h.refresh_from_db()
        self.assertEqual((h.valor_estimado, h.numero_parcelas), (Decimal("6000.00"), 3))
        self.assertEqual(h.lancamentos.count(), 3)

    def test_cancelar_cancela_so_as_receitas_pendentes_ainda_futuras(self):
        h = self._contratual(numero_parcelas=4, data_prevista=_somar_meses(self.hoje, -2))
        gerar_lancamentos_do_honorario(h)
        vencida = h.lancamentos.order_by("data_vencimento").first()
        self.client.post(f"/financeiro/honorarios/{h.pk}/cancelar/", HTTP_HOST=self.http_host)
        h.refresh_from_db()
        vencida.refresh_from_db()
        ultima = h.lancamentos.order_by("data_vencimento").last()
        self.assertEqual(h.status, "cancelado")
        self.assertEqual(vencida.status, "pendente")
        self.assertEqual(ultima.status, "cancelado")

    def test_confirmar_recebimento_nao_existe_para_exito_nem_parcelado_recorrente(self):
        parcelado = self._contratual()
        so_exito = self._exito()
        for h in (parcelado, so_exito):
            url = f"/financeiro/honorarios/{h.pk}/confirmar-recebimento/"
            self.assertEqual(self.client.get(url, HTTP_HOST=self.http_host).status_code, 404)
            self.assertEqual(self.client.post(url, {}, HTTP_HOST=self.http_host).status_code, 404)

    def test_confirmar_recebimento_segue_para_valor_unico(self):
        h = self._contratual(classificacao="unica", numero_parcelas=None)
        r = self.client.get(f"/financeiro/honorarios/{h.pk}/confirmar-recebimento/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)

    def test_lista_mostra_parcelado_e_exito_sem_botao_de_confirmar(self):
        self._contratual()
        self._exito()
        r = self.client.get("/financeiro/honorarios/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Parcelado em 3x")
        self.assertContains(r, "sem valor a receber calculado")
        self.assertNotContains(r, "Confirmar recebimento")


class TestSucumbenciaNova(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_suc"

    def _dados_suc(self, **kw):
        dados = {
            "tipo": "sucumbencial", "processo": self.processo.pk, "forma_condenacao": "percentual",
            "percentual": "10", "valor_condenacao": "100000", "devedor_tipo": "pessoa",
            "indice_correcao": "ipca", "taxa_indice_mensal": "0.5",
            "data_correcao": self._atras(6).isoformat(), "data_juros": self._atras(3).isoformat(),
        }
        dados.update(kw)
        return dados

    def test_percentual_exige_valor_da_condenacao(self):
        form = HonorarioForm(data=self._dados_suc(valor_condenacao=""))
        self.assertFalse(form.is_valid())
        self.assertIn("valor_condenacao", form.errors)

    def test_fixo_mais_percentual_exige_fixo_percentual_e_condenacao(self):
        form = HonorarioForm(data=self._dados_suc(forma_condenacao="fixo_percentual", percentual="", valor_condenacao=""))
        self.assertFalse(form.is_valid())
        for campo in ("valor_fixo", "percentual", "valor_condenacao"):
            self.assertIn(campo, form.errors)

    def test_fixo_descarta_percentual_e_condenacao(self):
        form = HonorarioForm(data=self._dados_suc(forma_condenacao="fixo", valor_fixo="5000"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["percentual"])
        self.assertIsNone(form.cleaned_data["valor_condenacao"])

    def test_ipca_e_um_indice_aceito(self):
        self.assertIn("ipca", dict(Honorario.INDICE_CHOICES))
        form = HonorarioForm(data=self._dados_suc(indice_correcao="ipca"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().indice_correcao, "ipca")

    def test_data_final_nao_pode_ser_anterior_a_inicial(self):
        form = HonorarioForm(data=self._dados_suc(
            data_correcao_fim=self._atras(8).isoformat(), data_juros_fim=self._atras(5).isoformat(),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("data_correcao_fim", form.errors)
        self.assertIn("data_juros_fim", form.errors)

    def test_ente_estatal_descarta_juros_e_data_final_de_juros(self):
        form = HonorarioForm(data=self._dados_suc(
            devedor_tipo="ente_estatal", indice_correcao="", data_juros="", data_juros_fim=self.hoje.isoformat(),
        ))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["data_juros_fim"])

    def test_valor_estimado_gravado_inclui_o_exito_dos_contratos_do_processo(self):
        self._exito()
        form = HonorarioForm(data=self._dados_suc(indice_correcao="inpc"))
        self.assertTrue(form.is_valid(), form.errors)
        # sucumbência 10.600 + êxito 20% × condenação corrigida 106.000 = 21.200
        self.assertEqual(form.save().valor_estimado, Decimal("31800.00"))


class TestCalculoNovo(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_calc"

    def _suc(self, **kw):
        base = {
            "forma_condenacao": "percentual", "percentual": Decimal("10"), "valor_condenacao": Decimal("100000"),
            "valor_fixo": None, "taxa_indice_mensal": Decimal("0"), "data_correcao": None, "data_juros": None,
        }
        base.update(kw)
        return self._honorario(**base)

    def test_fixo_mais_percentual_soma_o_fixo_ao_percentual_da_condenacao(self):
        h = self._suc(forma_condenacao="fixo_percentual", valor_fixo=Decimal("1000"))
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["sucumbencia"], Decimal("11000.00"))

    def test_correcao_para_na_data_final_e_com_data_final_vazia_vai_ate_hoje(self):
        h = self._suc(
            forma_condenacao="fixo", valor_fixo=Decimal("10000"), percentual=None, valor_condenacao=None,
            devedor_tipo="ente_estatal", indice_correcao="selic", taxa_indice_mensal=Decimal("1"),
            data_correcao=self._atras(6), data_correcao_fim=self._atras(3),
        )
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("10300.00"))
        h.data_correcao_fim = None
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("10600.00"))

    def test_juros_e_correcao_tem_intervalos_independentes(self):
        h = self._suc(
            forma_condenacao="fixo", valor_fixo=Decimal("10000"), percentual=None, valor_condenacao=None,
            devedor_tipo="pessoa", indice_correcao="ipca", taxa_indice_mensal=Decimal("1"),
            data_correcao=self._atras(6), data_correcao_fim=self._atras(4),
            data_juros=self._atras(5), data_juros_fim=self._atras(1),
        )
        # correção 1% × 2 meses + juros 1% × 4 meses
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("10600.00"))

    def test_data_final_anterior_a_inicial_nao_gera_correcao_negativa(self):
        h = self._suc(
            forma_condenacao="fixo", valor_fixo=Decimal("10000"), percentual=None, valor_condenacao=None,
            devedor_tipo="ente_estatal", taxa_indice_mensal=Decimal("1"),
            data_correcao=self._atras(3), data_correcao_fim=self._atras(6),
        )
        self.assertEqual(calcular_honorario_sucumbencial(h, self.hoje)["total"], Decimal("10000.00"))


class TestAvisoDeExito(ContratualBase):
    @classmethod
    def get_test_schema_name(cls):
        return "hon_ctr_aviso"

    def _sucumbencia(self, **kw):
        return self._honorario(**kw)  # 10% de 100.000, INPC 0,5% × 6 meses + juros 1% × 3 meses

    def test_aviso_calcula_sobre_a_condenacao_corrigida_e_soma_ao_total(self):
        contrato = self._exito(exito_percentual=Decimal("20"))
        suc = self._sucumbencia()
        calculo = calcular_honorario_sucumbencial(suc, self.hoje, contratos_de_exito_pelo_ganho(self.processo))
        # condenação corrigida = 100.000 + 3% + 3% = 106.000 → 20% = 21.200
        self.assertEqual(len(calculo["exito_contratos"]), 1)
        linha = calculo["exito_contratos"][0]
        self.assertEqual((linha["contrato"], linha["percentual"], linha["valor"]), (contrato, Decimal("20"), Decimal("21200.00")))
        self.assertEqual(calculo["sucumbencia"], Decimal("10600.00"))
        self.assertEqual(calculo["exito"], Decimal("21200.00"))
        self.assertEqual(calculo["total"], Decimal("31800.00"))

    def test_uma_linha_por_contrato_e_o_total_soma_todas(self):
        self._exito(exito_percentual=Decimal("20"))
        self._contratual(
            modalidade="valor_exito", exito_percentual=Decimal("5"), exito_base="ganho",
            classificacao="unica", numero_parcelas=None,
        )
        calculo = calcular_honorario_sucumbencial(
            self._sucumbencia(), self.hoje, contratos_de_exito_pelo_ganho(self.processo),
        )
        self.assertEqual(sorted(l["valor"] for l in calculo["exito_contratos"]), [Decimal("5300.00"), Decimal("21200.00")])
        self.assertEqual(calculo["exito"], Decimal("26500.00"))

    def test_pela_economia_cancelado_e_outro_processo_ficam_de_fora(self):
        outro = Processo.objects.create(criado_por=self.user, titulo="Outro")
        outro.clientes.add(self.cliente)
        self._exito(exito_base="economia")
        self._exito(status="cancelado")
        self._exito(processo=outro)
        self.assertEqual(contratos_de_exito_pelo_ganho(self.processo), [])
        calculo = calcular_honorario_sucumbencial(self._sucumbencia(), self.hoje, [])
        self.assertEqual((calculo["exito_contratos"], calculo["exito"], calculo["total"]),
                         ([], Decimal("0.00"), Decimal("10600.00")))

    def test_sem_condenacao_nao_ha_base_para_o_aviso(self):
        self._exito()
        suc = self._sucumbencia(forma_condenacao="fixo", percentual=None, valor_condenacao=None, valor_fixo=Decimal("5000"))
        calculo = calcular_honorario_sucumbencial(suc, self.hoje, contratos_de_exito_pelo_ganho(self.processo))
        self.assertEqual(calculo["exito_contratos"], [])

    def test_lista_mostra_o_aviso_e_o_total_com_o_exito(self):
        self._exito()
        self._sucumbencia()
        r = self.client.get("/financeiro/honorarios/", HTTP_HOST=self.http_host)
        suc = next(h for h in r.context["honorarios"] if h.tipo == "sucumbencial")
        self.assertEqual(suc.valor_total_exibido, Decimal("31800.00"))
        self.assertContains(r, "de êxito a receber")

    def test_edicao_da_sucumbencia_mostra_o_aviso(self):
        self._exito()
        suc = self._sucumbencia()
        r = self.client.get(f"/financeiro/honorarios/{suc.pk}/editar/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "de êxito a receber")

    def test_confirmar_recebimento_da_sucumbencia_vem_com_o_total_incluindo_o_exito(self):
        self._exito()
        suc = self._sucumbencia()
        r = self.client.get(f"/financeiro/honorarios/{suc.pk}/confirmar-recebimento/", HTTP_HOST=self.http_host)
        self.assertEqual(r.context["form"].initial["valor_efetivo"], Decimal("31800.00"))
