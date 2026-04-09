(function () {
    var toggleBtn   = document.getElementById('emailPreviewToggleBtn');
    var toggleIcon  = document.getElementById('emailPreviewToggleIcon');
    var toggleLabel = document.getElementById('emailPreviewToggleLabel');
    var panel       = document.getElementById('emailPreviewPanel');
    var spinner     = document.getElementById('emailPreviewSpinner');
    var bodyEl      = document.getElementById('emailPreviewBody');
    var refreshBtn  = document.getElementById('emailPreviewRefreshBtn');
    var testSendBtn = document.getElementById('previewTestSendBtn');
    var feedback    = document.getElementById('previewTestFeedback');

    function getForm() {
        return toggleBtn ? (toggleBtn.closest('form') || document.querySelector('form')) : document.querySelector('form');
    }

    function fetchPreview() {
        var form = getForm();
        if (!form) return;
        var data = new FormData(form);
        data.set('action', 'preview');

        bodyEl.classList.add('hidden');
        spinner.classList.remove('hidden');

        fetch(window.location.pathname, {
            method: 'POST',
            headers: { 'X-CSRFToken': data.get('csrfmiddlewaretoken') },
            body: data,
        })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            spinner.classList.add('hidden');
            bodyEl.classList.remove('hidden');
            if (d.html) bodyEl.innerHTML = d.html;
        })
        .catch(function () {
            spinner.classList.add('hidden');
            bodyEl.classList.remove('hidden');
        });
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            var isHidden = panel.classList.toggle('hidden');
            if (isHidden) {
                toggleIcon.textContent  = 'visibility';
                toggleLabel.textContent = 'Ver vista previa del email';
            } else {
                toggleIcon.textContent  = 'visibility_off';
                toggleLabel.textContent = 'Ocultar vista previa';
                fetchPreview();
            }
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchPreview);
    }

    if (testSendBtn) {
        testSendBtn.addEventListener('click', function () {
            var form = getForm();
            if (!form) return;
            var data = new FormData(form);
            data.set('action', 'test_send');

            testSendBtn.disabled = true;
            testSendBtn.innerHTML = '<span class="material-symbols-outlined">sync</span> Enviando…';
            feedback.classList.add('hidden');

            fetch(window.location.pathname, {
                method: 'POST',
                headers: { 'X-CSRFToken': data.get('csrfmiddlewaretoken') },
                body: data,
            })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                feedback.className = d.ok
                    ? 'mb-3 p-3 rounded-lg text-sm font-medium border bg-green-50 text-green-800 border-green-200'
                    : 'mb-3 p-3 rounded-lg text-sm font-medium border bg-red-50 text-red-800 border-red-200';
                feedback.textContent = d.message || (d.ok ? '✅ Enviado' : '❌ Error');
                feedback.classList.remove('hidden');
                testSendBtn.disabled = false;
                testSendBtn.innerHTML = '<span class="material-symbols-outlined">science</span> Enviar prueba';
            })
            .catch(function () {
                feedback.className = 'mb-3 p-3 rounded-lg text-sm font-medium border bg-red-50 text-red-800 border-red-200';
                feedback.textContent = '❌ Error de conexión';
                feedback.classList.remove('hidden');
                testSendBtn.disabled = false;
                testSendBtn.innerHTML = '<span class="material-symbols-outlined">science</span> Enviar prueba';
            });
        });
    }
}());

/**
 * Generic form submit handler for app forms.
 * Add data-confirm="message" to a form to get a confirmation dialog.
 * The submit button inside the form gets disabled + spinner on submit.
 */
(function () {
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var msg = form.dataset.confirm;
            if (msg && !confirm(msg)) {
                e.preventDefault();
                return;
            }
            var btn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin mr-2">sync</span>Enviando...';
            }
        });
    });

    /* Form-specific: receipt type toggle */
    var receiptTypeSelect = document.getElementById('receiptType');
    if (receiptTypeSelect) {
        var childFields = document.getElementById('quarterly-child-fields');
        var adultFields = document.getElementById('adult-fields');
        receiptTypeSelect.addEventListener('change', function () {
            if (childFields) childFields.classList.toggle('hidden', this.value !== 'quarterly_child');
            if (adultFields) adultFields.classList.toggle('hidden', this.value !== 'monthly_adult');
        });
    }

    /* Form-specific: enrollment email type toggle */
    var emailTypeSelect = document.getElementById('emailTypeSelect');
    if (emailTypeSelect) {
        var welcomeFields = document.getElementById('welcome-fields');
        var enrollmentFields = document.getElementById('enrollment-fields');
        emailTypeSelect.addEventListener('change', function () {
            if (welcomeFields) welcomeFields.classList.toggle('hidden', this.value !== 'welcome');
            if (enrollmentFields) enrollmentFields.classList.toggle('hidden', this.value !== 'enrollment');
        });
    }
}());
