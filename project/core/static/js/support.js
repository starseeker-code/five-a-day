/**
 * Sistema de Soporte - Five a Day
 * Maneja el modal de tickets de soporte y envío al backend
 */

const SupportSystem = {
    // Mapeo de categorías a tipos de backend
    categoryMap: {
        'interfaz': 'frontend',
        'sistema': 'backend',
        'datos': 'database',
        'otro': 'exception'
    },
    
    // Estado del modal
    selectedCategory: null,
    
    /**
     * Inicializa el sistema de soporte
     */
    init() {
        // Event listeners para abrir/cerrar modal
        const openBtn = document.getElementById('support-open-btn');
        const closeBtn = document.getElementById('support-close-btn');
        const modal = document.getElementById('support-modal');
        const backBtn = document.getElementById('support-back-btn');
        const sendBtn = document.getElementById('support-send-btn');
        
        if (openBtn) {
            openBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openModal();
            });
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }
        
        if (backBtn) {
            backBtn.addEventListener('click', () => this.showCategoryStep());
        }
        
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.submitTicket());
        }
        
        // Cerrar modal al hacer click fuera
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }
        
        // Event listeners para categorías
        document.querySelectorAll('.support-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const category = btn.dataset.category;
                this.selectCategory(category);
            });
        });
        
        // Cerrar con ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
                this.closeModal();
            }
        });
    },
    
    /**
     * Abre el modal de soporte
     */
    openModal() {
        const modal = document.getElementById('support-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.showCategoryStep();
        }
    },
    
    /**
     * Cierra el modal de soporte
     */
    closeModal() {
        const modal = document.getElementById('support-modal');
        if (modal) {
            modal.classList.add('hidden');
            this.resetModal();
        }
    },
    
    /**
     * Muestra el paso de selección de categoría
     */
    showCategoryStep() {
        const categoryStep = document.getElementById('support-step-category');
        const messageStep = document.getElementById('support-step-message');
        
        if (categoryStep) categoryStep.classList.remove('hidden');
        if (messageStep) messageStep.classList.add('hidden');
        
        this.selectedCategory = null;
    },
    
    /**
     * Selecciona una categoría y muestra el paso de mensaje
     */
    selectCategory(category) {
        this.selectedCategory = category;
        
        const categoryStep = document.getElementById('support-step-category');
        const messageStep = document.getElementById('support-step-message');
        const categoryLabel = document.getElementById('support-category-label');
        
        if (categoryStep) categoryStep.classList.add('hidden');
        if (messageStep) messageStep.classList.remove('hidden');
        
        // Capitalizar primera letra
        const displayCategory = category.charAt(0).toUpperCase() + category.slice(1);
        if (categoryLabel) categoryLabel.textContent = displayCategory;
        
        // Focus en el textarea
        const textarea = document.getElementById('support-message');
        if (textarea) {
            textarea.focus();
        }
    },
    
    /**
     * Resetea el modal a su estado inicial
     */
    resetModal() {
        this.selectedCategory = null;
        
        const textarea = document.getElementById('support-message');
        if (textarea) textarea.value = '';
        
        const errorMsg = document.getElementById('support-error');
        if (errorMsg) errorMsg.classList.add('hidden');
        
        const successMsg = document.getElementById('support-success');
        if (successMsg) successMsg.classList.add('hidden');
    },
    
    /**
     * Envía el ticket de soporte al backend
     */
    async submitTicket() {
        const textarea = document.getElementById('support-message');
        const sendBtn = document.getElementById('support-send-btn');
        const errorMsg = document.getElementById('support-error');
        const successMsg = document.getElementById('support-success');
        
        const message = textarea ? textarea.value.trim() : '';
        
        // Validar mensaje
        if (!message) {
            if (errorMsg) {
                errorMsg.textContent = 'Por favor, escribe un mensaje';
                errorMsg.classList.remove('hidden');
            }
            return;
        }
        
        if (message.length < 10) {
            if (errorMsg) {
                errorMsg.textContent = 'El mensaje debe tener al menos 10 caracteres';
                errorMsg.classList.remove('hidden');
            }
            return;
        }
        
        // Deshabilitar botón
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">sync</span>';
        }
        
        try {
            // Obtener CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
                || document.querySelector('meta[name="csrf-token"]')?.content
                || this.getCookie('csrftoken');
            
            const response = await fetch('/api/support/submit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    category: this.categoryMap[this.selectedCategory] || 'exception',
                    category_display: this.selectedCategory,
                    message: message,
                    current_url: window.location.pathname
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Mostrar éxito
                if (successMsg) {
                    successMsg.classList.remove('hidden');
                }
                if (errorMsg) errorMsg.classList.add('hidden');
                
                // Cerrar modal después de 2 segundos
                setTimeout(() => {
                    this.closeModal();
                }, 2000);
            } else {
                throw new Error(data.message || 'Error al enviar el ticket');
            }
        } catch (error) {
            console.error('Error enviando ticket:', error);
            if (errorMsg) {
                errorMsg.textContent = error.message || 'Error de conexión. Inténtalo de nuevo.';
                errorMsg.classList.remove('hidden');
            }
        } finally {
            // Restaurar botón
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.innerHTML = '<span class="material-symbols-outlined text-sm">send</span>';
            }
        }
    },
    
    /**
     * Obtiene el valor de una cookie
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    SupportSystem.init();
});
