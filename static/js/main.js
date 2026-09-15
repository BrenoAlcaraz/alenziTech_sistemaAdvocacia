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
