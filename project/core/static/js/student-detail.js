// student-detail.js — extracted from student_detail.html
// Expects window.STUDENT_ID to be set by the template

const STUDENT_ID = window.STUDENT_ID;

function getCsrf() {
    return document.cookie.split(';').map(c=>c.trim()).find(c=>c.startsWith('csrftoken='))?.split('=')[1]||'';
}

function addFunFriday() {
    const inp = document.getElementById('ff-new-date');
    const d = inp.value;
    if (!d) return;
    fetch(`/api/students/${STUDENT_ID}/fun-friday/add/`, {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-CSRFToken':getCsrf()},
        body: JSON.stringify({date: d}),
    }).then(r=>r.json()).then(data => {
        if (data.success) { inp.value=''; location.reload(); }
        else alert(data.error);
    });
}

function removeFunFriday(d) {
    if (!confirm('\u00bfEliminar esta fecha?')) return;
    fetch(`/api/students/${STUDENT_ID}/fun-friday/remove/`, {
        method: 'POST',
        headers: {'Content-Type':'application/json','X-CSRFToken':getCsrf()},
        body: JSON.stringify({date: d}),
    }).then(r=>r.json()).then(data => {
        if (data.success) location.reload();
        else alert(data.error);
    });
}

// ==================== MODALITY TOGGLE ====================
document.querySelectorAll('.modality-toggle-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const studentId = this.dataset.studentId;
        const current = this.dataset.current;
        const newModality = current === 'monthly' ? 'quarterly' : 'monthly';
        const enrollmentId = this.dataset.enrollmentId;

        if (!confirm(`\u00bfCambiar modalidad de pago a ${newModality === 'monthly' ? 'Mensual' : 'Trimestral'}?`)) return;

        fetch(`/api/students/${studentId}/enrollment/modality/`, {
            method: 'POST',
            headers: {'Content-Type':'application/json','X-CSRFToken':getCsrf()},
            body: JSON.stringify({payment_modality: newModality}),
        }).then(r=>r.json()).then(data => {
            if (data.success) {
                // Update the label
                const label = document.getElementById(`modality-label-${enrollmentId}`);
                if (label) {
                    label.textContent = data.payment_modality_display;
                    label.className = label.className.replace(/bg-\w+-100 text-\w+-800/g, '');
                    if (newModality === 'monthly') {
                        label.classList.add('bg-blue-100', 'text-blue-800');
                    } else {
                        label.classList.add('bg-green-100', 'text-green-800');
                    }
                }
                this.dataset.current = newModality;
            } else {
                alert(data.error || 'Error al cambiar modalidad');
            }
        }).catch(err => {
            console.error('Error:', err);
            alert('Error de conexi\u00f3n');
        });
    });
});
