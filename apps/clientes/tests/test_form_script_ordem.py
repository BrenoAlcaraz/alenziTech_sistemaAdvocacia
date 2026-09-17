"""
Regressão: o script inline de `clientes/form.html` lançava
TypeError ("Cannot read properties of undefined (reading 'checked')")
na carga da página, porque a primeira chamada de `selecionarTipo(...)`
disparava `aplicarMascaraDocumento()`, que lê `campoEstrangeiro`/
`campoDocumento` antes desses `var` serem atribuídos (hoisting deixa a
declaração como `undefined` até a linha de atribuição executar). Isso
interrompia o restante do script sem nenhum erro visível na tela —
inclusive os listeners de blur/input do CEP mais abaixo, que nunca
chegavam a ser registrados, quebrando a busca automática de endereço
por CEP (ViaCEP) documentada em docs/PRODUCT.md (seção Clientes).

Não há harness de execução de JS neste repositório (ver
docs/development/COMMANDS.md — Node é só para build do Tailwind), então
a regressão é coberta estruturalmente: as declarações de
`campoDocumento`/`campoEstrangeiro` devem preceder, no HTML renderizado,
a primeira chamada de `selecionarTipo(...)`.
"""

from django.contrib.auth.models import User
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import HabilitacaoPapel, PapelAcesso, PermissaoPapel, UsuarioPapel
from apps.accounts.permissoes_constants import HAB_CLIENTES_CRIAR, MODULO_CLIENTES, NIVEL_TODOS


class TestClientesFormScriptOrdem(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls):
        return "wi0001_clientes_form_script_ordem"

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nome = "Clientes Form Script Ordem"
        tenant.slug = "clientes-form-script-ordem"

    def setUp(self):
        super().setUp()
        from apps.saas_tenants.models import Dominio

        domain_obj = Dominio.objects.filter(tenant=self.tenant).first()
        self.http_host = domain_obj.domain if domain_obj else "localhost"

        self.user = User.objects.create_user(username="form_ordem", password="testpass")
        papel = PapelAcesso.objects.create(nome="Papel Clientes")
        UsuarioPapel.objects.create(usuario=self.user, papel=papel)
        PermissaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES,
            ativo=True, nivel=NIVEL_TODOS,
        )
        HabilitacaoPapel.objects.create(
            papel=papel, tipo_conta=None, modulo=MODULO_CLIENTES,
            item=HAB_CLIENTES_CRIAR, ativo=True,
        )
        self.client.force_login(self.user)

    def test_declaracoes_de_campoDocumento_e_campoEstrangeiro_precedem_selecionarTipo(self):
        r = self.client.get("/clientes/novo/", HTTP_HOST=self.http_host)
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")

        idx_chamada = html.index('selecionarTipo(document.getElementById("id_tipo").value')
        idx_doc = html.index('var campoDocumento = document.getElementById("id_cpf_cnpj")')
        idx_estrangeiro = html.index('var campoEstrangeiro = document.getElementById("id_estrangeiro")')

        self.assertLess(
            idx_doc, idx_chamada,
            "campoDocumento precisa ser atribuído antes da primeira chamada de "
            "selecionarTipo(), que aciona aplicarMascaraDocumento() e lê essa variável.",
        )
        self.assertLess(
            idx_estrangeiro, idx_chamada,
            "campoEstrangeiro precisa ser atribuído antes da primeira chamada de "
            "selecionarTipo(), que aciona aplicarMascaraDocumento() e lê essa variável.",
        )
