const csrfToken = window.MANAGEMENT_CONFIG.csrfToken;
let editMode = false;

// Toggle sección desplegable
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const iconId = sectionId.replace('-section', '-icon');
    const icon = document.getElementById(iconId);

    section.classList.toggle('hidden');
    icon.style.transform = section.classList.contains('hidden') ? '' : 'rotate(180deg)';
}

// Mostrar/ocultar modal
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = '';
}

// Toast de notificación
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = document.getElementById('toast-icon');

    toastMessage.textContent = message;

    if (type === 'success') {
        toast.querySelector('div').className = 'bg-green-500 text-white px-6 py-3 rounded-lg flex items-center gap-3';
        toastIcon.textContent = 'check_circle';
    } else {
        toast.querySelector('div').className = 'bg-red-500 text-white px-6 py-3 rounded-lg flex items-center gap-3';
        toastIcon.textContent = 'error';
    }

    toast.classList.remove('translate-y-full', 'opacity-0');

    setTimeout(() => {
        toast.classList.add('translate-y-full', 'opacity-0');
    }, 3000);
}

// Modo edición de configuración
document.getElementById('btn-edit-values').addEventListener('click', function() {
    editMode = !editMode;
    const inputs = document.querySelectorAll('.config-input');
    const saveContainer = document.getElementById('save-config-container');
    const editBtn = document.getElementById('btn-edit-values');

    if (editMode) {
        inputs.forEach(input => {
            input.disabled = false;
            input.classList.remove('bg-neutral-100', 'cursor-not-allowed');
            input.classList.add('bg-white', 'focus:ring-2', 'focus:ring-primary-500', 'focus:border-primary-500');
        });
        saveContainer.classList.remove('hidden');
        editBtn.innerHTML = '<span class="material-symbols-outlined">close</span> Cancelar Edición';
        editBtn.classList.remove('bg-primary-500', 'hover:bg-primary-600');
        editBtn.classList.add('bg-red-500', 'hover:bg-red-600');

        // Abrir sección de precios si está cerrada
        const preciosSection = document.getElementById('precios-section');
        if (preciosSection.classList.contains('hidden')) {
            toggleSection('precios-section');
        }
    } else {
        cancelEdit();
    }
});

function cancelEdit() {
    editMode = false;
    const inputs = document.querySelectorAll('.config-input');
    const saveContainer = document.getElementById('save-config-container');
    const editBtn = document.getElementById('btn-edit-values');

    inputs.forEach(input => {
        input.disabled = true;
        input.classList.add('bg-neutral-100', 'cursor-not-allowed');
        input.classList.remove('bg-white', 'focus:ring-2', 'focus:ring-primary-500', 'focus:border-primary-500');
    });
    saveContainer.classList.add('hidden');
    editBtn.innerHTML = '<span class="material-symbols-outlined">edit</span> Cambiar Valores';
    editBtn.classList.add('bg-primary-500', 'hover:bg-primary-600');
    editBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
}

document.getElementById('btn-cancel-edit').addEventListener('click', cancelEdit);

// Guardar configuración
document.getElementById('btn-save-config').addEventListener('click', async function() {
    const data = {};
    document.querySelectorAll('.config-input').forEach(input => {
        if (!input.disabled && input.name) {
            const parsedValue = Number.parseFloat(String(input.value).replace(',', '.'));
            if (Number.isNaN(parsedValue)) {
                showToast('Revisa los importes antes de guardar', 'error');
                return;
            }
            data[input.name] = parsedValue;
        }
    });

    try {
        const response = await fetch(window.MANAGEMENT_CONFIG.updateConfigUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            cancelEdit();
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('Error al guardar la configuración', 'error');
    }
});

// Nuevo Profesor
document.getElementById('btn-new-teacher').addEventListener('click', function() {
    openModal('modal-teacher');
});

document.getElementById('form-teacher').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
        first_name: formData.get('first_name'),
        last_name: formData.get('last_name'),
        email: formData.get('email'),
        phone: formData.get('phone') || '',
        admin: formData.get('admin') === 'on'
    };

    try {
        const response = await fetch(window.MANAGEMENT_CONFIG.createTeacherUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            closeModal('modal-teacher');
            // Recargar página para ver el nuevo profesor
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('Error al crear el profesor', 'error');
    }
});

// Nuevo Grupo
document.getElementById('btn-new-group').addEventListener('click', async function() {
    // Refrescar lista de profesores antes de abrir
    try {
        const response = await fetch(window.MANAGEMENT_CONFIG.getTeachersUrl);
        const data = await response.json();

        const select = document.getElementById('select-teacher');
        select.innerHTML = '<option value="">Seleccionar profesor...</option>';

        data.teachers.forEach(teacher => {
            const option = document.createElement('option');
            option.value = teacher.id;
            option.textContent = teacher.full_name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error al cargar profesores:', error);
    }

    openModal('modal-group');
});

document.getElementById('form-group').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
        group_name: formData.get('group_name'),
        color: formData.get('color') || '#6366f1',
        teacher_id: parseInt(formData.get('teacher_id'))
    };

    try {
        const response = await fetch(window.MANAGEMENT_CONFIG.createGroupUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showToast(result.message, 'success');
            closeModal('modal-group');
            // Recargar página para ver el nuevo grupo
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.message, 'error');
        }
    } catch (error) {
        showToast('Error al crear el grupo', 'error');
    }
});

// Cerrar modales al hacer click fuera
document.querySelectorAll('[id^="modal-"]').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal(this.id);
        }
    });
});

// Cerrar modales con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('[id^="modal-"]').forEach(modal => {
            if (modal.style.display !== 'none') closeModal(modal.id);
        });
    }
});
