const number = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 1 });
const form = document.querySelector('#shift-form');
form.elements.shift_date.value = new Date().toLocaleDateString('en-CA');

async function refresh() {
  const response = await fetch('/api/shifts');
  if (!response.ok) throw new Error('No se pudo cargar el historial.');
  const { shifts } = await response.json();
  const total = shifts.reduce((sum, s) => sum + s.actual_tonnes, 0);
  const planned = shifts.reduce((sum, s) => sum + s.planned_tonnes, 0);
  const scheduled = shifts.reduce((sum, s) => sum + s.scheduled_minutes, 0);
  const downtime = shifts.reduce((sum, s) => sum + s.downtime_minutes, 0);
  document.querySelector('#record-count').textContent = `${shifts.length} ${shifts.length === 1 ? 'turno' : 'turnos'}`;
  document.querySelector('#total-tonnes').textContent = shifts.length ? `${number.format(total)} t` : '—';
  document.querySelector('#compliance').textContent = planned ? `${number.format(100 * total / planned)} %` : '—';
  document.querySelector('#availability').textContent = scheduled ? `${number.format(100 * (scheduled - downtime) / scheduled)} %` : '—';
  const list = document.querySelector('#shift-list');
  list.replaceChildren();
  if (!shifts.length) {
    const empty = document.createElement('p'); empty.className = 'empty';
    empty.textContent = 'Aún no hay turnos. Registra el primero para ver los indicadores.';
    list.append(empty); return;
  }
  for (const s of shifts) {
    const row = document.createElement('div'); row.className = 'shift';
    const title = document.createElement('div'); title.className = 'shift-title';
    const strong = document.createElement('strong'); strong.textContent = `${s.shift_date} · ${s.name}`;
    const small = document.createElement('small'); small.textContent = `${number.format(s.actual_tonnes)} / ${number.format(s.planned_tonnes)} t`;
    title.append(strong, small); row.append(title);
    for (const [label, value] of [['Cumplimiento', `${number.format(s.compliance_pct)} %`], ['Disponibilidad', `${number.format(s.availability_pct)} %`], ['Tasa', s.tonnes_per_operating_hour === null ? '—' : `${number.format(s.tonnes_per_operating_hour)} t/h`]]) {
      const cell = document.createElement('div'); cell.className = 'shift-cell';
      cell.textContent = value; const caption = document.createElement('small'); caption.textContent = label; cell.append(caption); row.append(cell);
    }
    const button = document.createElement('button'); button.className = 'delete'; button.type = 'button';
    button.textContent = '×'; button.setAttribute('aria-label', `Eliminar turno ${s.shift_date} ${s.name}`);
    button.addEventListener('click', async () => {
      button.disabled = true;
      try { const result = await fetch(`/api/shifts/${s.id}`, { method: 'DELETE' }); if (!result.ok) throw new Error(); await refresh(); }
      catch { button.disabled = false; document.querySelector('#form-message').textContent = 'No se pudo eliminar el turno.'; }
    });
    row.append(button); list.append(row);
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const message = document.querySelector('#form-message'); message.textContent = '';
  const submit = form.querySelector('button[type=submit]'); submit.disabled = true;
  const payload = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch('/api/shifts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo guardar el turno.');
    form.elements.actual_tonnes.value = ''; form.elements.planned_tonnes.value = '';
    form.elements.downtime_minutes.value = '0';
    await refresh();
  } catch (error) { message.textContent = error.message; }
  finally { submit.disabled = false; }
});

refresh().catch(error => { document.querySelector('#shift-list').textContent = error.message; });
