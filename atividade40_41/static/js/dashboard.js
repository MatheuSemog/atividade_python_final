let progressChart;

function statusClass(status) {
  return status.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replaceAll(' ', '-');
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value ?? '';
  return div.innerHTML;
}

function taskCard(task) {
  const completeButton = task.status !== 'Concluída'
    ? `<button class="btn btn-sm btn-outline-success btn-complete" data-id="${task.id}" title="Concluir"><i class="bi bi-check-lg"></i></button>` : '';
  return `<div class="col-12 task-item" data-task-id="${task.id}">
    <div class="card task-card status-${statusClass(task.status)} shadow-sm"><div class="card-body">
      <div class="d-flex justify-content-between gap-3">
        <div><h3 class="h5 mb-1">${escapeHtml(task.titulo)}</h3><p class="mb-2 text-secondary">${escapeHtml(task.descricao || 'Sem descrição.')}</p><span class="badge text-bg-secondary">${escapeHtml(task.status)}</span></div>
        <div class="d-flex gap-2 align-items-start flex-wrap justify-content-end">
          <a class="btn btn-sm btn-outline-primary" href="/editar/${task.id}" title="Editar"><i class="bi bi-pencil"></i></a>
          ${completeButton}
          <button class="btn btn-sm btn-outline-danger btn-delete" data-id="${task.id}" title="Excluir"><i class="bi bi-trash"></i></button>
        </div>
      </div>
    </div></div>
  </div>`;
}

async function loadTasks(status = 'Todas') {
  const response = await fetch(`/tarefas/filtro?status=${encodeURIComponent(status)}`);
  const tasks = await response.json();
  const container = document.getElementById('tasksContainer');
  container.innerHTML = tasks.length ? tasks.map(taskCard).join('') : '<div class="col-12"><div class="card"><div class="card-body text-center text-secondary py-5"><i class="bi bi-inbox display-5"></i><p class="mt-2 mb-0">Nenhuma tarefa neste filtro.</p></div></div></div>';
}

async function loadProgress() {
  const response = await fetch('/api/progresso');
  const data = await response.json();
  const values = [data['Pendente'], data['Em andamento'], data['Concluída']];
  if (progressChart) {
    progressChart.data.datasets[0].data = values;
    progressChart.update();
    return;
  }
  const canvas = document.getElementById('progressChart');
  progressChart = new Chart(canvas, {
    type: 'doughnut',
    data: { labels: ['Pendente', 'Em andamento', 'Concluída'], datasets: [{ data: values }] },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
  });
}

document.getElementById('statusFilter')?.addEventListener('change', (e) => loadTasks(e.target.value));

document.getElementById('tasksContainer')?.addEventListener('click', async (e) => {
  const complete = e.target.closest('.btn-complete');
  const del = e.target.closest('.btn-delete');
  if (complete) {
    await fetch(`/concluir/${complete.dataset.id}`, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    await loadTasks(document.getElementById('statusFilter').value);
    await loadProgress();
  }
  if (del && confirm('Deseja realmente excluir esta tarefa?')) {
    await fetch(`/excluir/${del.dataset.id}`, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    await loadTasks(document.getElementById('statusFilter').value);
    await loadProgress();
  }
});

loadProgress();
