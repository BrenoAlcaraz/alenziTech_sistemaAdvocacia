from django.contrib import admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory
from django.urls import resolve, reverse

from apps.accounts.permissoes_constants import NIVEL_TODOS
from apps.clientes.models import Cliente
from apps.processos.forms import ParteProcessoForm
from apps.processos.models import (
    AutoridadeProcessual,
    HistoricoClassificacaoParte,
    ParteProcesso,
    Processo,
    RepresentanteParte,
)
from apps.processos.services import (
    garantir_participante_cliente,
    normalizar_documento,
    obter_ou_criar_representante_externo,
)

from .test_escopo import ProcessosEscopoBase


class TestParticipantesProcessuais(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0006_participantes"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "WI-0006 Participantes"
        tenant.slug = "wi0006-participantes"

    def setUp(self):
        super().setUp()
        self.user = self._user("responsavel_participantes")
        self.user.first_name = "Ana"
        self.user.last_name = "Interna"
        self.user.save(update_fields=["first_name", "last_name"])
        self._autorizar(self.user, NIVEL_TODOS)
        self.cliente = self._cliente(self.user, "Cliente do Processo")
        self.cliente.cpf_cnpj = "123.456.789-00"
        self.cliente.save(update_fields=["cpf_cnpj"])
        self.processo = self._processo(
            self.user,
            self.cliente,
            "Processo WI-0006",
        )
        self.client.force_login(self.user)

    def _url_parte(self, processo=None):
        processo = processo or self.processo
        return f"/processos/{processo.pk}/partes/nova/"

    def _url_advogado(self, parte, processo=None):
        processo = processo or parte.processo
        return f"/processos/{processo.pk}/partes/{parte.pk}/advogados/novo/"

    def _url_remover(self, representante):
        parte = representante.parte
        return (
            f"/processos/{parte.processo_id}/partes/{parte.pk}/advogados/"
            f"{representante.pk}/remover/"
        )

    def _url_classificacao(self, parte, processo=None):
        processo = processo or parte.processo
        return f"/processos/{processo.pk}/partes/{parte.pk}/classificacao/"

    def _adicionar_parte(self, tipo="autor", **extra):
        payload = {
            "tipo": tipo,
            "vinculo_escritorio": "outro",
            "nome": f"Parte {tipo}",
            "cpf_cnpj": "",
        }
        payload.update(extra)
        return self.client.post(
            self._url_parte(),
            payload,
            HTTP_HOST=self.http_host,
        )

    def _parte(self, **kwargs):
        defaults = {
            "processo": self.processo,
            "nome": "Parte existente",
            "vinculo_escritorio": "outro",
            "posicao": "polo_ativo",
            "qualificacao": "autor",
        }
        defaults.update(kwargs)
        return ParteProcesso.objects.create(**defaults)

    def _login_superuser_admin(self):
        administrador = self._user("django_admin_participantes")
        administrador.is_staff = True
        administrador.is_superuser = True
        administrador.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(administrador)
        return administrador

    def test_cliente_do_processo_nasce_pendente_com_fk_e_advogado_sem_depender_de_documento(self):
        participante = self.processo.partes.get(cliente=self.cliente)
        self.assertTrue(participante.classificacao_pendente)
        self.assertIsNone(participante.posicao)
        self.assertIsNone(participante.qualificacao)
        self.assertEqual(participante.nome, "")
        self.assertEqual(participante.cpf_cnpj, "")
        self.assertEqual(participante.nome_exibicao, self.cliente.nome_razao_social)
        self.assertEqual(participante.cpf_cnpj_exibicao, self.cliente.cpf_cnpj)
        self.assertEqual(
            list(participante.representantes.values_list("usuario_id", flat=True)),
            [self.processo.responsavel_id],
        )

        cliente_sem_documento = self._cliente(self.user, "Cliente sem documento")
        processo_sem_documento = Processo.objects.create(
            titulo="Processo sem documento",
            cliente=cliente_sem_documento,
            responsavel=self.user,
        )
        participante_sem_documento = processo_sem_documento.partes.get(
            cliente=cliente_sem_documento
        )
        self.assertTrue(participante_sem_documento.classificacao_pendente)
        self.assertEqual(participante_sem_documento.cpf_cnpj_exibicao, "")
        self.assertEqual(participante_sem_documento.representantes.count(), 1)

    def test_criacao_http_do_processo_cria_participante_automatico(self):
        cliente = self._cliente(self.user, "Cliente criado por HTTP")
        resposta = self.client.post(
            "/processos/novo/",
            {
                "titulo": "Processo criado por HTTP",
                "cliente": cliente.pk,
                "area_direito": "CÍVEL",
                "fase": "conhecimento",
                "instancia": "1ª Instância",
                "gratuidade_justica_status": "nao_requerida",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        processo = Processo.objects.get(titulo="Processo criado por HTTP")
        participante = processo.partes.get(cliente=cliente)
        self.assertTrue(participante.classificacao_pendente)
        self.assertEqual(participante.representantes.get().usuario_id, self.user.pk)

    def test_sincronizacao_repetida_nao_duplica_cliente_nem_advogado(self):
        for _ in range(3):
            garantir_participante_cliente(self.processo)
        participante = self.processo.partes.get(cliente=self.cliente)
        self.assertEqual(
            self.processo.partes.filter(cliente=self.cliente).count(),
            1,
        )
        self.assertEqual(
            participante.representantes.filter(
                tipo="interno",
                usuario=self.processo.responsavel,
            ).count(),
            1,
        )

    def test_identidade_exibida_reflete_alteracao_do_cliente(self):
        participante = self.processo.partes.get(cliente=self.cliente)
        self.cliente.nome_razao_social = "Cliente atualizado"
        self.cliente.cpf_cnpj = "98.765.432/0001-10"
        self.cliente.save(update_fields=["nome_razao_social", "cpf_cnpj"])
        participante.refresh_from_db()
        self.assertEqual(participante.nome_exibicao, "Cliente atualizado")
        self.assertEqual(participante.cpf_cnpj_exibicao, "98.765.432/0001-10")
        resposta = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertContains(resposta, "Cliente atualizado")
        self.assertContains(resposta, "98.765.432/0001-10")

    def test_troca_cliente_a_b_a_reutiliza_participante_e_preserva_historico(self):
        anterior = self.processo.partes.get(cliente=self.cliente)
        self.client.post(
            self._url_classificacao(anterior),
            {"tipo": "autor", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        RepresentanteParte.objects.create(
            parte=anterior,
            tipo="externo",
            nome_externo="Advogada preservada",
            oab="12345",
            uf_oab="SP",
        )
        novo_cliente = self._cliente(self.user, "Novo Cliente")
        self.processo.cliente = novo_cliente
        self.processo.save(update_fields=["cliente"])

        anterior.refresh_from_db()
        novo = self.processo.partes.get(cliente=novo_cliente)
        self.assertEqual(anterior.qualificacao, "autor")
        self.assertTrue(anterior.representantes.filter(nome_externo="Advogada preservada").exists())
        self.assertTrue(novo.classificacao_pendente)
        self.assertEqual(novo.representantes.filter(usuario=self.user).count(), 1)

        historico_ids = list(
            anterior.historico_classificacao.values_list("pk", flat=True)
        )
        representante_ids = list(
            anterior.representantes.values_list("pk", flat=True)
        )
        self.processo.cliente = self.cliente
        self.processo.save(update_fields=["cliente"])

        participante_a = self.processo.partes.get(cliente=self.cliente)
        participante_b = self.processo.partes.get(cliente=novo_cliente)
        self.assertEqual(participante_a.pk, anterior.pk)
        self.assertEqual(participante_b.pk, novo.pk)
        self.assertEqual(
            self.processo.partes.filter(cliente=self.cliente).count(),
            1,
        )
        self.assertEqual(
            list(
                participante_a.historico_classificacao.values_list(
                    "pk", flat=True
                )
            ),
            historico_ids,
        )
        self.assertEqual(
            list(participante_a.representantes.values_list("pk", flat=True)),
            representante_ids,
        )

    def test_taxonomia_agrupada_mapeia_os_nove_tipos_de_parte(self):
        grupos = ParteProcessoForm.TIPO_CHOICES
        self.assertEqual([grupo for grupo, _ in grupos], ["POLO ATIVO", "POLO PASSIVO", "OUTROS"])
        self.assertEqual(
            dict(ParteProcessoForm.POSICAO_POR_TIPO),
            {
                "autor": "polo_ativo",
                "embargante": "polo_ativo",
                "recorrente": "polo_ativo",
                "reu": "polo_passivo",
                "embargado": "polo_passivo",
                "recorrido": "polo_passivo",
                "terceiro_interessado": "terceiro",
                "ministerio_publico": "ministerio_publico",
                "amicus_curiae": "terceiro",
            },
        )
        valores = {valor for _, opcoes in grupos for valor, _ in opcoes}
        self.assertIn("juiz", valores)
        self.assertNotIn("advogado_contrario", valores)

    def test_cada_tipo_cria_posicao_e_qualificacao_corretas(self):
        for tipo, posicao in ParteProcessoForm.POSICAO_POR_TIPO.items():
            with self.subTest(tipo=tipo):
                extra = {}
                if tipo == "ministerio_publico":
                    extra["atuacao_ministerio_publico"] = "fiscal_ordem_juridica"
                resposta = self._adicionar_parte(tipo, **extra)
                self.assertEqual(resposta.status_code, 302)
                parte = ParteProcesso.objects.get(
                    processo=self.processo,
                    qualificacao=tipo,
                )
                self.assertEqual(parte.posicao, posicao)

    def test_ministerio_publico_aceita_parte_e_fiscal(self):
        for atuacao in ("parte", "fiscal_ordem_juridica"):
            with self.subTest(atuacao=atuacao):
                resposta = self._adicionar_parte(
                    "ministerio_publico",
                    nome=f"MP {atuacao}",
                    atuacao_ministerio_publico=atuacao,
                )
                self.assertEqual(resposta.status_code, 302)
                participante = ParteProcesso.objects.get(nome=f"MP {atuacao}")
                self.assertEqual(participante.posicao, "ministerio_publico")
                self.assertEqual(participante.atuacao_ministerio_publico, atuacao)

    def test_juiz_e_autoridade_separada_e_nao_parte(self):
        antes = ParteProcesso.objects.count()
        resposta = self._adicionar_parte(
            "juiz",
            nome="Juíza Maria",
            vara_orgao="2ª Vara Cível",
            observacao="Substituta",
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(ParteProcesso.objects.count(), antes)
        autoridade = AutoridadeProcessual.objects.get(processo=self.processo)
        self.assertEqual(autoridade.tipo, "juiz")
        self.assertEqual(autoridade.vara_orgao, "2ª Vara Cível")
        self.assertFalse(hasattr(autoridade, "representantes"))

    def test_parte_aceita_zero_um_e_multiplos_advogados_externos(self):
        parte = self._parte()
        self.assertEqual(parte.representantes.count(), 0)
        for numero, uf in (("123456", "RJ"), ("654321", "SP")):
            resposta = self.client.post(
                self._url_advogado(parte),
                {
                    "tipo": "externo",
                    "nome_externo": f"Advogado {numero}",
                    "oab": numero,
                    "uf_oab": uf,
                    "telefone": "(11) 99999-0000",
                    "email": f"{numero}@example.com",
                },
                HTTP_HOST=self.http_host,
            )
            self.assertEqual(resposta.status_code, 302)
        self.assertEqual(parte.representantes.count(), 2)
        primeiro = parte.representantes.order_by("pk").first()
        self.assertEqual(primeiro.oab, "123456")
        self.assertEqual(primeiro.uf_oab, "RJ")
        self.assertEqual(primeiro.telefone, "11999990000")
        self.assertEqual(primeiro.email, "123456@example.com")
        self.assertEqual(ParteProcesso.objects.filter(pk=parte.pk).count(), 1)

    def test_advogado_interno_reutiliza_user_e_post_repetido_e_idempotente(self):
        parte = self._parte()
        payload = {"tipo": "interno", "usuario": self.user.pk}
        for _ in range(2):
            resposta = self.client.post(
                self._url_advogado(parte),
                payload,
                HTTP_HOST=self.http_host,
            )
            self.assertEqual(resposta.status_code, 302)
        representante = RepresentanteParte.objects.get(parte=parte)
        self.assertEqual(representante.usuario_id, self.user.pk)
        self.assertEqual(representante.nome, "Ana Interna")
        self.assertEqual(parte.representantes.count(), 1)

    def test_constraint_impede_representante_interno_duplicado(self):
        parte = self._parte()
        RepresentanteParte.objects.create(
            parte=parte,
            tipo="interno",
            usuario=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RepresentanteParte.objects.bulk_create([
                    RepresentanteParte(
                        parte=parte,
                        tipo="interno",
                        usuario=self.user,
                    )
                ])

    def test_constraint_exige_identidade_profissional_minima_do_externo(self):
        parte = self._parte()
        with self.assertRaises(ValidationError):
            RepresentanteParte.objects.create(
                parte=parte,
                tipo="externo",
                nome_externo="",
                oab="",
                uf_oab="",
            )

    def test_constraint_mantem_vinculo_cliente_coerente_com_fk(self):
        for cliente, vinculo in ((None, "cliente"), (self.cliente, "outro")):
            with self.subTest(cliente=cliente, vinculo=vinculo):
                with self.assertRaises(ValidationError):
                    self._parte(
                        cliente=cliente,
                        vinculo_escritorio=vinculo,
                    )

        automatico = self.processo.partes.get(cliente=self.cliente)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParteProcesso.objects.bulk_create([
                    ParteProcesso(
                        processo=self.processo,
                        cliente=self.cliente,
                        nome="",
                        vinculo_escritorio="cliente",
                        classificacao_pendente=True,
                    )
                ])
        self.assertTrue(ParteProcesso.objects.filter(pk=automatico.pk).exists())

    def test_taxonomia_invalida_e_rejeitada_no_model_e_no_banco(self):
        casos = [
            ("autor", "polo_passivo"),
            ("embargante", "polo_passivo"),
            ("recorrente", "polo_passivo"),
            ("reu", "polo_ativo"),
            ("embargado", "polo_ativo"),
            ("recorrido", "polo_ativo"),
        ]
        for qualificacao, posicao in casos:
            with self.subTest(qualificacao=qualificacao):
                with self.assertRaises(ValidationError):
                    self._parte(qualificacao=qualificacao, posicao=posicao)

        parte = self._parte()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParteProcesso.objects.filter(pk=parte.pk).update(
                    posicao="polo_passivo",
                    qualificacao="autor",
                )

    def test_pendente_mp_e_legado_possuem_integridade_de_dominio(self):
        with self.assertRaises(ValidationError):
            self._parte(
                classificacao_pendente=True,
                posicao=None,
                qualificacao=None,
            )
        with self.assertRaises(ValidationError):
            self._parte(
                posicao="ministerio_publico",
                qualificacao="ministerio_publico",
                atuacao_ministerio_publico="",
            )
        with self.assertRaises(ValidationError):
            self._parte(atuacao_ministerio_publico="parte")
        with self.assertRaises(ValidationError):
            self._parte(
                vinculo_escritorio="legado",
                posicao="legado",
                qualificacao="advogado_contrario_legado",
                registro_legado=False,
            )
        with self.assertRaises(ValidationError):
            self._parte(
                vinculo_escritorio="legado",
                posicao="legado",
                qualificacao="advogado_contrario_legado",
                registro_legado=True,
                tipo_legado="",
            )

    def test_constraint_banco_impede_taxonomia_legada_sem_flag(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParteProcesso.objects.bulk_create([
                    ParteProcesso(
                        processo=self.processo,
                        nome="Legado inválido por bypass",
                        vinculo_escritorio="outro",
                        posicao="legado",
                        qualificacao="advogado_contrario_legado",
                        tipo_legado="advogado_contrario",
                        registro_legado=False,
                    )
                ])

        parte = self._parte()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ParteProcesso.objects.filter(pk=parte.pk).update(
                    posicao="legado",
                    qualificacao="advogado_contrario_legado",
                    registro_legado=False,
                )

        ParteProcesso.objects.bulk_create([
            ParteProcesso(
                processo=self.processo,
                nome="Advogado contrário preservado",
                vinculo_escritorio="legado",
                posicao="legado",
                qualificacao="advogado_contrario_legado",
                tipo_legado="advogado_contrario",
                registro_legado=True,
            )
        ])
        self.assertTrue(
            ParteProcesso.objects.filter(
                nome="Advogado contrário preservado",
                registro_legado=True,
            ).exists()
        )

    def test_representante_hibrido_e_rejeitado(self):
        parte = self._parte()
        with self.assertRaises(ValidationError):
            RepresentanteParte.objects.create(
                parte=parte,
                tipo="interno",
                usuario=self.user,
                nome_externo="Nome contraditório",
                oab="123",
                uf_oab="SP",
            )
        with self.assertRaises(ValidationError):
            RepresentanteParte.objects.create(
                parte=parte,
                tipo="externo",
                usuario=self.user,
                nome_externo="Externo híbrido",
                oab="456",
                uf_oab="RJ",
            )

    def test_constraint_banco_rejeita_representante_hibrido_sem_clean(self):
        parte = self._parte()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RepresentanteParte.objects.bulk_create([
                    RepresentanteParte(
                        parte=parte,
                        tipo="interno",
                        usuario=self.user,
                        nome_externo="Nome externo indevido",
                        oab="12345",
                        uf_oab="SP",
                    )
                ])

    def test_post_externo_repetido_e_idempotente_com_dados_normalizados(self):
        parte = self._parte()
        payloads = [
            {
                "tipo": "externo",
                "nome_externo": "  Maria   Externa ",
                "oab": "12345-A",
                "uf_oab": "sp",
                "telefone": "(11) 99999-0000",
                "email": "MARIA@EXAMPLE.COM",
            },
            {
                "tipo": "externo",
                "nome_externo": "mArIa ExTeRnA",
                "oab": "12345A",
                "uf_oab": "SP",
                "telefone": "11999990000",
                "email": "maria@example.com",
            },
        ]
        for payload in payloads:
            resposta = self.client.post(
                self._url_advogado(parte),
                payload,
                HTTP_HOST=self.http_host,
            )
            self.assertEqual(resposta.status_code, 302)
        representante = parte.representantes.get(tipo="externo")
        self.assertEqual(representante.nome_externo, "Maria Externa")
        self.assertEqual(representante.oab, "12345A")
        self.assertEqual(representante.uf_oab, "SP")
        self.assertEqual(representante.telefone, "11999990000")
        self.assertEqual(representante.email, "maria@example.com")

    def test_update_fields_persiste_novo_fingerprint_externo(self):
        parte = self._parte()
        representante = RepresentanteParte.objects.create(
            parte=parte,
            tipo="externo",
            nome_externo="Maria Externa",
            oab="12345-A",
            uf_oab="sp",
            telefone="(11) 99999-0000",
            email="MARIA@EXAMPLE.COM",
        )
        fingerprint_anterior = representante.fingerprint_externo

        representante.oab = "98765-B"
        representante.save(update_fields=["oab"])
        fingerprint_novo = representante.fingerprint_externo
        representante.refresh_from_db()

        self.assertEqual(representante.oab, "98765B")
        self.assertEqual(representante.fingerprint_externo, fingerprint_novo)
        self.assertNotEqual(representante.fingerprint_externo, fingerprint_anterior)

        equivalente = RepresentanteParte(
            tipo="externo",
            nome_externo="  maria   externa ",
            oab="98765 B",
            uf_oab="SP",
            telefone="11999990000",
            email="maria@example.com",
        )
        obtido, criado = obter_ou_criar_representante_externo(
            parte,
            equivalente,
        )
        self.assertFalse(criado)
        self.assertEqual(obtido.pk, representante.pk)
        self.assertEqual(parte.representantes.count(), 1)

    def test_mesmo_externo_e_aceito_em_partes_distintas(self):
        partes = [
            self._parte(nome="Parte A"),
            self._parte(nome="Parte B", qualificacao="reu", posicao="polo_passivo"),
        ]
        for parte in partes:
            representante = RepresentanteParte(
                tipo="externo",
                nome_externo="Advogada Compartilhada",
                oab="12345-A",
                uf_oab="sp",
                telefone="(11) 99999-0000",
                email="ADVOGADA@EXAMPLE.COM",
            )
            _, criado = obter_ou_criar_representante_externo(
                parte,
                representante,
            )
            self.assertTrue(criado)

        self.assertEqual(partes[0].representantes.count(), 1)
        self.assertEqual(partes[1].representantes.count(), 1)
        self.assertEqual(
            partes[0].representantes.get().fingerprint_externo,
            partes[1].representantes.get().fingerprint_externo,
        )

    def test_classificacao_pendente_e_alteracao_preservam_pk_e_criam_historico(self):
        parte = self.processo.partes.get(cliente=self.cliente)
        pk_original = parte.pk
        resposta = self.client.post(
            self._url_classificacao(parte),
            {"tipo": "autor", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        parte.refresh_from_db()
        self.assertEqual(parte.pk, pk_original)
        self.assertFalse(parte.classificacao_pendente)
        historico_pendente = parte.historico_classificacao.get()
        self.assertIsNone(historico_pendente.posicao_anterior)
        self.assertIsNone(historico_pendente.qualificacao_anterior)
        self.assertEqual(historico_pendente.posicao_nova, "polo_ativo")
        self.assertEqual(historico_pendente.qualificacao_nova, "autor")
        self.assertEqual(historico_pendente.usuario_id, self.user.pk)

        self.client.post(
            self._url_classificacao(parte),
            {"tipo": "reu", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        parte.refresh_from_db()
        self.assertEqual(parte.pk, pk_original)
        self.assertEqual(parte.qualificacao, "reu")
        alteracao = parte.historico_classificacao.order_by("-pk").first()
        self.assertEqual(alteracao.posicao_anterior, "polo_ativo")
        self.assertEqual(alteracao.qualificacao_anterior, "autor")
        self.assertEqual(alteracao.posicao_nova, "polo_passivo")
        self.assertEqual(alteracao.qualificacao_nova, "reu")
        self.assertEqual(HistoricoClassificacaoParte.objects.filter(parte=parte).count(), 2)

    def test_salvar_sem_alteracao_efetiva_nao_cria_historico(self):
        parte = self._parte()
        parte.save(
            update_fields=[
                "posicao",
                "qualificacao",
                "atuacao_ministerio_publico",
            ]
        )
        self.assertFalse(parte.historico_classificacao.exists())

    def test_alteracao_de_dominio_sem_usuario_cria_historico_com_ator_nulo(self):
        parte = self._parte()
        parte.posicao = "polo_passivo"
        parte.qualificacao = "reu"
        parte.save(update_fields=["posicao", "qualificacao"])

        historico = parte.historico_classificacao.get()
        self.assertEqual(historico.posicao_anterior, "polo_ativo")
        self.assertEqual(historico.qualificacao_anterior, "autor")
        self.assertEqual(historico.posicao_nova, "polo_passivo")
        self.assertEqual(historico.qualificacao_nova, "reu")
        self.assertIsNone(historico.usuario_id)

    def test_autovinculo_normaliza_documento_e_usa_responsavel_do_processo(self):
        self.assertEqual(normalizar_documento("123.456.789-00"), "12345678900")
        resposta = self._adicionar_parte(
            "autor",
            nome="Nome digitado não prevalece",
            cpf_cnpj="12345678900",
        )
        self.assertEqual(resposta.status_code, 302)
        parte = ParteProcesso.objects.get(processo=self.processo)
        self.assertEqual(parte.cliente_id, self.cliente.pk)
        self.assertEqual(parte.nome, "")
        self.assertEqual(parte.nome_exibicao, self.cliente.nome_razao_social)
        representante = parte.representantes.get()
        self.assertEqual(representante.tipo, "interno")
        self.assertEqual(representante.usuario_id, self.processo.responsavel_id)

        # Reprocessamento da mesma automação não duplica o usuário interno.
        from apps.processos.services import vincular_responsavel_como_advogado

        vincular_responsavel_como_advogado(parte)
        self.assertEqual(parte.representantes.count(), 1)

    def test_autovinculo_nao_ocorre_com_documento_diferente_vazio_ou_cliente_alheio(self):
        outro_cliente = Cliente.objects.create(
            nome_razao_social="Outro cliente",
            tipo="PF",
            cpf_cnpj="999.999.999-99",
            responsavel=self.user,
        )
        casos = [
            ("documento_diferente", "000.000.000-00"),
            ("documento_vazio", ""),
            # Existe outro Cliente do escritório com este documento, mas não é
            # o Cliente vinculado ao Processo.
            ("cliente_alheio", outro_cliente.cpf_cnpj),
        ]
        for sufixo, documento in casos:
            with self.subTest(caso=sufixo):
                self._adicionar_parte(
                    "autor",
                    nome=f"Parte {sufixo}",
                    cpf_cnpj=documento,
                )
                parte = ParteProcesso.objects.get(nome=f"Parte {sufixo}")
                self.assertIsNone(parte.cliente_id)
                self.assertEqual(parte.representantes.count(), 0)

    def test_remocao_apaga_somente_representacao(self):
        parte = self._parte()
        representante = RepresentanteParte.objects.create(
            parte=parte,
            tipo="interno",
            usuario=self.user,
        )
        resposta = self.client.post(
            self._url_remover(representante),
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(RepresentanteParte.objects.filter(pk=representante.pk).exists())
        self.assertTrue(ParteProcesso.objects.filter(pk=parte.pk).exists())
        self.assertTrue(type(self.user).objects.filter(pk=self.user.pk).exists())
        self.assertTrue(type(self.processo).objects.filter(pk=self.processo.pk).exists())

    def test_admin_nao_exclui_participante_do_cliente_atual(self):
        participante = self.processo.partes.get(cliente=self.cliente)
        self._login_superuser_admin()

        resposta = self.client.post(
            reverse(
                "admin:processos_parteprocesso_delete",
                args=[participante.pk],
            ),
            {"post": "yes"},
            HTTP_HOST=self.http_host,
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(ParteProcesso.objects.filter(pk=participante.pk).exists())

    def test_admin_delete_em_massa_bloqueia_selecao_com_cliente_atual(self):
        participante = self.processo.partes.get(cliente=self.cliente)
        parte_comum = self._parte(nome="Parte selecionada com Cliente atual")
        self._login_superuser_admin()

        resposta = self.client.post(
            reverse("admin:processos_parteprocesso_changelist"),
            {
                "action": "delete_selected",
                ACTION_CHECKBOX_NAME: [participante.pk, parte_comum.pk],
                "select_across": "0",
                "index": "0",
                "post": "yes",
            },
            HTTP_HOST=self.http_host,
            follow=True,
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "A exclusão foi bloqueada")
        self.assertTrue(ParteProcesso.objects.filter(pk=participante.pk).exists())
        self.assertTrue(ParteProcesso.objects.filter(pk=parte_comum.pk).exists())

    def test_admin_pode_excluir_participante_de_cliente_antigo(self):
        participante_antigo = self.processo.partes.get(cliente=self.cliente)
        cliente_atual = self._cliente(self.user, "Cliente atual após troca")
        self.processo.cliente = cliente_atual
        self.processo.save(update_fields=["cliente"])
        administrador = self._login_superuser_admin()
        request = RequestFactory().post("/admin/processos/parteprocesso/")
        request.user = administrador
        model_admin = admin.site._registry[ParteProcesso]

        self.assertTrue(
            model_admin.has_delete_permission(request, participante_antigo)
        )
        model_admin.delete_model(request, participante_antigo)
        self.assertFalse(
            ParteProcesso.objects.filter(pk=participante_antigo.pk).exists()
        )
        self.assertTrue(
            ParteProcesso.objects.filter(
                processo=self.processo,
                cliente=cliente_atual,
            ).exists()
        )

    def test_admin_exclusao_do_processo_mantem_cascata_legitima(self):
        participante = self.processo.partes.get(cliente=self.cliente)
        administrador = self._login_superuser_admin()
        url = reverse("admin:processos_processo_delete", args=[self.processo.pk])
        request = RequestFactory().get(url)
        request.user = administrador
        request.resolver_match = resolve(url)
        processo_admin = admin.site._registry[Processo]

        _, _, permissoes_faltantes, protegidos = (
            processo_admin.get_deleted_objects([self.processo], request)
        )
        self.assertFalse(permissoes_faltantes)
        self.assertFalse(protegidos)

        processo_pk = self.processo.pk
        self.processo.delete()
        self.assertFalse(Processo.objects.filter(pk=processo_pk).exists())
        self.assertFalse(ParteProcesso.objects.filter(pk=participante.pk).exists())

    def test_detalhe_exibe_advogados_abaixo_da_parte_sem_oab_inventada(self):
        parte = self._parte(nome="Maria da Silva")
        RepresentanteParte.objects.create(
            parte=parte,
            tipo="interno",
            usuario=self.user,
        )
        RepresentanteParte.objects.create(
            parte=parte,
            tipo="externo",
            nome_externo="João Souza",
            oab="123456",
            uf_oab="RJ",
        )
        resposta = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        conteudo = resposta.content.decode()
        self.assertContains(resposta, "Maria da Silva")
        self.assertContains(resposta, "Ana Interna")
        self.assertContains(resposta, "Advogado do escritório")
        self.assertContains(resposta, "OAB/RJ 123456")
        self.assertNotIn("OAB/  ", conteudo)


class TestParticipantesIdor(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0006_participantes_idor"

    def setUp(self):
        super().setUp()
        self.user = self._user("leitor_todos")
        self.dono = self._user("dono_processo_alheio")
        self._autorizar(self.user, NIVEL_TODOS)
        cliente = self._cliente(self.dono)
        self.processo = self._processo(self.dono, cliente, "Processo alheio")
        self.parte = ParteProcesso.objects.create(
            processo=self.processo,
            nome="Parte alheia",
            vinculo_escritorio="outro",
            posicao="polo_passivo",
            qualificacao="reu",
        )
        self.representante = RepresentanteParte.objects.create(
            parte=self.parte,
            tipo="interno",
            usuario=self.dono,
        )
        self.client.force_login(self.user)

    def _url_classificacao(self, parte):
        return (
            f"/processos/{parte.processo_id}/partes/{parte.pk}/classificacao/"
        )

    def test_todos_le_processo_mas_nao_adiciona_nem_remove_advogado(self):
        detalhe = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(detalhe.status_code, 200)
        self.assertFalse(detalhe.context["pode_modificar"])
        self.assertNotContains(detalhe, "Adicionar advogado")
        self.assertNotContains(detalhe, "Alterar classificação")
        self.assertNotContains(detalhe, "Classificar participante")

        quantidade = self.parte.representantes.count()
        adicionar = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/novo/",
            {"tipo": "interno", "usuario": self.user.pk},
            HTTP_HOST=self.http_host,
        )
        remover = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/"
            f"{self.representante.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        classificar = self.client.post(
            self._url_classificacao(self.parte),
            {"tipo": "autor", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(adicionar.status_code, 404)
        self.assertEqual(remover.status_code, 404)
        self.assertEqual(classificar.status_code, 404)
        self.assertEqual(self.parte.representantes.count(), quantidade)
        self.parte.refresh_from_db()
        self.assertEqual(self.parte.qualificacao, "reu")
        self.assertTrue(
            RepresentanteParte.objects.filter(pk=self.representante.pk).exists()
        )

    def test_somente_seus_nao_modifica_advogado_de_processo_alheio(self):
        somente_seus = self._user("participantes_somente_seus")
        self._autorizar(somente_seus, "somente_seus")
        self.client.force_login(somente_seus)
        quantidade = self.parte.representantes.count()

        adicionar = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/novo/",
            {"tipo": "interno", "usuario": somente_seus.pk},
            HTTP_HOST=self.http_host,
        )
        remover = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/"
            f"{self.representante.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        classificar = self.client.post(
            self._url_classificacao(self.parte),
            {"tipo": "autor", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(adicionar.status_code, 404)
        self.assertEqual(remover.status_code, 404)
        self.assertEqual(classificar.status_code, 404)
        self.assertEqual(self.parte.representantes.count(), quantidade)

    def test_usuario_sem_modulo_recebe_403_nas_novas_acoes(self):
        sem_modulo = self._user("participantes_sem_modulo")
        self.client.force_login(sem_modulo)
        quantidade = self.parte.representantes.count()

        adicionar = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/novo/",
            {"tipo": "interno", "usuario": sem_modulo.pk},
            HTTP_HOST=self.http_host,
        )
        remover = self.client.post(
            f"/processos/{self.processo.pk}/partes/{self.parte.pk}/advogados/"
            f"{self.representante.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        classificar = self.client.post(
            self._url_classificacao(self.parte),
            {"tipo": "autor", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(adicionar.status_code, 403)
        self.assertEqual(remover.status_code, 403)
        self.assertEqual(classificar.status_code, 403)
        self.assertEqual(self.parte.representantes.count(), quantidade)


class TestParticipantesAdministrador(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0006_participantes_admin"

    def test_admin_adiciona_e_remove_advogado_em_processo_alheio(self):
        admin = self._admin("admin_participantes")
        dono = self._user("dono_participantes_admin")
        cliente = self._cliente(dono)
        processo = self._processo(dono, cliente, "Processo administrado")
        parte = ParteProcesso.objects.create(
            processo=processo,
            nome="Parte administrada",
            vinculo_escritorio="outro",
            posicao="polo_ativo",
            qualificacao="autor",
        )
        self.client.force_login(admin)

        adicionar = self.client.post(
            f"/processos/{processo.pk}/partes/{parte.pk}/advogados/novo/",
            {"tipo": "interno", "usuario": admin.pk},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(adicionar.status_code, 302)
        representante = parte.representantes.get()
        remover = self.client.post(
            f"/processos/{processo.pk}/partes/{parte.pk}/advogados/"
            f"{representante.pk}/remover/",
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(remover.status_code, 302)
        self.assertFalse(parte.representantes.exists())

        classificar = self.client.post(
            f"/processos/{processo.pk}/partes/{parte.pk}/classificacao/",
            {"tipo": "reu", "atuacao_ministerio_publico": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(classificar.status_code, 302)
        parte.refresh_from_db()
        self.assertEqual(parte.qualificacao, "reu")
        self.assertEqual(parte.historico_classificacao.get().usuario_id, admin.pk)
