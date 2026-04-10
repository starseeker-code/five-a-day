// Build current URL params helper
function buildUrl(overrides, hash) {
  const params = new URLSearchParams(window.location.search);
  for (const [k, v] of Object.entries(overrides)) params.set(k, v);
  return '?' + params.toString() + (hash ? '#' + hash : '');
}

// Students sort change → reload with new sort, reset to page 1
const studentsSort = document.getElementById('students-sort');
if (studentsSort) {
  studentsSort.addEventListener('change', (e) => {
    window.location.href = buildUrl({ students_sort: e.target.value, students_page: 1 }, 'db-students-section');
  });
}

// Payments sort change → reload with new sort, reset to page 1
const paymentsSort = document.getElementById('payments-sort');
if (paymentsSort) {
  paymentsSort.addEventListener('change', (e) => {
    window.location.href = buildUrl({ payments_sort: e.target.value, payments_page: 1 }, 'db-payments-section');
  });
}
