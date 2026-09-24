// Testes de static/js/formularios.js (confirmação e envio em andamento).
// Rodar: npm run test:js  (node:test, sem dependências; DOM mínimo simulado).

const test = require("node:test");
const assert = require("node:assert/strict");
const { instalar, rotuloEmAndamento } = require("../../static/js/formularios.js");

const proximoCiclo = () => new Promise((resolve) => setTimeout(resolve, 0));

class Alvo {
  constructor() { this.ouvintes = {}; }
  addEventListener(tipo, fn) { (this.ouvintes[tipo] ||= []).push(fn); }
  disparar(tipo, evento = {}) { (this.ouvintes[tipo] || []).forEach((fn) => fn(evento)); return evento; }
}

function criarBotao(texto, dataset = {}, filhos = []) {
  const b = new Alvo();
  Object.assign(b, {
    tagName: "BUTTON", textContent: texto, children: filhos, dataset: { ...dataset },
    disabled: false, isConnected: true, focado: false,
    focus() { b.focado = true; }, getAttribute: () => null,
    click() { b.disparar("click", {}); },
  });
  return b;
}

function criarDocumento({ comDialogo = true } = {}) {
  const doc = new Alvo();
  doc.enviados = [];
  // Envia pelo mesmo caminho do navegador: handlers do form, depois o documento.
  doc.submeter = (form, submitter) => {
    const evento = { target: form, submitter, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
    (form.aoEnviar || []).forEach((fn) => fn(evento));
    doc.disparar("submit", evento);
    if (!evento.defaultPrevented) doc.enviados.push({ form, submitter });
    return evento;
  };

  let dialogo = null;
  if (comDialogo) {
    const partes = {
      "[data-confirmar-titulo]": { textContent: "", hidden: false },
      "[data-confirmar-registro]": { textContent: "", hidden: true },
      "[data-confirmar-texto]": { textContent: "", hidden: false },
      "[data-confirmar-preserva]": { textContent: "", hidden: true },
      "[data-confirmar-ok]": criarBotao(""),
      "[data-fechar-dialogo]": criarBotao("Cancelar"),
    };
    dialogo = new Alvo();
    Object.assign(dialogo, {
      open: false, partes,
      querySelector: (seletor) => partes[seletor],
      showModal() { dialogo.open = true; },
      close() { dialogo.open = false; dialogo.disparar("close"); },
    });
  }
  doc.dialogo = dialogo;
  doc.querySelector = (seletor) => (seletor === "[data-dialogo-confirmacao]" ? dialogo : null);
  doc.querySelectorAll = () => [];
  doc.defaultView = null;
  return doc;
}

function criarFormulario(doc, metodo, botao) {
  const attrs = { method: metodo };
  return {
    dataset: {}, attrs, aoEnviar: [],
    getAttribute: (nome) => (nome in attrs ? attrs[nome] : null),
    setAttribute: (nome, valor) => { attrs[nome] = valor; },
    removeAttribute: (nome) => { delete attrs[nome]; },
    querySelector: () => botao,
    requestSubmit(submitter) { doc.submeter(this, submitter); },
  };
}

test("duplo clique em Criar lançamento envia o formulário uma única vez", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Criar lançamento");
  const form = criarFormulario(doc, "post", botao);

  const primeiro = doc.submeter(form, botao);
  const segundo = doc.submeter(form, botao);

  assert.equal(primeiro.defaultPrevented, false);
  assert.equal(segundo.defaultPrevented, true);
  assert.equal(doc.enviados.length, 1);
  assert.equal(form.attrs["aria-busy"], "true");

  // Botão ainda habilitado no próprio evento (mantém name/value no envio).
  assert.equal(botao.disabled, false);
  await proximoCiclo();
  assert.equal(botao.disabled, true);
  assert.equal(botao.textContent, "Criando…");
});

test("envio por Enter (sem submitter) também bloqueia o segundo envio", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Salvar alterações");
  const form = criarFormulario(doc, "POST", botao);

  doc.submeter(form, null);
  doc.submeter(form, null);
  await proximoCiclo();

  assert.equal(doc.enviados.length, 1);
  assert.equal(botao.textContent, "Salvando…");
});

