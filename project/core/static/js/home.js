/**
 * home.js — Dashboard todo system and pending students modal.
 * Requires: data-create-todo-url on <body>
 */
document.addEventListener('DOMContentLoaded', function () {
    const todoText = document.getElementById('todoText');
    const addTodoBtn = document.getElementById('addTodoBtn');
    const todoList = document.getElementById('todoList');
    const todoError = document.getElementById('todoError');
    const customDate = document.getElementById('customDate');
    const dateBtns = document.querySelectorAll('.todo-date-btn');
    const createTodoUrl = document.body.dataset.createTodoUrl || '/api/todos/create/';

    let selectedDate = getTodayISO();
    let activeMode = 'hoy';

    function getTodayISO() {
        const d = new Date();
        return d.toISOString().split('T')[0];
    }

    function getThisWeekFridayISO() {
        const d = new Date();
        const day = d.getDay();
        const daysUntilFriday = day <= 5 ? 5 - day : 7 - day + 5;
        d.setDate(d.getDate() + daysUntilFriday);
        return d.toISOString().split('T')[0];
    }

    function formatDisplayDate(isoStr) {
        const [y, m, da] = isoStr.split('-');
        return `${da}/${m}/${y}`;
    }

    function setActiveBtn(mode) {
        activeMode = mode;
        dateBtns.forEach(btn => {
            const isActive = btn.dataset.mode === mode;
            btn.classList.toggle('bg-primary-100', isActive);
            btn.classList.toggle('text-primary-700', isActive);
            btn.classList.toggle('ring-2', isActive);
            btn.classList.toggle('ring-primary-400', isActive);
            btn.classList.toggle('bg-neutral-100', !isActive);
            btn.classList.toggle('text-neutral-700', !isActive);
        });
        customDate.classList.toggle('hidden', mode !== 'fecha');
    }

    document.getElementById('btnHoy').addEventListener('click', function () {
        selectedDate = getTodayISO();
        setActiveBtn('hoy');
    });

    document.getElementById('btnSemana').addEventListener('click', function () {
        selectedDate = getThisWeekFridayISO();
        setActiveBtn('semana');
    });

    document.getElementById('btnFecha').addEventListener('click', function () {
        setActiveBtn('fecha');
        customDate.focus();
        if (customDate.value) selectedDate = customDate.value;
    });

    customDate.addEventListener('change', function () {
        if (this.value) selectedDate = this.value;
    });

    function getCsrfToken() {
        return document.cookie.split(';')
            .map(c => c.trim())
            .find(c => c.startsWith('csrftoken='))
            ?.split('=')[1] || '';
    }

    function showError(msg) {
        todoError.textContent = msg;
        todoError.classList.remove('hidden');
        setTimeout(() => todoError.classList.add('hidden'), 3000);
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function buildTodoRow(todo) {
        const overdue = todo.is_overdue;
        const textClass = overdue ? 'text-red-500 font-medium' : 'text-neutral-700';
        const dateClass = overdue ? 'text-red-400 font-semibold' : 'text-neutral-400';
        const row = document.createElement('div');
        row.id = `todo-${todo.id}`;
        row.className = 'todo-item flex items-center gap-3 py-3 px-1 group hover:bg-neutral-50 rounded-lg transition-colors';
        row.dataset.overdue = overdue ? 'true' : 'false';
        row.innerHTML = `
            <input type="checkbox" class="todo-checkbox w-4 h-4 rounded border-neutral-300 text-primary-500 cursor-pointer accent-primary-500" data-id="${todo.id}">
            <span class="flex-1 text-sm ${textClass}">${escapeHtml(todo.text)}</span>
            <span class="text-xs ${dateClass} shrink-0">${todo.due_date_display}</span>
        `;
        row.querySelector('.todo-checkbox').addEventListener('change', handleCheckbox);
        return row;
    }

    function insertTodoSorted(row, isoDate) {
        const emptyMsg = document.getElementById('emptyTodos');
        if (emptyMsg) emptyMsg.remove();
        const existing = todoList.querySelectorAll('.todo-item');
        let inserted = false;
        for (const el of existing) {
            const elIso = el.dataset.isoDate || '9999-12-31';
            if (isoDate <= elIso) {
                todoList.insertBefore(row, el);
                inserted = true;
                break;
            }
        }
        if (!inserted) todoList.appendChild(row);
        row.dataset.isoDate = isoDate;
    }

    addTodoBtn.addEventListener('click', submitTodo);
    todoText.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') submitTodo();
    });

    function submitTodo() {
        if (activeMode === 'fecha' && customDate.value) {
            selectedDate = customDate.value;
        }
        const text = todoText.value.trim();
        if (!text) { showError('Escribe una tarea antes de añadirla'); return; }
        if (!selectedDate) { showError('Selecciona una fecha'); return; }

        addTodoBtn.disabled = true;

        fetch(createTodoUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ text, due_date: selectedDate }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const row = buildTodoRow(data.todo);
                insertTodoSorted(row, data.todo.due_date_iso);
                todoText.value = '';
            } else {
                showError(data.error || 'Error al añadir la tarea');
            }
        })
        .catch(() => showError('Error de conexión'))
        .finally(() => { addTodoBtn.disabled = false; });
    }

    function handleCheckbox(e) {
        const checkbox = e.target;
        const id = checkbox.dataset.id;
        const row = document.getElementById(`todo-${id}`);

        checkbox.disabled = true;
        row.style.opacity = '0.4';

        fetch(`/api/todos/${id}/complete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                row.remove();
                if (!todoList.querySelector('.todo-item')) {
                    const p = document.createElement('p');
                    p.id = 'emptyTodos';
                    p.className = 'text-sm text-neutral-400 py-4 text-center';
                    p.textContent = 'No hay tareas pendientes';
                    todoList.appendChild(p);
                }
            } else {
                checkbox.disabled = false;
                row.style.opacity = '1';
            }
        })
        .catch(() => {
            checkbox.disabled = false;
            row.style.opacity = '1';
        });
    }

    // Attach listeners to server-rendered rows
    document.querySelectorAll('.todo-checkbox').forEach(cb => {
        cb.addEventListener('change', handleCheckbox);
    });

    // Pending students modal
    const pendingTrigger = document.getElementById('pendingCountTrigger');
    const pendingModal = document.getElementById('pending-modal');
    const pendingCloseBtn = document.getElementById('pending-close-btn');

    function openPendingModal() { pendingModal.style.display = 'flex'; }
    function closePendingModal() { pendingModal.style.display = 'none'; }

    if (pendingTrigger) pendingTrigger.addEventListener('click', openPendingModal);
    if (pendingCloseBtn) pendingCloseBtn.addEventListener('click', closePendingModal);
    if (pendingModal) {
        pendingModal.addEventListener('click', (e) => {
            if (e.target === pendingModal) closePendingModal();
        });
    }

    // Store iso dates on server-rendered rows for sorting
    document.querySelectorAll('.todo-item').forEach(row => {
        const dateSpan = row.querySelector('span:last-child');
        if (dateSpan) {
            const parts = dateSpan.textContent.trim().split('/');
            if (parts.length === 3) {
                row.dataset.isoDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
            }
        }
    });
});
