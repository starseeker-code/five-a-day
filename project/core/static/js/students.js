/**
 * students.js — Student list: modal, search, sort, Fun Friday toggle/filter,
 * student type filter, new-student dropdown, form validation.
 * No Django template variables required.
 */
document.addEventListener('DOMContentLoaded', function () {
    // Modal functionality
    const modal = document.getElementById('studentModal');
    const closeBtn = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const form = document.getElementById('studentForm');
    const modalTitle = document.getElementById('modalTitle');
    const submitBtnText = document.getElementById('submitBtnText');
    const studentIdInput = document.getElementById('studentId');

    // Close modal
    function closeModal() {
        modal.classList.add('hidden');
        resetForm();
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Reset form
    function resetForm() {
        form.reset();
        // Reset checkboxes
        document.querySelectorAll('input[name="parents"]').forEach(cb => cb.checked = false);
        document.getElementById('active').checked = true;
    }

    // Edit student function
    window.editStudent = function editStudent(studentId) {
        fetch(`/students/${studentId}/`)
            .then(response => response.json())
            .then(data => {
                // Populate form with student data
                document.getElementById('first_name').value = data.first_name;
                document.getElementById('last_name').value = data.last_name;
                document.getElementById('birth_date').value = data.birth_date;
                document.getElementById('email').value = data.email || '';
                document.getElementById('school').value = data.school || '';
                document.getElementById('group').value = data.group;
                document.getElementById('allergies').value = data.allergies || '';
                document.getElementById('gdpr_signed').checked = data.gdpr_signed;
                document.getElementById('active').checked = data.active;

                // Set parent checkboxes
                document.querySelectorAll('input[name="parents"]').forEach(cb => {
                    cb.checked = data.parents.includes(parseInt(cb.value));
                });

                // Update modal
                modalTitle.textContent = 'Editar Estudiante';
                submitBtnText.textContent = 'Actualizar Estudiante';
                studentIdInput.value = studentId;
                form.action = `/students/${studentId}/update/`;
                modal.classList.remove('hidden');
            })
            .catch(error => {
                console.error('Error loading student data:', error);
                alert('Error al cargar los datos del estudiante');
            });
    };

    // ==================== SEARCH & SORT ====================
    const studentSearchBtn = document.getElementById('studentSearchBtn');
    const studentSearchInput = document.getElementById('studentSearchInput');
    const studentSortBtn = document.getElementById('studentSortBtn');
    const studentSortIcon = document.getElementById('studentSortIcon');
    const studentsTableBody = document.getElementById('studentsTableBody');

    // Each row has three independent visibility flags: searchHidden, ffHidden, typeHidden
    // A row is shown only if no flag is set.
    function applyVisibility() {
        studentsTableBody.querySelectorAll('tr[data-name]').forEach(row => {
            row.style.display = (row._searchHidden || row._ffHidden || row._typeHidden) ? 'none' : '';
        });
    }

    // Search toggle
    studentSearchBtn.addEventListener('click', () => {
        const visible = studentSearchInput.style.display !== 'none';
        if (visible) {
            studentSearchInput.style.display = 'none';
            studentSearchInput.value = '';
            studentsTableBody.querySelectorAll('tr[data-name]').forEach(r => { r._searchHidden = false; });
            applyVisibility();
        } else {
            studentSearchInput.style.display = 'block';
            studentSearchInput.focus();
        }
    });

    studentSearchInput.addEventListener('input', function() {
        const q = this.value.toLowerCase().trim();
        studentsTableBody.querySelectorAll('tr[data-name]').forEach(row => {
            row._searchHidden = q !== '' && !row.dataset.name.toLowerCase().includes(q);
        });
        applyVisibility();
    });

    // Sort — cycles: date ↑ → date ↓ → name A→Z → name Z→A → repeat
    let studentSortState = 0;
    const studentSortCfg = [
        { field: 'date', dir: 'asc',  icon: 'calendar_month', title: 'Fecha ↑' },
        { field: 'date', dir: 'desc', icon: 'calendar_month', title: 'Fecha ↓' },
        { field: 'name', dir: 'asc',  icon: 'sort_by_alpha',  title: 'Nombre A→Z' },
        { field: 'name', dir: 'desc', icon: 'sort_by_alpha',  title: 'Nombre Z→A' },
    ];

    studentSortBtn.addEventListener('click', () => {
        studentSortState = (studentSortState + 1) % 4;
        const cfg = studentSortCfg[studentSortState];
        studentSortIcon.textContent = cfg.icon;
        studentSortBtn.title = cfg.title;
        const rows = Array.from(studentsTableBody.querySelectorAll('tr[data-name]'));
        rows.sort((a, b) => {
            if (cfg.field === 'name') {
                const na = a.dataset.name.toLowerCase(), nb = b.dataset.name.toLowerCase();
                return cfg.dir === 'asc' ? na.localeCompare(nb) : nb.localeCompare(na);
            } else {
                const da = parseInt(a.dataset.date), db = parseInt(b.dataset.date);
                return cfg.dir === 'asc' ? da - db : db - da;
            }
        });
        rows.forEach(row => studentsTableBody.appendChild(row));
    });

    // ==================== FUN FRIDAY ====================
    function getCsrf() {
        return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='))?.split('=')[1]||'';
    }

    // Returns sort priority 1(green)→2(yellow✓)→3(yellow✗)→4(grey)
    function getFFCategory(row) {
        const t = row.dataset.ffThis === '1', l = row.dataset.ffLast === '1';
        if (t && !l) return 1;
        if (t && l)  return 2;
        if (!t && l) return 3;
        return 4;
    }

    function updateFFIcon(btn, isThis, isLast) {
        const span = btn.querySelector('.ff-icon');
        const row = btn.closest('tr');
        row.dataset.ffThis = isThis ? '1' : '0';
        if (isThis && !isLast)       { span.textContent = 'check_circle'; span.style.color = '#22c55e'; }
        else if (isThis && isLast)   { span.textContent = 'check_circle'; span.style.color = '#f59e0b'; }
        else if (!isThis && isLast)  { span.textContent = 'cancel';       span.style.color = '#f59e0b'; }
        else                         { span.textContent = 'cancel';       span.style.color = '#d1d5db'; }
    }

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

    // FF Filter: 0=all → 1=not-in-this-week → 2=in-this-week → 0
    const studentFFFilterBtn = document.getElementById('studentFFFilterBtn');
    const studentFFFilterIcon = document.getElementById('studentFFFilterIcon');
    let ffFilterState = 0;

    function applyFFFilter() {
        studentsTableBody.querySelectorAll('tr[data-name]').forEach(row => {
            const isThis = row.dataset.ffThis === '1';
            row._ffHidden = (ffFilterState === 1 && isThis) || (ffFilterState === 2 && !isThis);
        });
        applyVisibility();
    }

    const ffFilterCfg = [
        { icon: 'celebration',   title: 'Filtrar por Fun Friday',          bg: '',        color: '' },
        { icon: 'cancel',        title: 'Mostrando: Sin FF esta semana',   bg: '#6b7280', color: '#ffffff' },
        { icon: 'check_circle',  title: 'Mostrando: Con FF esta semana',   bg: '#22c55e', color: '#ffffff' },
    ];

    studentFFFilterBtn.addEventListener('click', () => {
        ffFilterState = (ffFilterState + 1) % 3;
        const cfg = ffFilterCfg[ffFilterState];
        studentFFFilterIcon.textContent = cfg.icon;
        studentFFFilterBtn.title = cfg.title;
        studentFFFilterBtn.style.background = cfg.bg;
        studentFFFilterBtn.style.color = cfg.color;
        applyFFFilter();
    });

    // ==================== STUDENT TYPE FILTER (All / Children / Adults) ====================
    const studentTypeFilterBtn = document.getElementById('studentTypeFilterBtn');
    const studentTypeFilterIcon = document.getElementById('studentTypeFilterIcon');
    let typeFilterState = 0; // 0=all, 1=children, 2=adults

    const typeFilterCfg = [
        { icon: 'groups',       title: 'Todos los estudiantes',   bg: '', color: '' },
        { icon: 'child_care',   title: 'Solo niños',              bg: '#3b82f6', color: '#ffffff' },
        { icon: 'person',       title: 'Solo adultos',            bg: '#f59e0b', color: '#ffffff' },
        { icon: 'translate',    title: 'Cheque idioma',            bg: '#059669', color: '#ffffff' },
    ];

    function applyTypeFilter() {
        studentsTableBody.querySelectorAll('tr[data-name]').forEach(row => {
            const isAdult = row.dataset.isAdult === '1';
            const hasLC = row.dataset.hasLc === '1';
            if (typeFilterState === 0) row._typeHidden = false;
            else if (typeFilterState === 1) row._typeHidden = isAdult;
            else if (typeFilterState === 2) row._typeHidden = !isAdult;
            else if (typeFilterState === 3) row._typeHidden = !hasLC;
        });
        applyVisibility();
    }

    studentTypeFilterBtn.addEventListener('click', () => {
        typeFilterState = (typeFilterState + 1) % 4;
        const cfg = typeFilterCfg[typeFilterState];
        studentTypeFilterIcon.textContent = cfg.icon;
        studentTypeFilterBtn.title = cfg.title;
        studentTypeFilterBtn.style.background = cfg.bg;
        studentTypeFilterBtn.style.color = cfg.color;
        applyTypeFilter();
    });

    // Form validation
    form.addEventListener('submit', (e) => {
        const selectedParents = document.querySelectorAll('input[name="parents"]:checked');
        if (selectedParents.length === 0) {
            e.preventDefault();
            alert('Debe seleccionar al menos un padre/tutor para el estudiante.');
            return;
        }
    });

    // ==================== NEW STUDENT DROPDOWN ====================
    const newStudentBtn = document.getElementById('newStudentBtn');
    const newStudentMenu = document.getElementById('newStudentMenu');
    const newStudentArrow = document.getElementById('newStudentArrow');

    newStudentBtn.addEventListener('click', () => {
        const open = !newStudentMenu.classList.contains('hidden');
        newStudentMenu.classList.toggle('hidden');
        newStudentArrow.textContent = open ? 'expand_more' : 'expand_less';
    });

    document.addEventListener('click', (e) => {
        if (!document.getElementById('newStudentDropdown').contains(e.target)) {
            newStudentMenu.classList.add('hidden');
            newStudentArrow.textContent = 'expand_more';
        }
    });
});
