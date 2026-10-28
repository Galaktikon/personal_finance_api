const form = document.querySelector('#upload-form');
const input = document.querySelector('#csv-file');
const zone = document.querySelector('#drop-zone');
const selected = document.querySelector('#selected-file');
const button = document.querySelector('#submit-button');
const message = document.querySelector('#message');
const results = document.querySelector('#results');
const metrics = document.querySelector('#metric-grid');
const rowResults = document.querySelector('#row-results');

function showFile(file) {
  selected.hidden = !file;
  selected.textContent = file ? `Selected: ${file.name} · ${(file.size / 1024).toFixed(1)} KB` : '';
}

input.addEventListener('change', () => showFile(input.files[0]));
zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragging'); });
zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
zone.addEventListener('drop', event => {
  event.preventDefault();
  zone.classList.remove('dragging');
  if (event.dataTransfer.files.length) {
    input.files = event.dataTransfer.files;
    showFile(input.files[0]);
  }
});

function cell(text, label) {
  const element = document.createElement('td');
  element.textContent = text;
  element.dataset.label = label;
  return element;
}

function render(data) {
  const values = [
    ['Net cash flow', data.net_cash_flow, true],
    ['Gross income', data.gross_income],
    ['Gross expenses', data.gross_expenses],
    ['Refunds', data.refunds],
    ['Net spending', data.net_spending],
    ['Posted rows', String(data.posted_count)],
  ];
  metrics.replaceChildren();
  for (const [label, value, highlight] of values) {
    const card = document.createElement('div');
    card.className = `metric${highlight ? ' highlight' : ''}`;
    const name = document.createElement('label');
    name.textContent = label;
    const figure = document.createElement('strong');
    figure.textContent = label === 'Posted rows' ? value : `$${value}`;
    card.append(name, figure);
    metrics.append(card);
  }
  rowResults.replaceChildren();
  for (const row of data.rows) {
    const tr = document.createElement('tr');
    tr.append(cell(String(row.row_number), 'Row'));
    const status = document.createElement('td');
    status.dataset.label = 'Result';
    const pill = document.createElement('span');
    pill.className = `pill${row.status === 'failed' ? ' failed' : row.posted === false ? ' pending' : ''}`;
    pill.textContent = row.status === 'failed' ? 'Failed' : row.posted ? 'Posted' : 'Pending';
    status.append(pill);
    tr.append(status, cell(row.kind || '—', 'Kind'), cell(row.amount ? `$${row.amount}` : '—', 'Amount'), cell(row.error_code || (row.posted ? 'Included in totals' : row.status === 'accepted' ? 'Excluded from totals' : 'Check row values'), 'Details'));
    rowResults.append(tr);
  }
  document.querySelector('#result-count').textContent = `${data.accepted_count} accepted · ${data.failed_count} failed`;
  results.hidden = false;
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const file = input.files[0];
  if (!file) { message.textContent = 'Choose a CSV file first.'; return; }
  if (!file.name.toLowerCase().endsWith('.csv')) { message.textContent = 'Choose a .csv file.'; return; }
  message.textContent = '';
  button.disabled = true;
  button.firstChild.textContent = 'Processing… ';
  try {
    const body = new FormData();
    body.append('file', file);
    const response = await fetch('/api/v1/demo/process', { method: 'POST', body });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The file could not be processed. Check its format and try again.');
    render(data);
  } catch (error) {
    results.hidden = true;
    message.textContent = error.message || 'The request failed. Please try again.';
  } finally {
    button.disabled = false;
    button.firstChild.textContent = 'Process CSV ';
  }
});