test("formulário GET (filtros) não é bloqueado", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Filtrar");
  const form = criarFormulario(doc, "get", botao);

  doc.submeter(form, botao);
  doc.submeter(form, botao);
  await proximoCiclo();

  assert.equal(doc.enviados.length, 2);
  assert.equal(botao.disabled, false);
});

test("envio cancelado pelo próprio formulário não fica em andamento", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Salvar");
  const form = criarFormulario(doc, "post", botao);
  let bloquear = true;
  form.aoEnviar.push((evento) => { if (bloquear) evento.preventDefault(); });

  doc.submeter(form, botao);
  bloquear = false;
  doc.submeter(form, botao);

  assert.equal(doc.enviados.length, 1);
});

test("botão só de ícone é desabilitado sem perder o conteúdo", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("", {}, [{ tagName: "svg" }]);
  const form = criarFormulario(doc, "post", botao);

  doc.submeter(form, botao);
  await proximoCiclo();

  assert.equal(botao.disabled, true);
  assert.equal(botao.textContent, "");
});

test("ação com data-confirmar abre o diálogo com foco no Cancelar e só envia ao confirmar", async () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Excluir", {
    confirmar: "Excluir este documento?",
    confirmarRegistro: "contrato.pdf",
    confirmarTexto: "Esta ação não pode ser desfeita.",
    confirmarAcao: "Excluir documento",
  });
  const form = criarFormulario(doc, "post", botao);
  const partes = doc.dialogo.partes;

  const evento = doc.submeter(form, botao);

  assert.equal(evento.defaultPrevented, true);
  assert.equal(doc.enviados.length, 0);
  assert.equal(doc.dialogo.open, true);
  assert.equal(partes["[data-fechar-dialogo]"].focado, true);
  assert.equal(partes["[data-confirmar-titulo]"].textContent, "Excluir este documento?");
  assert.equal(partes["[data-confirmar-registro]"].textContent, "contrato.pdf");
  assert.equal(partes["[data-confirmar-registro]"].hidden, false);
  assert.equal(partes["[data-confirmar-preserva]"].hidden, true);
  assert.equal(partes["[data-confirmar-ok]"].textContent, "Excluir documento");
  assert.equal(partes["[data-confirmar-ok]"].className, "btn-danger");

  partes["[data-confirmar-ok]"].click();

  assert.equal(doc.dialogo.open, false);
  assert.equal(doc.enviados.length, 1);
  assert.equal(doc.enviados[0].submitter, botao);
});

test("cancelar (ou Esc) não envia e devolve o foco ao botão de origem", () => {
  const doc = criarDocumento();
  instalar(doc);
  const botao = criarBotao("Arquivar processo", { confirmar: "Arquivar este processo?", confirmarTom: "neutro" });
  const form = criarFormulario(doc, "post", botao);

  doc.submeter(form, botao);
  assert.equal(doc.dialogo.partes["[data-confirmar-ok]"].className, "btn-primary");
  assert.equal(doc.dialogo.partes["[data-confirmar-ok]"].textContent, "Arquivar processo");

  // Esc fecha o <dialog> nativamente e dispara "close", como o Cancelar.
  doc.dialogo.close();

  assert.equal(doc.enviados.length, 0);
  assert.equal(botao.focado, true);
  assert.equal(form.dataset.enviando, undefined);

  // Reabrir depois de cancelar volta a pedir confirmação.
  const denovo = doc.submeter(form, botao);
  assert.equal(denovo.defaultPrevented, true);
  assert.equal(doc.dialogo.open, true);
});

test("rótulo em andamento acompanha o verbo da ação", () => {
  assert.equal(rotuloEmAndamento("Salvar alterações"), "Salvando…");
  assert.equal(rotuloEmAndamento("Excluir"), "Excluindo…");
  assert.equal(rotuloEmAndamento("Gerar procuração"), "Gerando…");
  assert.equal(rotuloEmAndamento("Mensagem"), "Enviando…");
});
