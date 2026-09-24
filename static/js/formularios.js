// ─── formularios.js ──────────────────────────────────────────────────────────
// Confirmação de ação (diálogo único, components/dialogo_confirmacao.html) e
// envio em andamento de todo formulário POST. Só interface: autorização e
// validação continuam no backend.
//
// Um único ouvinte de "submit" no documento (fase de bolha): handlers do
// próprio formulário rodam antes e, se cancelarem o envio, nada acontece aqui.

(function () {
  // "Salvar" → "Salvando…", "Excluir" → "Excluindo…", "Gerar" → "Gerando…".
  function rotuloEmAndamento(rotulo) {
    const palavras = rotulo.trim().split(/\s+/);
    const verbo = palavras[0] || "";
    const gerundio = verbo.replace(/ar$/i, "ando").replace(/er$/i, "endo").replace(/ir$/i, "indo");
    if (gerundio === verbo) return "Enviando…";
    return gerundio + "…";
  }

  function botaoDeEnvio(form, submitter) {
    return submitter || form.querySelector('button[type="submit"], button:not([type]), input[type="submit"]');
  }

  function marcarEnviando(form, botao) {
    form.dataset.enviando = "1";
    form.setAttribute("aria-busy", "true");
    if (!botao) return;
    // Desabilitar dentro do próprio evento tiraria name/value do botão dos
    // dados enviados; por isso fica para o próximo ciclo.
    setTimeout(() => {
      botao.disabled = true;
      // Botão só de ícone (ou ícone + texto) mantém o conteúdo; só troca
      // rótulo quando é texto puro, para não sumir com o ícone.
      if (botao.tagName === "INPUT") {
        botao.dataset.rotuloOriginal = botao.value;
        botao.value = botao.dataset.enviandoRotulo || rotuloEmAndamento(botao.value);
      } else if (botao.children.length === 0) {
        botao.dataset.rotuloOriginal = botao.textContent;
        botao.textContent = botao.dataset.enviandoRotulo || rotuloEmAndamento(botao.textContent);
      }
    }, 0);
  }

  // Voltar pelo histórico (bfcache) devolve a página como estava: reabilita.
  function restaurarEnvios(doc) {
    doc.querySelectorAll("form[data-enviando]").forEach((form) => {
      delete form.dataset.enviando;
      form.removeAttribute("aria-busy");
      form.querySelectorAll("[data-rotulo-original]").forEach((botao) => {
        if (botao.tagName === "INPUT") botao.value = botao.dataset.rotuloOriginal;
        else botao.textContent = botao.dataset.rotuloOriginal;
        delete botao.dataset.rotuloOriginal;
      });
      form.querySelectorAll("button:disabled, input[type=submit]:disabled").forEach((b) => { b.disabled = false; });
    });
  }

  function preencherTexto(elemento, texto) {
    elemento.textContent = texto || "";
    elemento.hidden = !texto;
  }

  function instalar(doc) {
    const dialogo = doc.querySelector("[data-dialogo-confirmacao]");
    let pendente = null; // { form, botao }
    let abrir = null;

    if (dialogo) {
      const ok = dialogo.querySelector("[data-confirmar-ok]");
      const cancelar = dialogo.querySelector("[data-fechar-dialogo]");

      ok.addEventListener("click", () => {
        const { form, botao } = pendente;
        form.dataset.confirmado = "1";
        dialogo.close();
        form.requestSubmit(botao);
      });
      cancelar.addEventListener("click", () => dialogo.close());
      // Esc dispara "cancel" e fecha nativamente; em qualquer saída o foco
      // volta ao botão que abriu o diálogo.
      dialogo.addEventListener("close", () => {
        if (pendente && pendente.botao.isConnected) pendente.botao.focus();
        pendente = null;
      });

      abrir = (form, botao) => {
        const d = botao.dataset;
        pendente = { form, botao };
        preencherTexto(dialogo.querySelector("[data-confirmar-titulo]"), d.confirmar);
        preencherTexto(dialogo.querySelector("[data-confirmar-registro]"), d.confirmarRegistro);
        preencherTexto(dialogo.querySelector("[data-confirmar-texto]"), d.confirmarTexto);
        preencherTexto(dialogo.querySelector("[data-confirmar-preserva]"), d.confirmarPreserva);
        ok.textContent = d.confirmarAcao || botao.getAttribute("aria-label") || botao.textContent.trim();
        ok.className = d.confirmarTom === "neutro" ? "btn-primary" : "btn-danger";
        dialogo.showModal();
        cancelar.focus();
      };
    }

    doc.addEventListener("submit", (evento) => {
      if (evento.defaultPrevented) return;
      const form = evento.target;

      if (form.dataset.enviando) {
        evento.preventDefault();
        return;
      }

      const botao = botaoDeEnvio(form, evento.submitter);
      const pedeConfirmacao = botao && botao.dataset.confirmar !== undefined;
      if (pedeConfirmacao && !form.dataset.confirmado && abrir) {
        evento.preventDefault();
        abrir(form, botao);
        return;
      }
      delete form.dataset.confirmado;

      if ((form.getAttribute("method") || "get").toLowerCase() !== "post") return;
      marcarEnviando(form, botao);
    });

    const janela = doc.defaultView;
    if (janela) {
      janela.addEventListener("pageshow", (evento) => {
        if (evento.persisted) restaurarEnvios(doc);
      });
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { instalar, rotuloEmAndamento };
  } else {
    document.addEventListener("DOMContentLoaded", () => instalar(document));
  }
})();
