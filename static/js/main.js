// ─── main.js ─────────────────────────────────────────────────────────────────
// JS mínimo para interações visuais da fase estrutural.
// Sem lógica de negócio real — apenas toggles e navegação visual.

document.addEventListener("DOMContentLoaded", () => {

  // ── Toggle sidebar mobile (futuramente) ─────────────────────────────────────
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("-translate-x-full");
    });
  }

  // ── Tabs internas ───────────────────────────────────────────────────────────
  // Abas com data-tab e data-tab-panel para alternância visual sem JS avançado
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const group = tab.dataset.tabGroup;
      const target = tab.dataset.tab;

      // Desativa todas as abas do mesmo grupo
      document.querySelectorAll(`[data-tab-group="${group}"]`).forEach((t) => {
        t.classList.remove("tab-active");
        t.classList.add("tab-inactive");
      });

      // Oculta todos os painéis do mesmo grupo
      document.querySelectorAll(`[data-tab-panel-group="${group}"]`).forEach((p) => {
        p.classList.add("hidden");
      });

      // Ativa a aba clicada
      tab.classList.add("tab-active");
      tab.classList.remove("tab-inactive");

      // Exibe o painel correspondente
      const panel = document.querySelector(`[data-tab-panel="${target}"][data-tab-panel-group="${group}"]`);
      if (panel) panel.classList.remove("hidden");
    });
  });

  // ── Alternância Quadro / Lista em Tarefas ───────────────────────────────────
  document.querySelectorAll("[data-view-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.viewToggle;
      document.querySelectorAll("[data-view]").forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.view !== view);
      });
      document.querySelectorAll("[data-view-toggle]").forEach((b) => {
        b.classList.toggle("bg-white", b.dataset.viewToggle === view);
        b.classList.toggle("text-gray-900", b.dataset.viewToggle === view);
        b.classList.toggle("text-gray-500", b.dataset.viewToggle !== view);
      });
    });
  });

  // ── Fechar alertas ──────────────────────────────────────────────────────────
  document.querySelectorAll("[data-dismiss-alert]").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest("[data-alert]")?.remove();
    });
  });

  // ── Campos condicionados a um <select> (ex: classificação Única/Recorrente) ──
  // <select data-toggle-select="grupo"> mostra/esconde <... data-toggle-panel="grupo"
  // data-toggle-values="valor1,valor2"> conforme o valor atual do select.
  document.querySelectorAll("[data-toggle-select]").forEach((select) => {
    const grupo = select.dataset.toggleSelect;
    const atualizar = () => {
      document.querySelectorAll(`[data-toggle-panel="${grupo}"]`).forEach((panel) => {
        const valores = (panel.dataset.toggleValues || "").split(",");
        panel.classList.toggle("hidden", !valores.includes(select.value));
      });
    };
    select.addEventListener("change", atualizar);
    atualizar();
  });

  // ── Filtro de Processo por Cliente ──────────────────────────────────────────
  // O campo Processo (marcado com data-processos-url) acompanha o Cliente
  // (marcado com data-cliente-filtro) do mesmo <form>, sem recarregar a página.
  document.querySelectorAll("[data-processos-url]").forEach((processoSelect) => {
    const form = processoSelect.closest("form");
    const clienteSelect = form?.querySelector("[data-cliente-filtro]");
    if (!clienteSelect) return;

    const url = processoSelect.dataset.processosUrl;
    const opcoesOriginais = Array.from(processoSelect.options).map((o) => o.cloneNode(true));

    clienteSelect.addEventListener("change", () => {
      const clienteId = clienteSelect.value;

      if (!clienteId) {
        processoSelect.innerHTML = "";
        opcoesOriginais.forEach((o) => processoSelect.appendChild(o.cloneNode(true)));
        processoSelect.disabled = false;
        return;
      }

      fetch(`${url}?cliente=${encodeURIComponent(clienteId)}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((r) => r.json())
        .then((data) => {
          processoSelect.innerHTML = "";
          const vazio = document.createElement("option");
          vazio.value = "";
          vazio.textContent = data.processos.length ? "Nenhum" : "Nenhum processo para este cliente";
          processoSelect.appendChild(vazio);
          data.processos.forEach(({ id, label }) => {
            const opt = document.createElement("option");
            opt.value = id;
            opt.textContent = label;
            processoSelect.appendChild(opt);
          });
          processoSelect.disabled = data.processos.length === 0;
        });
    });
  });

  // ── Busca em campo de Processo (combobox) ───────────────────────────────────
  // Todo <select> de Processo leva data-processo-busca="1" (ver
  // PROCESSO_SELECT_ATTRS em apps/processos/forms.py). Envolve o <select>
  // original (mantido no DOM, só oculto — sem display:none/hidden, para não
  // quebrar o foco por Tab) com um campo de texto que filtra as opções
  // exibidas numa lista customizada, e mantém os dois sincronizados nos dois
  // sentidos. Reaproveitável por qualquer formulário: nenhuma template
  // precisa de alteração, o data-* já sai no widget renderizado.
  document.querySelectorAll("[data-processo-busca]").forEach((select) => {
    const classeOriginal = select.className;
    const placeholder = select.dataset.processoBuscaPlaceholder || "Digite para buscar um processo...";

    // Backend é a autoridade: a validação nativa do navegador não alcança um
    // <select> oculto (bloqueia o submit em silêncio, sem mensagem visível,
    // em qualquer campo required) — required continua garantido em
    // form.is_valid() no servidor.
    select.required = false;
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    select.className = "sr-only";

    const wrapper = document.createElement("div");
    wrapper.className = "relative";
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);

    const input = document.createElement("input");
    input.type = "text";
    input.autocomplete = "off";
    input.className = classeOriginal;
    input.placeholder = placeholder;
    wrapper.insertBefore(input, select);

    const lista = document.createElement("ul");
    lista.className = "absolute z-20 mt-1 w-full max-h-60 overflow-y-auto rounded-xl border border-gray-100 bg-white shadow-lg hidden";
    wrapper.appendChild(lista);

    if (select.id) {
      const rotulo = document.querySelector(`label[for="${select.id}"]`);
      if (rotulo) rotulo.addEventListener("click", (e) => {
        e.preventDefault();
        input.focus();
      });
    }

    function opcoes() {
      return Array.from(select.options);
    }

    function sincronizarComSelecao() {
      const selecionada = select.options[select.selectedIndex];
      input.value = selecionada && selecionada.value ? selecionada.textContent : "";
      input.disabled = select.disabled;
    }

    function escolher(opcao) {
      select.value = opcao.value;
      sincronizarComSelecao();
      lista.classList.add("hidden");
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function destacar(indice) {
      Array.from(lista.children).forEach((item, i) => {
        item.classList.toggle("bg-gray-100", i === indice);
      });
      lista.children[indice]?.scrollIntoView({ block: "nearest" });
    }

    function criarItem(opcao) {
      const item = document.createElement("li");
      item.className = "cursor-pointer px-3 py-2 text-sm hover:bg-gray-100";
      item.textContent = opcao.value === "" ? (opcao.textContent || "Nenhum") : opcao.textContent;
      item.addEventListener("mousedown", (e) => {
        e.preventDefault(); // mantém o foco no input até processar o clique
        escolher(opcao);
      });
      return item;
    }

    function renderizarLista(termoDigitado) {
      const termo = termoDigitado.trim().toLowerCase();
      const filtradas = opcoes().filter((o) => o.textContent.toLowerCase().includes(termo));
      lista.innerHTML = "";
      if (!filtradas.length) {
        const vazio = document.createElement("li");
        vazio.className = "px-3 py-2 text-sm text-gray-400";
        vazio.textContent = "Nenhum processo encontrado.";
        lista.appendChild(vazio);
      } else {
        filtradas.forEach((o) => lista.appendChild(criarItem(o)));
      }
      lista.classList.remove("hidden");
      return filtradas;
    }

    let opcoesFiltradas = [];
    let indiceAtivo = -1;

    input.addEventListener("focus", () => {
      if (input.disabled) return;
      opcoesFiltradas = renderizarLista("");
      indiceAtivo = -1;
    });
    input.addEventListener("input", () => {
      opcoesFiltradas = renderizarLista(input.value);
      indiceAtivo = -1;
    });
    input.addEventListener("blur", () => {
      // Atraso para o mousedown do item processar antes do input perder o foco.
      setTimeout(() => lista.classList.add("hidden"), 150);
      sincronizarComSelecao();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        lista.classList.add("hidden");
      } else if (e.key === "ArrowDown" && opcoesFiltradas.length) {
        e.preventDefault();
        indiceAtivo = (indiceAtivo + 1) % opcoesFiltradas.length;
        destacar(indiceAtivo);
      } else if (e.key === "ArrowUp" && opcoesFiltradas.length) {
        e.preventDefault();
        indiceAtivo = (indiceAtivo - 1 + opcoesFiltradas.length) % opcoesFiltradas.length;
        destacar(indiceAtivo);
      } else if (e.key === "Enter" && !lista.classList.contains("hidden") && opcoesFiltradas.length) {
        e.preventDefault();
        escolher(opcoesFiltradas[indiceAtivo >= 0 ? indiceAtivo : 0]);
      }
    });

    document.addEventListener("click", (e) => {
      if (!wrapper.contains(e.target)) lista.classList.add("hidden");
    });

    // Mantém a busca sincronizada quando outro script troca as <option> do
    // <select> em tempo real (ex.: "Filtro de Processo por Cliente", acima).
    new MutationObserver(sincronizarComSelecao).observe(select, {
      childList: true,
      attributes: true,
      attributeFilter: ["disabled"],
    });

    sincronizarComSelecao();
  });

  // ── Disponibilidade de convidado (Agenda) ───────────────────────────────────
  // Ao marcar/selecionar um participante num container com
  // data-disponibilidade-url, consulta os compromissos que esse usuário já
  // tem no horário do formulário (campos data_hora_inicio/data_hora_fim da
  // página) e mostra o resultado no data-disponibilidade-resultado mais
  // próximo — nunca bloqueia o envio, é só informativo.
  document.querySelectorAll("[data-disponibilidade-url]").forEach((container) => {
    const url = container.dataset.disponibilidadeUrl;
    const campoInicio = document.querySelector('[name="data_hora_inicio"]');
    const campoFim = document.querySelector('[name="data_hora_fim"]');

    function escaparHtml(texto) {
      const div = document.createElement("div");
      div.textContent = texto;
      return div.innerHTML;
    }

    function elementoResultado(campo) {
      if (campo.type === "checkbox") {
        return document.getElementById(`disponibilidade-${campo.value}`);
      }
      return container.querySelector("[data-disponibilidade-resultado]");
    }

    function consultar(campo) {
      const resultado = elementoResultado(campo);
      if (!resultado) return;

      const usuarioId = campo.type === "checkbox" ? (campo.checked ? campo.value : "") : campo.value;
      if (!usuarioId || !campoInicio?.value) {
        resultado.innerHTML = "";
        return;
      }

      const params = new URLSearchParams({ usuario: usuarioId, inicio: campoInicio.value });
      if (campoFim?.value) params.set("fim", campoFim.value);

      fetch(`${url}?${params}`, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((r) => r.json())
        .then((data) => {
          if (!data.compromissos.length) {
            resultado.innerHTML = '<span class="text-xs text-juridico-verde">Sem conflito de horário.</span>';
            return;
          }
          const lista = data.compromissos
            .map((c) => `${escaparHtml(c.titulo)} (${escaparHtml(c.horario)})`)
            .join(", ");
          resultado.innerHTML = `<span class="text-xs text-juridico-urgente">Já tem compromisso nesse horário: ${lista}</span>`;
        });
    }

    container.querySelectorAll("[data-disponibilidade-participante]").forEach((campo) => {
      campo.addEventListener("change", () => consultar(campo));
    });
  });

  // ── Chat em tempo real (WebSocket) ──────────────────────────────────────────
  // Progressivo: sem WebSocket disponível, o Chat continua funcionando só
  // por HTTP (envio e leitura de mensagem), como antes desta feature.
  function conectarComReconexao(caminho, aoReceberTexto) {
    let tentativa = 0;

    function conectar() {
      const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocolo}//${window.location.host}${caminho}`);
      socket.addEventListener("message", (evento) => aoReceberTexto(evento.data));
      socket.addEventListener("close", () => {
        tentativa += 1;
        const espera = Math.min(30000, 1000 * 2 ** tentativa);
        setTimeout(conectar, espera);
      });
    }

    conectar();
  }

  // Conversa individual/grupo/sala global aberta: cada frame recebido já
  // é o fragmento HTML da mensagem, renderizado no backend — só anexa.
  const containerMensagens = document.querySelector("[data-ws-mensagens]");
  if (containerMensagens && containerMensagens.dataset.wsMensagens) {
    conectarComReconexao(containerMensagens.dataset.wsMensagens, (html) => {
      containerMensagens.insertAdjacentHTML("beforeend", html);
      containerMensagens.scrollTop = containerMensagens.scrollHeight;
    });
  }

  // Lista de conversas: cada frame é "<id-da-conversa>\n<fragmento-html-do-indicador>".
  const listaDeConversas = document.querySelector("[data-ws-lista]");
  if (listaDeConversas) {
    conectarComReconexao(listaDeConversas.dataset.wsLista, (payload) => {
      const fim = payload.indexOf("\n");
      const conversaId = payload.slice(0, fim);
      const html = payload.slice(fim + 1);
      const slot = document.querySelector(`[data-conversa-id="${conversaId}"] [data-nao-lida-slot]`);
      if (slot && !slot.innerHTML.trim()) slot.innerHTML = html;
    });
  }

});
