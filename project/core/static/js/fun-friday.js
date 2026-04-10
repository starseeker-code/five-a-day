// fun-friday.js — extracted from fun_friday.html
// No Django template variables needed

const ffStudentList = document.getElementById('ffStudentList');

function getCsrf() {
    return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='))?.split('=')[1]||'';
}

// Dual-flag visibility
function applyVisibility() {
    ffStudentList.querySelectorAll('.ff-student-row').forEach(row => {
        row.style.display = (row._searchHidden || row._ffHidden) ? 'none' : '';
    });
}

// Sort priority 1(green)->2(yellow check)->3(yellow x)->4(grey)
function getFFCategory(row) {
    const t = row.dataset.ffThis === '1', l = row.dataset.ffLast === '1';
    if (t && !l) return 1;
    if (t && l)  return 2;
    if (!t && l) return 3;
    return 4;
}

function updateFFIcon(btn, isThis, isLast) {
    const span = btn.querySelector('.ff-icon');
    const row = btn.closest('.ff-student-row');
    row.dataset.ffThis = isThis ? '1' : '0';
    const nameSpan = row.querySelector('.ff-name');
    nameSpan.style.color = isThis ? '#404040' : '#d1d5db';
    nameSpan.style.fontWeight = isThis ? '500' : '400';
    if (isThis && !isLast)      { span.textContent = 'check_circle'; span.style.color = '#22c55e'; }
    else if (isThis && isLast)  { span.textContent = 'check_circle'; span.style.color = '#f59e0b'; }
    else if (!isThis && isLast) { span.textContent = 'cancel';       span.style.color = '#f59e0b'; }
    else                        { span.textContent = 'cancel';       span.style.color = '#d1d5db'; }
}

// FF Toggle
document.querySelectorAll('.ff-toggle-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const studentId = this.dataset.studentId;
        fetch(`/api/students/${studentId}/fun-friday/toggle/`, {
            method: 'POST',
            headers: {'Content-Type':'application/json','X-CSRFToken':getCsrf()},
            body: '{}',
        }).then(r=>r.json()).then(data => {
            if (data.success) {
                updateFFIcon(this, data.is_this_week, data.was_last_week);
                applyFFFilter();
            }
        });
    });
});

// ==================== SEARCH ====================
const ffSearchBtn = document.getElementById('ffSearchBtn');
const ffSearchInput = document.getElementById('ffSearchInput');

ffSearchBtn.addEventListener('click', () => {
    const visible = ffSearchInput.style.display !== 'none';
    if (visible) {
        ffSearchInput.style.display = 'none';
        ffSearchInput.value = '';
        ffStudentList.querySelectorAll('.ff-student-row').forEach(r => { r._searchHidden = false; });
        applyVisibility();
    } else {
        ffSearchInput.style.display = 'block';
        ffSearchInput.focus();
    }
});

ffSearchInput.addEventListener('input', function() {
    const q = this.value.toLowerCase().trim();
    ffStudentList.querySelectorAll('.ff-student-row').forEach(row => {
        row._searchHidden = q !== '' && !row.dataset.name.toLowerCase().includes(q);
    });
    applyVisibility();
});

// ==================== NAME SORT ====================
const ffSortBtn = document.getElementById('ffSortBtn');
const ffSortIcon = document.getElementById('ffSortIcon');
let ffNameSortDir = 0; // 0=default, 1=A->Z, 2=Z->A

ffSortBtn.addEventListener('click', () => {
    ffNameSortDir = (ffNameSortDir % 2) + 1;
    const asc = ffNameSortDir === 1;
    ffSortIcon.textContent = 'sort_by_alpha';
    ffSortBtn.title = asc ? 'Nombre Z\u2192A' : 'Nombre A\u2192Z';
    ffSortBtn.style.background = '#ede9fe';
    ffSortBtn.style.color = '#2e1065';
    const rows = Array.from(ffStudentList.querySelectorAll('.ff-student-row'));
    rows.sort((a, b) => {
        const na = a.dataset.name.toLowerCase(), nb = b.dataset.name.toLowerCase();
        return asc ? na.localeCompare(nb) : nb.localeCompare(na);
    });
    rows.forEach(row => ffStudentList.appendChild(row));
});

// ==================== FF FILTER ====================
const ffFilterBtn = document.getElementById('ffFilterBtn');
const ffFilterIcon = document.getElementById('ffFilterIcon');
let ffFilterState = 0;

function applyFFFilter() {
    ffStudentList.querySelectorAll('.ff-student-row').forEach(row => {
        const isThis = row.dataset.ffThis === '1';
        row._ffHidden = (ffFilterState === 1 && isThis) || (ffFilterState === 2 && !isThis);
    });
    applyVisibility();
}

const ffFilterCfg = [
    { icon: 'filter_list', bg: '',        color: '' },
    { icon: 'celebration', bg: '#fee2e2', color: '#991b1b' },
    { icon: 'star',        bg: '#dcfce7', color: '#166534' },
];

ffFilterBtn.addEventListener('click', () => {
    ffFilterState = (ffFilterState + 1) % 3;
    const cfg = ffFilterCfg[ffFilterState];
    ffFilterIcon.textContent = cfg.icon;
    ffFilterBtn.style.background = cfg.bg;
    ffFilterBtn.style.color = cfg.color;
    applyFFFilter();
});

// ==================== POPUP LISTS ====================
const ffListBtn = document.getElementById('ffListBtn');
const modalFfLists = document.getElementById('modal-ff-lists');

ffListBtn.addEventListener('click', () => {
    modalFfLists.style.display = 'flex';
    document.body.style.overflow = 'hidden';
});

modalFfLists.addEventListener('click', (e) => {
    if (e.target === modalFfLists) {
        modalFfLists.style.display = 'none';
        document.body.style.overflow = '';
    }
});
