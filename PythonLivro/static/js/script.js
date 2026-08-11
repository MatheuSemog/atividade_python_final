// ---------------------------------------------------------------------------
// Modo escuro (persistido em localStorage)
// ---------------------------------------------------------------------------

function aplicarModoSalvo() {
    const modoEscuro = localStorage.getItem("modoEscuro") === "true";
    document.body.classList.toggle("modo-escuro", modoEscuro);
    atualizarIconeModoEscuro(modoEscuro);
}

function atualizarIconeModoEscuro(modoEscuro) {
    const botao = document.getElementById("btn-modo-escuro");
    if (!botao) return;
    const icone = botao.querySelector("i");
    if (icone) {
        icone.classList.toggle("bi-moon-stars-fill", !modoEscuro);
        icone.classList.toggle("bi-sun-fill", modoEscuro);
    }
}

function inicializarToggleModoEscuro() {
    const botao = document.getElementById("btn-modo-escuro");
    if (!botao) return;

    botao.addEventListener("click", function () {
        const modoEscuro = document.body.classList.toggle("modo-escuro");
        localStorage.setItem("modoEscuro", modoEscuro);
        atualizarIconeModoEscuro(modoEscuro);
    });
}

aplicarModoSalvo();
document.addEventListener("DOMContentLoaded", inicializarToggleModoEscuro);

// ---------------------------------------------------------------------------
// Filtro de tarefas por status (via fetch, sem recarregar a página)
// ---------------------------------------------------------------------------

function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto || "";
    return div.innerHTML;
}

function montarCardTarefa(tarefa) {
    const podeConcluir = tarefa.status !== "Concluída";
    const descricao = tarefa.descricao ? escaparHtml(tarefa.descricao) : "Sem descrição.";

    return `
        <div class="col-12 col-xl-6 tarefa-item">
            <div class="card h-100 shadow-sm border-0 card-tarefa" data-status="${tarefa.status}">
                <div class="card-body d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title mb-0">${escaparHtml(tarefa.titulo)}</h5>
                        <span class="badge status-badge" data-status="${tarefa.status}">${tarefa.status}</span>
                    </div>
                    <p class="card-text flex-grow-1">${descricao}</p>
                    <div class="d-flex gap-2 mt-3">
                        ${podeConcluir ? `
                        <form method="POST" action="/concluir/${tarefa.id}">
                            <button type="submit" class="btn btn-sm btn-success" title="Concluir">
                                <i class="bi bi-check2-circle"></i>
                            </button>
                        </form>` : ""}
                        <a href="/editar/${tarefa.id}" class="btn btn-sm btn-primary" title="Editar">
                            <i class="bi bi-pencil-fill"></i>
                        </a>
                        <form method="POST" action="/excluir/${tarefa.id}" onsubmit="return confirm('Excluir esta tarefa?');">
                            <button type="submit" class="btn btn-sm btn-danger" title="Excluir">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function carregarTarefas(status) {
    const container = document.getElementById("tarefas-container");
    if (!container) return;

    try {
        const resposta = await fetch(`/api/tarefas?status=${encodeURIComponent(status)}`);
        if (!resposta.ok) throw new Error("Falha ao buscar tarefas");
        const tarefas = await resposta.json();

        if (tarefas.length === 0) {
            container.innerHTML = `
                <div class="col-12">
                    <p class="text-body-secondary text-center py-5">
                        <i class="bi bi-inbox fs-2 d-block mb-2"></i>
                        Nenhuma tarefa encontrada para este filtro.
                    </p>
                </div>
            `;
            return;
        }

        container.innerHTML = tarefas.map(montarCardTarefa).join("");
    } catch (erro) {
        container.innerHTML = `
            <div class="col-12">
                <p class="text-danger text-center py-5">Não foi possível carregar as tarefas.</p>
            </div>
        `;
    }
}

function inicializarFiltroTarefas() {
    const opcoes = document.querySelectorAll(".filtro-status");
    const rotuloFiltro = document.getElementById("filtro-atual");

    opcoes.forEach(function (opcao) {
        opcao.addEventListener("click", function (evento) {
            evento.preventDefault();
            const status = opcao.dataset.status;
            if (rotuloFiltro) rotuloFiltro.textContent = opcao.textContent;
            carregarTarefas(status);
        });
    });
}

// ---------------------------------------------------------------------------
// Gráfico de progresso (Chart.js)
// ---------------------------------------------------------------------------

async function inicializarGraficoProgresso() {
    const canvas = document.getElementById("grafico-progresso");
    if (!canvas || typeof Chart === "undefined") return;

    try {
        const resposta = await fetch("/api/progresso");
        const dados = await resposta.json();

        const rotulos = Object.keys(dados);
        const valores = Object.values(dados);
        const cores = {
            "Pendente": "#ffc107",
            "Em andamento": "#0d6efd",
            "Concluída": "#198754",
        };

        new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: rotulos,
                datasets: [{
                    data: valores,
                    backgroundColor: rotulos.map((rotulo) => cores[rotulo] || "#6c757d"),
                    borderWidth: 2,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom" },
                },
            },
        });
    } catch (erro) {
        canvas.replaceWith("Não foi possível carregar o gráfico.");
    }
}
