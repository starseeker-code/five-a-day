// payments.js — merged from payments_list.html and payment_create.html

// ============================================================
// PAYMENTS LIST (payments_list.html)
// ============================================================
(function initPaymentsList() {
    const paymentsTableBody = document.getElementById('paymentsTableBody');
    if (!paymentsTableBody) return;

    const PAGE_SIZE = 10;
    let currentPage = 1;

    function getCsrf() {
        return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='))?.split('=')[1]||'';
    }

    // Get all data rows (cached once)
    const allRows = Array.from(paymentsTableBody.querySelectorAll('tr[data-name]'));

    // ==================== VISIBILITY + PAGINATION ====================
    function getVisibleRows() {
        return allRows.filter(row => !row._searchHidden && !row._typeHidden && !row._statusHidden);
    }

    function renderPage() {
        const visible = getVisibleRows();
        const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
        if (currentPage > totalPages) currentPage = totalPages;
        const start = (currentPage - 1) * PAGE_SIZE;
        const end = start + PAGE_SIZE;

        // Hide all rows first
        allRows.forEach(row => row.style.display = 'none');
        // Show only current page of visible rows
        visible.forEach((row, i) => {
            row.style.display = (i >= start && i < end) ? '' : 'none';
        });

        // Update count
        document.getElementById('visibleCount').textContent = visible.length;

        // Render pagination controls
        renderPagination(totalPages);
    }

    function renderPagination(totalPages) {
        const nav = document.getElementById('paginationNav');
        if (totalPages <= 1) { nav.innerHTML = ''; return; }

        const btnStyle = 'text-decoration:none;width:2.5rem;height:2.5rem;border-radius:9999px;display:inline-flex;align-items:center;justify-content:center;border:1px solid #e5e7eb;background:#fff;color:#525252;font-size:0.875rem;cursor:pointer;transition:background 0.2s;';
        const activeStyle = 'width:2.5rem;height:2.5rem;border-radius:9999px;display:inline-flex;align-items:center;justify-content:center;background:#8b5cf6;color:#fff;font-size:0.875rem;font-weight:700;';

        let html = '';
        if (currentPage > 1) {
            html += `<button type="button" class="pg-btn" data-page="${currentPage - 1}" style="${btnStyle}font-size:1rem;">\u2039</button>`;
        }

        // Show limited page range for many pages
        let pages = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            pages = [1];
            let start = Math.max(2, currentPage - 1);
            let end = Math.min(totalPages - 1, currentPage + 1);
            if (start > 2) pages.push('...');
            for (let i = start; i <= end; i++) pages.push(i);
            if (end < totalPages - 1) pages.push('...');
            pages.push(totalPages);
        }

        for (const p of pages) {
            if (p === '...') {
                html += `<span style="width:2rem;text-align:center;color:#9ca3af;">\u2026</span>`;
            } else if (p === currentPage) {
                html += `<span style="${activeStyle}">${p}</span>`;
            } else {
                html += `<button type="button" class="pg-btn" data-page="${p}" style="${btnStyle}">${p}</button>`;
            }
        }

        if (currentPage < totalPages) {
            html += `<button type="button" class="pg-btn" data-page="${currentPage + 1}" style="${btnStyle}font-size:1rem;">\u203A</button>`;
        }
        nav.innerHTML = html;

        // Attach click handlers
        nav.querySelectorAll('.pg-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentPage = parseInt(btn.dataset.page);
                renderPage();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
        });
    }

    function applyFiltersAndPaginate() {
        currentPage = 1;
        renderPage();
    }

    // ==================== SEARCH ====================
    const paymentSearchBtn = document.getElementById('paymentSearchBtn');
    const paymentSearchInput = document.getElementById('paymentSearchInput');

    paymentSearchBtn.addEventListener('click', () => {
        const visible = paymentSearchInput.style.display !== 'none';
        if (visible) {
            paymentSearchInput.style.display = 'none';
            paymentSearchInput.value = '';
            allRows.forEach(r => { r._searchHidden = false; });
            applyFiltersAndPaginate();
        } else {
            paymentSearchInput.style.display = 'block';
            paymentSearchInput.focus();
        }
    });

    paymentSearchInput.addEventListener('input', function() {
        const q = this.value.toLowerCase().trim();
        allRows.forEach(row => {
            row._searchHidden = q !== '' && !row.dataset.name.toLowerCase().includes(q);
        });
        applyFiltersAndPaginate();
    });

    // ==================== TYPE FILTER (Monthly 2d/w, Monthly 1d/w, Quarterly) ====================
    const paymentTypeFilterBtn = document.getElementById('paymentTypeFilterBtn');
    const paymentTypeFilterIcon = document.getElementById('paymentTypeFilterIcon');
    let typeFilterState = 0;

    const typeFilterCfg = [
        { icon: 'tune',           title: 'Tipo: Todos',                 bg: '',        color: '', match: null },
        { icon: 'event_repeat',   title: 'Mensual 2 d\u00edas/sem',          bg: '#3b82f6', color: '#fff', match: r => r.dataset.paymentType === 'monthly' && r.dataset.scheduleType === 'full_time' },
        { icon: 'event_note',     title: 'Mensual 1 d\u00eda/sem',           bg: '#8b5cf6', color: '#fff', match: r => r.dataset.paymentType === 'monthly' && (r.dataset.scheduleType === 'part_time' || r.dataset.scheduleType === 'adult_group') },
        { icon: 'date_range',     title: 'Trimestral',                  bg: '#059669', color: '#fff', match: r => r.dataset.paymentType === 'quarterly' },
    ];

    function applyTypeFilter() {
        const cfg = typeFilterCfg[typeFilterState];
        allRows.forEach(row => {
            row._typeHidden = cfg.match ? !cfg.match(row) : false;
        });
        applyFiltersAndPaginate();
    }

    paymentTypeFilterBtn.addEventListener('click', () => {
        typeFilterState = (typeFilterState + 1) % typeFilterCfg.length;
        const cfg = typeFilterCfg[typeFilterState];
        paymentTypeFilterIcon.textContent = cfg.icon;
        paymentTypeFilterBtn.title = cfg.title;
        paymentTypeFilterBtn.style.background = cfg.bg;
        paymentTypeFilterBtn.style.color = cfg.color;
        applyTypeFilter();
    });

    // ==================== STATUS FILTER (All / Not completed) ====================
    const paymentStatusFilterBtn = document.getElementById('paymentStatusFilterBtn');
    const paymentStatusFilterIcon = document.getElementById('paymentStatusFilterIcon');
    let statusFilterState = 0;

    const statusFilterCfg = [
        { icon: 'filter_list',     title: 'Estado: Todos',        bg: '',        color: '' },
        { icon: 'pending_actions', title: 'No completados',       bg: '#dc2626', color: '#fff' },
    ];

    function applyStatusFilter() {
        allRows.forEach(row => {
            if (statusFilterState === 0) {
                row._statusHidden = false;
            } else {
                row._statusHidden = row.dataset.paymentStatus === 'completed';
            }
        });
        applyFiltersAndPaginate();
    }

    paymentStatusFilterBtn.addEventListener('click', () => {
        statusFilterState = (statusFilterState + 1) % statusFilterCfg.length;
        const cfg = statusFilterCfg[statusFilterState];
        paymentStatusFilterIcon.textContent = cfg.icon;
        paymentStatusFilterBtn.title = cfg.title;
        paymentStatusFilterBtn.style.background = cfg.bg;
        paymentStatusFilterBtn.style.color = cfg.color;
        applyStatusFilter();
    });

    // ==================== SORT ====================
    const paymentSortBtn = document.getElementById('paymentSortBtn');
    const paymentSortIcon = document.getElementById('paymentSortIcon');
    let paymentSortState = 0;
    const paymentSortCfg = [
        { field: 'date', dir: 'asc',  icon: 'calendar_month', title: 'Fecha \u2191' },
        { field: 'date', dir: 'desc', icon: 'calendar_month', title: 'Fecha \u2193' },
        { field: 'name', dir: 'asc',  icon: 'sort_by_alpha',  title: 'Nombre A\u2192Z' },
        { field: 'name', dir: 'desc', icon: 'sort_by_alpha',  title: 'Nombre Z\u2192A' },
    ];

    paymentSortBtn.addEventListener('click', () => {
        paymentSortState = (paymentSortState + 1) % 4;
        const cfg = paymentSortCfg[paymentSortState];
        paymentSortIcon.textContent = cfg.icon;
        paymentSortBtn.title = cfg.title;
        // Sort the cached allRows array (this reorders the canonical list)
        allRows.sort((a, b) => {
            if (cfg.field === 'name') {
                const na = a.dataset.name.toLowerCase(), nb = b.dataset.name.toLowerCase();
                return cfg.dir === 'asc' ? na.localeCompare(nb) : nb.localeCompare(na);
            }
            return cfg.dir === 'asc'
                ? a.dataset.date.localeCompare(b.dataset.date)
                : b.dataset.date.localeCompare(a.dataset.date);
        });
        // Re-append in new order
        allRows.forEach(row => paymentsTableBody.appendChild(row));
        renderPage();
    });

    // ==================== PAYMENT COMPLETION DROPDOWN ====================
    document.querySelectorAll('.payment-complete-trigger').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.stopPropagation();
            document.querySelectorAll('.payment-dropdown').forEach(d => {
                if (d !== this.querySelector('.payment-dropdown')) d.classList.add('hidden');
            });
            this.querySelector('.payment-dropdown').classList.toggle('hidden');
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.payment-dropdown').forEach(d => d.classList.add('hidden'));
    });

    document.querySelectorAll('.payment-method-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const paymentId = this.dataset.paymentId;
            const method = this.dataset.method;

            fetch(`/api/payments/${paymentId}/quick-complete/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrf(),
                },
                body: JSON.stringify({ payment_method: method }),
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const row = document.querySelector(`tr[data-payment-id="${paymentId}"]`);
                    if (row) {
                        row.dataset.paymentStatus = 'completed';
                        const trigger = row.querySelector('.payment-complete-trigger');
                        if (trigger) trigger.remove();
                        const statusCell = row.querySelectorAll('td')[5];
                        if (statusCell) {
                            statusCell.innerHTML = '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"><span class="material-symbols-outlined text-sm mr-1">check_circle</span>Completado</span>';
                        }
                        const payDateCell = row.querySelectorAll('td')[7];
                        if (payDateCell) {
                            const today = new Date();
                            payDateCell.textContent = `${String(today.getDate()).padStart(2,'0')}/${String(today.getMonth()+1).padStart(2,'0')}/${today.getFullYear()}`;
                        }
                        const methodLabels = { cash: 'Cash', transfer: 'Bank Transfer', credit_card: 'Credit Card' };
                        const methodCell = row.querySelectorAll('td')[4];
                        if (methodCell) {
                            methodCell.innerHTML = `<span class="text-sm text-neutral-800">${methodLabels[method] || method}</span>`;
                        }
                        applyStatusFilter();
                    }
                } else {
                    alert(data.error || 'Error al completar el pago');
                }
            })
            .catch(err => {
                console.error('Error completing payment:', err);
                alert('Error de conexi\u00f3n');
            });

            document.querySelectorAll('.payment-dropdown').forEach(d => d.classList.add('hidden'));
        });
    });

    // ==================== INIT ====================
    // Initialize filter flags
    allRows.forEach(r => { r._searchHidden = false; r._typeHidden = false; r._statusHidden = false; });
    renderPage();
})();


// ============================================================
// PAYMENT CREATE (payment_create.html)
// ============================================================
(function initPaymentCreate() {
    const studentSearch = document.getElementById('student_search');
    if (!studentSearch) return;

    const studentSuggestions = document.getElementById('student_suggestions');
    const parentDisplay = document.getElementById('parent_display');
    const validationMessage = document.getElementById('validation_message');
    const form = document.getElementById('paymentForm');

    let selectedStudent = null;
    let selectedParent = null;

    // Set today as default due date
    document.getElementById('due_date').value = new Date().toISOString().split('T')[0];

    // Auto-fill payment date when status changes to completed
    document.getElementById('payment_status').addEventListener('change', function() {
        const paymentDate = document.getElementById('payment_date');
        if (this.value === 'completed' && !paymentDate.value) {
            paymentDate.value = new Date().toISOString().split('T')[0];
        }
    });

    // Auto-generate concept based on payment type
    document.getElementById('payment_type').addEventListener('change', function() {
        const concept = document.getElementById('concept');
        if (!concept.value || concept.value.startsWith('Pago de') || concept.value === 'Otro pago') {
            const map = {
                enrollment: 'Pago de matr\u00edcula',
                monthly: 'Pago mensualidad',
                materials: 'Pago de materiales',
                registration: 'Pago de inscripci\u00f3n',
                exam: 'Pago de examen',
                other: 'Otro pago',
            };
            concept.value = map[this.value] || '';
        }
    });

    // Student search
    let studentTimeout;
    studentSearch.addEventListener('input', function() {
        clearTimeout(studentTimeout);
        const query = this.value.trim();
        if (query.length < 2) { studentSuggestions.classList.add('hidden'); return; }
        studentTimeout = setTimeout(() => {
            fetch(`/api/search/students/?q=${encodeURIComponent(query)}`)
                .then(r => r.json())
                .then(data => displayStudentSuggestions(data.results))
                .catch(e => console.error(e));
        }, 300);
    });

    // Parent is auto-populated from student selection

    function displayStudentSuggestions(students) {
        if (!students.length) { studentSuggestions.classList.add('hidden'); return; }
        studentSuggestions.innerHTML = students.map(s => `
            <div class="p-3 hover:bg-neutral-50 cursor-pointer border-b border-neutral-100"
                 onclick="window._paymentSelectStudent(${s.id}, '${s.full_name.replace(/'/g, "\\'")}', '${(s.school||'').replace(/'/g, "\\'")}')">
                <div class="font-medium text-neutral-800">${s.full_name}</div>
                ${s.school ? `<div class="text-sm text-neutral-500">${s.school}</div>` : ''}
            </div>
        `).join('');
        studentSuggestions.classList.remove('hidden');
    }



    function selectStudent(id, name, school) {
        selectedStudent = { id, name };
        studentSearch.value = name;
        document.getElementById('student_id').value = id;
        studentSuggestions.classList.add('hidden');

        // Auto-fetch first parent for this student
        fetch(`/api/validate/student-parent/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
            body: JSON.stringify({ student_id: id, parent_id: 0 })
        })
        .then(r => r.json())
        .then(data => {
            if (data.parents && data.parents.length > 0) {
                const p = data.parents[0];
                selectedParent = { id: p.id, name: p.full_name };
                document.getElementById('parent_id').value = p.id;
                if (parentDisplay) parentDisplay.value = p.full_name;
            } else {
                selectedParent = null;
                document.getElementById('parent_id').value = '';
                if (parentDisplay) parentDisplay.value = 'Sin padre/tutor (estudiante adulto)';
            }
        })
        .catch(() => {});
    }

    function selectParent(id, name, email) {
        selectedParent = { id, name };
        if (parentDisplay) parentDisplay.value = name;
        document.getElementById('parent_id').value = id;
    }

    // Expose for inline onclick handlers in dynamic HTML
    window._paymentSelectStudent = selectStudent;
    window._paymentSelectParent = selectParent;

    function validateRelation() {
        if (!selectedStudent || !selectedParent) { validationMessage.classList.add('hidden'); return; }
        fetch('/api/validate/student-parent/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
            body: JSON.stringify({ student_id: selectedStudent.id, parent_id: selectedParent.id })
        })
        .then(r => r.json())
        .then(data => {
            validationMessage.classList.remove('hidden');
            if (data.valid) {
                validationMessage.style.color = '#16a34a';
                validationMessage.textContent = '\u2713 Relaci\u00f3n v\u00e1lida entre estudiante y padre/tutor';
                if (data.enrollment && data.enrollment.remaining_amount > 0) {
                    document.getElementById('amount').value = data.enrollment.remaining_amount;
                    document.getElementById('concept').value = `Pago de matr\u00edcula - ${data.enrollment.enrollment_type}`;
                    document.getElementById('payment_type').value = 'enrollment';
                }
            } else {
                validationMessage.style.color = '#dc2626';
                validationMessage.textContent = '\u26A0 El padre/tutor seleccionado no est\u00e1 asociado con este estudiante';
            }
        })
        .catch(e => console.error(e));
    }

    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!studentSearch.contains(e.target) && !studentSuggestions.contains(e.target))
            studentSuggestions.classList.add('hidden');
        if (!parentSearch.contains(e.target) && !parentSuggestions.contains(e.target))
            parentSuggestions.classList.add('hidden');
    });

    // Form validation
    form.addEventListener('submit', (e) => {
        if (!selectedStudent || !selectedParent) {
            e.preventDefault();
            validationMessage.classList.remove('hidden');
            validationMessage.style.color = '#dc2626';
            validationMessage.textContent = '\u26A0 Debe seleccionar un estudiante y un padre/tutor v\u00e1lidos.';
            return;
        }
        // Auto-set payment date if status is completed and date is empty
        const paymentStatus = document.getElementById('payment_status').value;
        const paymentDate = document.getElementById('payment_date');
        if (paymentStatus === 'completed' && !paymentDate.value) {
            paymentDate.value = new Date().toISOString().split('T')[0];
        }
    });
})();
