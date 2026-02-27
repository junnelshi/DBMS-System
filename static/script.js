/* ============================================================
   MotoRent — script.js
   ============================================================ */

/* ── TOAST ─────────────────────────────────────────────────── */
function showToast(msg, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

/* ── MODAL ─────────────────────────────────────────────────── */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modal when clicking overlay background
document.addEventListener('click', function (e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Close modal on Escape key
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

/* ── AUTH TABS (login.html) ────────────────────────────────── */
function switchTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.auth-panel').forEach(p => p.classList.remove('active'));

  const tabEl = document.querySelector(`.auth-tab[data-tab="${tab}"]`);
  const panelEl = document.getElementById(tab + '-panel');
  if (tabEl)   tabEl.classList.add('active');
  if (panelEl) panelEl.classList.add('active');
}

// Auto-switch tab from URL param (?tab=register)
(function () {
  const params = new URLSearchParams(window.location.search);
  if (params.get('tab') === 'register') switchTab('register');
})();

/* ── MOTOR MODAL ───────────────────────────────────────────── */
function openAddMotor() {
  document.getElementById('motorModalTitle').textContent = 'ADD MOTOR';
  document.getElementById('motorForm').reset();
  document.getElementById('motorIdField').value = '';
  openModal('motorModal');
}

function openEditMotor(id, brand, model, year, type, plate, rate, status, notes) {
  document.getElementById('motorModalTitle').textContent = 'EDIT MOTOR';
  document.getElementById('motorIdField').value = id;
  document.getElementById('m-brand').value  = brand;
  document.getElementById('m-model').value  = model;
  document.getElementById('m-year').value   = year;
  document.getElementById('m-type').value   = type;
  document.getElementById('m-plate').value  = plate;
  document.getElementById('m-rate').value   = rate;
  document.getElementById('m-status').value = status;
  document.getElementById('m-notes').value  = notes || '';
  openModal('motorModal');
}

function submitMotorForm() {
  const id    = document.getElementById('motorIdField').value;
  const brand = document.getElementById('m-brand').value.trim();
  const model = document.getElementById('m-model').value.trim();
  const plate = document.getElementById('m-plate').value.trim();
  const rate  = document.getElementById('m-rate').value.trim();

  if (!brand || !model || !plate || !rate) {
    showToast('Please fill in all required fields.', 'error');
    return;
  }

  const form   = document.getElementById('motorForm');
  const action = id
    ? `/motors/edit/${id}`
    : '/motors/add';
  form.action = action;
  form.submit();
}

function confirmDeleteMotor(motorId) {
  if (confirm('Are you sure you want to delete this motor?')) {
    document.getElementById('deleteMotorForm-' + motorId).submit();
  }
}

/* ── RENTAL MODAL ──────────────────────────────────────────── */
function openRentalModal(motorId, motorName) {
  const form = document.getElementById('rentalForm');
  if (form) form.reset();

  // Pre-select motor if provided
  if (motorId) {
    const sel = document.getElementById('r-motor');
    if (sel) sel.value = motorId;
  }

  // Default dates
  const today    = new Date().toISOString().split('T')[0];
  const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];
  const startEl  = document.getElementById('r-start');
  const endEl    = document.getElementById('r-end');
  if (startEl) startEl.value = today;
  if (endEl)   endEl.value   = tomorrow;

  calcRentalTotal();
  openModal('rentalModal');
}

function calcRentalTotal() {
  const startEl  = document.getElementById('r-start');
  const endEl    = document.getElementById('r-end');
  const motorSel = document.getElementById('r-motor');
  const totalDiv = document.getElementById('rental-total');
  if (!startEl || !endEl || !totalDiv) return;

  const start = startEl.value;
  const end   = endEl.value;
  if (!start || !end) return;

  const days = Math.max(1, Math.round((new Date(end) - new Date(start)) / 86400000));

  // Try to get rate from selected option's data attribute
  let rate = 500;
  if (motorSel && motorSel.selectedOptions[0]) {
    const dataRate = motorSel.selectedOptions[0].getAttribute('data-rate');
    if (dataRate) rate = parseFloat(dataRate);
  }

  const total = days * rate;
  totalDiv.innerHTML = `
    <span style="color:var(--muted)">${days} day(s) &times; &#8369;${rate.toLocaleString()}/day = </span>
    <strong style="color:var(--accent);font-size:1rem;">&#8369;${total.toLocaleString()}</strong>`;
}

function submitRentalForm() {
  const customer = document.getElementById('r-customer');
  const motorSel = document.getElementById('r-motor');
  const start    = document.getElementById('r-start');
  const end      = document.getElementById('r-end');

  // Admin must select a customer
  if (customer && !customer.value.trim()) {
    showToast('Please select or enter a customer.', 'error');
    return;
  }
  if (!motorSel || !motorSel.value) {
    showToast('Please select a motor.', 'error');
    return;
  }
  if (!start.value || !end.value) {
    showToast('Please select rental dates.', 'error');
    return;
  }
  document.getElementById('rentalForm').submit();
}

function confirmDeleteRental(rentalId) {
  if (confirm('Are you sure you want to delete this rental?')) {
    document.getElementById('deleteRentalForm-' + rentalId).submit();
  }
}

function confirmReturnRental(rentalId) {
  if (confirm('Mark this rental as returned? The motor will be set to Available.')) {
    document.getElementById('returnRentalForm-' + rentalId).submit();
  }
}

function confirmApproveRental(rentalId) {
  if (confirm('Approve this rental?')) {
    document.getElementById('approveRentalForm-' + rentalId).submit();
  }
}

/* ── CONFIRM DELETE CUSTOMER ───────────────────────────────── */
function confirmDeleteCustomer(studentId) {
  if (confirm('Remove this customer? This cannot be undone.')) {
    document.getElementById('deleteCustomerForm-' + studentId).submit();
  }
}

/* ── MOTOR FILTER (motors.html live search) ────────────────── */
function filterMotorCards() {
  const search = (document.getElementById('motor-search')?.value || '').toLowerCase();
  const status = document.getElementById('motor-status-filter')?.value || '';
  const type   = document.getElementById('motor-type-filter')?.value   || '';

  document.querySelectorAll('.motor-card[data-brand]').forEach(card => {
    const brand = (card.dataset.brand || '').toLowerCase();
    const model = (card.dataset.model || '').toLowerCase();
    const plate = (card.dataset.plate || '').toLowerCase();
    const cStatus = card.dataset.status || '';
    const cType   = card.dataset.type   || '';

    const matchSearch = `${brand} ${model} ${plate}`.includes(search);
    const matchStatus = !status || cStatus === status;
    const matchType   = !type   || cType   === type;

    card.style.display = (matchSearch && matchStatus && matchType) ? '' : 'none';
  });
}

/* ── RENTAL FILTER (rentals.html) ──────────────────────────── */
function filterRentalRows() {
  const search = (document.getElementById('rental-search')?.value || '').toLowerCase();
  const status = document.getElementById('rental-status-filter')?.value || '';

  document.querySelectorAll('tbody tr[data-customer]').forEach(row => {
    const customer = (row.dataset.customer || '').toLowerCase();
    const motor    = (row.dataset.motor    || '').toLowerCase();
    const rStatus  = row.dataset.status    || '';

    const matchSearch = `${customer} ${motor}`.includes(search);
    const matchStatus = !status || rStatus === status;

    row.style.display = (matchSearch && matchStatus) ? '' : 'none';
  });
}

/* ── CUSTOMER FILTER (customers.html) ──────────────────────── */
function filterCustomerRows() {
  const search = (document.getElementById('cust-search')?.value || '').toLowerCase();

  document.querySelectorAll('tbody tr[data-name]').forEach(row => {
    const name  = (row.dataset.name  || '').toLowerCase();
    const idno  = (row.dataset.idno  || '').toLowerCase();
    const email = (row.dataset.email || '').toLowerCase();

    row.style.display = `${name} ${idno} ${email}`.includes(search) ? '' : 'none';
  });
}

/* ── CHART INIT (dashboard.html) ───────────────────────────── */
function initFleetChart(available, rented, maintenance) {
  const ctx = document.getElementById('fleetChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Available', 'Rented', 'Maintenance'],
      datasets: [{
        data: [available, rented, maintenance],
        backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b'],
        borderWidth: 0, borderRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#64748b', font: { family: 'DM Sans' }, boxWidth: 10, borderRadius: 4 } }
      },
      cutout: '65%'
    }
  });
}

function initRevenueChart(labels, data) {
  const ctx = document.getElementById('revenueChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Revenue (₱)',
        data,
        backgroundColor: 'rgba(59,130,246,0.15)',
        borderColor: '#3b82f6',
        borderWidth: 2, borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: '#f1f5f9' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: '#f1f5f9' } }
      }
    }
  });
}

/* ── RENTAL DATE LISTENERS ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  const startEl  = document.getElementById('r-start');
  const endEl    = document.getElementById('r-end');
  const motorSel = document.getElementById('r-motor');
  if (startEl)  startEl.addEventListener('change',  calcRentalTotal);
  if (endEl)    endEl.addEventListener('change',    calcRentalTotal);
  if (motorSel) motorSel.addEventListener('change', calcRentalTotal);
});
