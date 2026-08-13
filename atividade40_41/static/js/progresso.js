async function loadProgress() {
  const response = await fetch('/api/progresso');
  const data = await response.json();
  new Chart(document.getElementById('progressChart'), {
    type: 'bar',
    data: {
      labels: ['Pendente', 'Em andamento', 'Concluída'],
      datasets: [{ label: 'Tarefas', data: [data['Pendente'], data['Em andamento'], data['Concluída']] }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
  });
}
loadProgress();
