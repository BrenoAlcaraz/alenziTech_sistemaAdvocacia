from django.apps import apps as django_apps
from django.core.exceptions import ValidationError

from apps.accounts.permissoes_constants import NIVEL_TODOS
from apps.clientes.models import Cliente
from apps.processos.forms import ParteProcessoForm
from apps.processos.models import ParteProcesso, Processo
from apps.processos.services import normalizar_documento

from .test_escopo import ProcessosEscopoBase


class TestParticipantesProcessuais(ProcessosEscopoBase):
    """Cobre o modelo de Partes simplificado (PDR-0013)."""

    @classmethod
    def get_test_schema_name(cls):
        return "pdr0013_partes"

    def setUp(self):
        super().setUp()
        self.user = self._user("responsavel_partes")
        self.user.first_name = "Ana"
        self.user.last_name = "Interna"
        self.user.save(update_fields=["first_name", "last_name"])
        self._autorizar(self.user, NIVEL_TODOS)
        self.cliente = self._cliente(self.user, "Cliente do Processo")
        self.cliente.cpf_cnpj = "123.456.789-00"
        self.cliente.save(update_fields=["cpf_cnpj"])
        self.processo = self._processo(self.user, self.cliente, "Processo PDR-0013")
        self.client.force_login(self.user)

    def _url_parte(self, processo=None):
        processo = processo or self.processo
        return f"/processos/{processo.pk}/partes/nova/"

    def _url_editar(self, parte, processo=None):
        processo = processo or parte.processo
        return f"/processos/{processo.pk}/partes/{parte.pk}/editar/"

    def _adicionar_parte(self, papel="autor", **extra):
        payload = {"papel": papel, "nome": f"Parte {papel}", "cpf_cnpj": ""}
        payload.update(extra)
        return self.client.post(
            self._url_parte(),
            payload,
            HTTP_HOST=self.http_host,
        )

    def _parte(self, **kwargs):
        defaults = {
            "processo": self.processo,
            "papel": "autor",
            "nome": "Parte existente",
        }
        defaults.update(kwargs)
        return ParteProcesso.objects.create(**defaults)

    def test_entidades_do_modelo_antigo_nao_existem_mais(self):
        for nome_modelo in (
            "AutoridadeProcessual",
            "RepresentanteParte",
            "HistoricoClassificacaoParte",
        ):
            with self.subTest(modelo=nome_modelo):
                with self.assertRaises(LookupError):
                    django_apps.get_model("processos", nome_modelo)

    def test_criacao_do_processo_nao_cria_parte_automatica(self):
        self.assertEqual(self.processo.partes.count(), 0)

        cliente = self._cliente(self.user, "Outro cliente")
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
        self.assertEqual(processo.partes.count(), 0)

    def test_cada_papel_cria_parte_no_grupo_visual_correto(self):
        for papel, grupo in ParteProcesso.GRUPO_POR_PAPEL.items():
            with self.subTest(papel=papel):
                resposta = self._adicionar_parte(papel, nome=f"Parte grupo {papel}")
                self.assertEqual(resposta.status_code, 302)
                parte = ParteProcesso.objects.get(
                    processo=self.processo,
                    nome=f"Parte grupo {papel}",
                )
                self.assertEqual(parte.papel, papel)
                self.assertEqual(parte.grupo_visual, grupo)

    def test_grupos_visuais_agrupam_os_dez_papeis(self):
        grupos = dict(ParteProcessoForm.GRUPOS_PAPEL)
        self.assertEqual(set(grupos.keys()), {"Polo Ativo", "Polo Passivo", "Outros"})
        valores = {valor for opcoes in grupos.values() for valor, _ in opcoes}
        self.assertEqual(valores, set(dict(ParteProcesso.PAPEL_CHOICES).keys()))
        self.assertIn("juiz", dict(grupos["Outros"]))
        self.assertIn("ministerio_publico", dict(grupos["Outros"]))

    def test_juiz_e_um_papel_da_parte_sem_entidade_separada(self):
        resposta = self._adicionar_parte("juiz", nome="Juíza Maria")
        self.assertEqual(resposta.status_code, 302)
        parte = ParteProcesso.objects.get(processo=self.processo, papel="juiz")
        self.assertEqual(parte.grupo_visual, "outros")
        self.assertFalse(hasattr(parte, "vara_orgao"))
        self.assertFalse(hasattr(parte, "observacao"))

    def test_nome_obrigatorio_papel_obrigatorio_cpf_cnpj_opcional(self):
        formulario = ParteProcessoForm({"papel": "autor", "nome": "", "cpf_cnpj": ""})
        self.assertFalse(formulario.is_valid())
        self.assertIn("nome", formulario.errors)

        formulario = ParteProcessoForm({"papel": "", "nome": "Nome válido"})
        self.assertFalse(formulario.is_valid())
        self.assertIn("papel", formulario.errors)

        formulario = ParteProcessoForm({"papel": "autor", "nome": "Nome válido"})
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_nome_em_branco_e_rejeitado_pelo_model(self):
        with self.assertRaises(ValidationError):
            self._parte(nome="   ")

    def test_advogado_prefill_quando_parte_corresponde_ao_cliente_do_processo(self):
        self.assertEqual(normalizar_documento("123.456.789-00"), "12345678900")
        resposta = self._adicionar_parte(
            "autor",
            nome="Parte do próprio cliente",
            cpf_cnpj="123.456.789-00",
        )
        self.assertEqual(resposta.status_code, 302)
        parte = ParteProcesso.objects.get(nome="Parte do próprio cliente")
        self.assertEqual(parte.advogado_nome, "Ana Interna")
        self.assertEqual(parte.advogado_oab, "")

    def test_advogado_nao_e_preenchido_quando_documento_nao_corresponde(self):
        outro_cliente = Cliente.objects.create(
            nome_razao_social="Outro cliente",
            tipo="PF",
            cpf_cnpj="999.999.999-99",
            responsavel=self.user,
        )
        casos = [
            ("documento_diferente", "000.000.000-00"),
            ("documento_vazio", ""),
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
                self.assertEqual(parte.advogado_nome, "")

    def test_advogado_informado_pelo_usuario_nao_e_sobrescrito(self):
        resposta = self._adicionar_parte(
            "autor",
            nome="Parte com advogado próprio",
            cpf_cnpj="123.456.789-00",
            advogado_nome="Advogado Externo",
            advogado_oab="99999",
        )
        self.assertEqual(resposta.status_code, 302)
        parte = ParteProcesso.objects.get(nome="Parte com advogado próprio")
        self.assertEqual(parte.advogado_nome, "Advogado Externo")
        self.assertEqual(parte.advogado_oab, "99999")

    def test_editar_parte_atualiza_papel_nome_e_advogado_preservando_pk(self):
        parte = self._parte(papel="autor", nome="Nome original")
        pk_original = parte.pk

        resposta = self.client.post(
            self._url_editar(parte),
            {
                "papel": "reu",
                "nome": "Nome atualizado",
                "cpf_cnpj": "",
                "advogado_nome": "Advogado Atualizado",
                "advogado_oab": "12345",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        parte.refresh_from_db()
        self.assertEqual(parte.pk, pk_original)
        self.assertEqual(parte.papel, "reu")
        self.assertEqual(parte.nome, "Nome atualizado")
        self.assertEqual(parte.advogado_nome, "Advogado Atualizado")
        self.assertEqual(parte.advogado_oab, "12345")

    def test_editar_parte_pode_limpar_advogado(self):
        parte = self._parte(advogado_nome="Advogado antigo", advogado_oab="111")
        resposta = self.client.post(
            self._url_editar(parte),
            {"papel": "autor", "nome": parte.nome, "cpf_cnpj": "", "advogado_nome": "", "advogado_oab": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        parte.refresh_from_db()
        self.assertEqual(parte.advogado_nome, "")
        self.assertEqual(parte.advogado_oab, "")

    def test_detalhe_exibe_parte_e_advogado(self):
        self._parte(nome="Maria da Silva", advogado_nome="João Souza", advogado_oab="123456")
        resposta = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertContains(resposta, "Maria da Silva")
        self.assertContains(resposta, "João Souza")
        self.assertContains(resposta, "123456")

    def test_form_adicionar_parte_oferece_reaproveitar_dados_do_cliente(self):
        resposta = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertContains(resposta, "Usar dados do Cliente do processo")
        self.assertContains(resposta, self.cliente.nome_razao_social)
        # cpf_cnpj vai para dentro de um literal JS: o hífen é escapado por
        # `escapejs` (-), então comparamos só o trecho sem hífen.
        self.assertContains(resposta, "123.456.789")

    def test_form_adicionar_parte_nao_oferece_reaproveitar_sem_cliente_no_processo(self):
        processo_sem_cliente = Processo.objects.create(
            titulo="Processo sem cliente",
            cliente=None,
            responsavel=self.user,
        )
        resposta = self.client.get(
            f"/processos/{processo_sem_cliente.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertNotContains(resposta, "Usar dados do Cliente do processo")


class TestParticipantesIdor(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0013_partes_idor"

    def setUp(self):
        super().setUp()
        self.user = self._user("leitor_todos_partes")
        self.dono = self._user("dono_processo_alheio_partes")
        self._autorizar(self.user, NIVEL_TODOS)
        cliente = self._cliente(self.dono)
        self.processo = self._processo(self.dono, cliente, "Processo alheio")
        self.parte = ParteProcesso.objects.create(
            processo=self.processo,
            papel="reu",
            nome="Parte alheia",
        )
        self.client.force_login(self.user)

    def _url_editar(self, parte):
        return f"/processos/{parte.processo_id}/partes/{parte.pk}/editar/"

    def test_todos_le_processo_mas_nao_edita_parte(self):
        detalhe = self.client.get(
            f"/processos/{self.processo.pk}/",
            {"aba": "partes"},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(detalhe.status_code, 200)
        self.assertFalse(detalhe.context["pode_modificar"])
        self.assertNotContains(detalhe, "Editar parte")

        editar = self.client.post(
            self._url_editar(self.parte),
            {"papel": "autor", "nome": "Invadida", "cpf_cnpj": "", "advogado_nome": "", "advogado_oab": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(editar.status_code, 404)
        self.parte.refresh_from_db()
        self.assertEqual(self.parte.papel, "reu")
        self.assertEqual(self.parte.nome, "Parte alheia")

    def test_somente_seus_nao_edita_parte_de_processo_alheio(self):
        somente_seus = self._user("participantes_somente_seus_partes")
        self._autorizar(somente_seus, "somente_seus")
        self.client.force_login(somente_seus)

        editar = self.client.post(
            self._url_editar(self.parte),
            {"papel": "autor", "nome": "Invadida", "cpf_cnpj": "", "advogado_nome": "", "advogado_oab": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(editar.status_code, 404)
        self.parte.refresh_from_db()
        self.assertEqual(self.parte.nome, "Parte alheia")

    def test_usuario_sem_modulo_recebe_403(self):
        sem_modulo = self._user("participantes_sem_modulo_partes")
        self.client.force_login(sem_modulo)

        editar = self.client.post(
            self._url_editar(self.parte),
            {"papel": "autor", "nome": "Invadida", "cpf_cnpj": "", "advogado_nome": "", "advogado_oab": ""},
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(editar.status_code, 403)
        self.parte.refresh_from_db()
        self.assertEqual(self.parte.nome, "Parte alheia")


class TestParticipantesAdministrador(ProcessosEscopoBase):
    @classmethod
    def get_test_schema_name(cls):
        return "pdr0013_partes_admin"

    def test_admin_edita_parte_em_processo_alheio(self):
        admin = self._admin("admin_participantes_partes")
        dono = self._user("dono_participantes_admin_partes")
        cliente = self._cliente(dono)
        processo = self._processo(dono, cliente, "Processo administrado")
        parte = ParteProcesso.objects.create(
            processo=processo,
            papel="autor",
            nome="Parte administrada",
        )
        self.client.force_login(admin)

        resposta = self.client.post(
            f"/processos/{processo.pk}/partes/{parte.pk}/editar/",
            {
                "papel": "reu",
                "nome": "Parte administrada",
                "cpf_cnpj": "",
                "advogado_nome": "",
                "advogado_oab": "",
            },
            HTTP_HOST=self.http_host,
        )
        self.assertEqual(resposta.status_code, 302)
        parte.refresh_from_db()
        self.assertEqual(parte.papel, "reu")
