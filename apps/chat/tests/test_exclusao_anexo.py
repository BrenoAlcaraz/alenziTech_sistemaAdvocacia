"""
Testes de limpeza de arquivo ao excluir Mensagem com anexo.

Não há hoje uma view de exclusão de mensagem/conversa no Chat, mas o
model tem FileField e é registrado no Django Admin — o signal
post_delete (apps/chat/signals.py) cobre qualquer caminho de exclusão
(admin, cascata por Conversa excluída, shell), não só uma view futura.

Reaproveita a fixture de apps/chat/tests/test_anexos.py.
"""

import os

from apps.chat.models import Conversa, Mensagem
from apps.chat.tests.test_anexos import ChatAnexosBase, _anexo


class TestExclusaoDeAnexoDeMensagem(ChatAnexosBase):
    @classmethod
    def get_test_schema_name(cls):
        return "chat_anexo_exclusao"

    def setUp(self):
        super().setUp()
        self.ana = self._user("ana_exclusao")
        self.bruno = self._user("bruno_exclusao")
        for user in (self.ana, self.bruno):
            self._dar_acesso_chat(user)
        self.client.force_login(self.ana)
        self.client.post(
            "/chat/nova/individual/", {"usuario": self.bruno.pk}, HTTP_HOST=self.http_host
        )
        self.conversa = Conversa.objects.get(tipo=Conversa.TIPO_INDIVIDUAL)
        self.client.post(
            f"/chat/{self.conversa.pk}/",
            {"conteudo": "", "anexo": _anexo(conteudo=b"conteudo-a-excluir")},
            HTTP_HOST=self.http_host,
        )
        self.mensagem = Mensagem.objects.get(conversa=self.conversa)

    def test_excluir_mensagem_remove_arquivo_do_storage(self):
        caminho_arquivo = self.mensagem.anexo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        self.mensagem.delete()

        self.assertFalse(os.path.exists(caminho_arquivo))

    def test_excluir_conversa_remove_arquivo_em_cascata(self):
        caminho_arquivo = self.mensagem.anexo.path
        self.assertTrue(os.path.exists(caminho_arquivo))

        self.conversa.delete()

        self.assertFalse(Mensagem.objects.filter(pk=self.mensagem.pk).exists())
        self.assertFalse(os.path.exists(caminho_arquivo))

    def test_excluir_mensagem_sem_anexo_nao_falha(self):
        self.client.post(
            f"/chat/{self.conversa.pk}/", {"conteudo": "sem anexo"}, HTTP_HOST=self.http_host
        )
        mensagem_sem_anexo = Mensagem.objects.get(conteudo="sem anexo")
        mensagem_sem_anexo.delete()
        self.assertFalse(Mensagem.objects.filter(pk=mensagem_sem_anexo.pk).exists())
