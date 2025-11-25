document.addEventListener('DOMContentLoaded', () => {
    // Verificar si los elementos existen antes de usarlos
    const checkbox = document.getElementById('useDefaultPrompt');
    const promptArea = document.getElementById('customPrompt');
    const promptContainer = document.getElementById('customPromptContainer');
    const form = document.getElementById('analysisForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn ? submitBtn.querySelector('span') : null;
    const btnIcon = submitBtn ? submitBtn.querySelector('i') : null;

    // Mode selector elements
    const modeBtns = document.querySelectorAll('.mode-btn');
    const urlGroup = document.getElementById('urlGroup');
    const runIdGroup = document.getElementById('runIdGroup');
    const adUrlInput = document.getElementById('adUrl');
    const runIdInput = document.getElementById('runId');

    // Results elements
    const resultsSection = document.getElementById('resultsSection');
    const resultsMessage = document.getElementById('resultsMessage');
    const pdfLink = document.getElementById('pdfLink');
    const jsonLink = document.getElementById('jsonLink');

    let currentMode = 'url'; // default mode
    // API is on port 8001, frontend on 3001
    const API_BASE = 'http://localhost:8001';

    // Toggle Custom Prompt (solo si existe)
    if (checkbox && promptArea && promptContainer) {
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                promptArea.disabled = true;
                promptContainer.classList.add('disabled');
                promptContainer.classList.remove('enabled');
                promptArea.value = '';
            } else {
                promptArea.disabled = false;
                promptContainer.classList.remove('disabled');
                promptContainer.classList.add('enabled');
                promptArea.focus();
            }
        });
    }

    // Mode Selector
    if (modeBtns && modeBtns.length > 0) {
        modeBtns.forEach((btn, index) => {
            // Asegurar que el botón tenga pointer-events habilitado
            btn.style.pointerEvents = 'auto';
            btn.style.cursor = 'pointer';
            
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('Botón clickeado:', btn.dataset.mode || btn.getAttribute('data-mode'));
                
                // Update active state
                modeBtns.forEach(b => {
                    b.classList.remove('active');
                });
                btn.classList.add('active');

                // Get selected mode
                currentMode = btn.dataset.mode || btn.getAttribute('data-mode');
                console.log('Modo actual:', currentMode);

                // Toggle input groups
                if (currentMode === 'url') {
                    if (urlGroup) urlGroup.classList.remove('hidden');
                    if (runIdGroup) runIdGroup.classList.add('hidden');
                    if (adUrlInput) adUrlInput.value = '';
                } else if (currentMode === 'runid') {
                    if (urlGroup) urlGroup.classList.add('hidden');
                    if (runIdGroup) runIdGroup.classList.remove('hidden');
                    if (runIdInput) runIdInput.value = '';
                }

                // Hide results
                if (resultsSection) resultsSection.classList.add('hidden');

                // Reinitialize icons
                if (typeof lucide !== 'undefined' && lucide.createIcons) {
                    lucide.createIcons();
                }
            });
        });
    } else {
        console.error('No se encontraron botones de modo');
    }

    // Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Validate input based on mode
        let inputValue;
        if (currentMode === 'url') {
            inputValue = adUrlInput.value.trim();
            if (!inputValue) {
                shakeElement(adUrlInput);
                return;
            }
        } else {
            inputValue = runIdInput.value.trim();
            if (!inputValue) {
                shakeElement(runIdInput);
                return;
            }
        }

        // Hide previous results
        resultsSection.classList.add('hidden');

        // Set loading state
        submitBtn.disabled = true;
        const originalText = btnText.textContent;
        btnText.textContent = 'Analizando...';
        submitBtn.style.opacity = '0.8';

        try {
            let response;

            if (currentMode === 'url') {
                // Call nuevo endpoint analyze-url-with-download
                response = await fetch(`${API_BASE}/api/v1/apify/facebook/analyze-url-with-download`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: inputValue,
                        count: 100,
                        timeout: 600
                    })
                });
            } else {
                // Call analyze-local-and-pdf endpoint
                response = await fetch(`${API_BASE}/api/v1/apify/facebook/analyze-local-and-pdf?run_id=${encodeURIComponent(inputValue)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
            }

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error en el análisis');
            }

            const data = await response.json();

            // Show success state
            btnText.textContent = '¡Análisis Completado!';
            submitBtn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

            // Display results
            displayResults(data);

            // Descargar PDF automáticamente para ambos modos
            if (data.pdf_path && data.run_id) {
                await downloadPDF(data.run_id);
            }

            // Reset button after delay
            setTimeout(() => {
                btnText.textContent = originalText;
                submitBtn.style.background = '';
                submitBtn.style.opacity = '1';
                submitBtn.disabled = false;
            }, 2000);

        } catch (error) {
            console.error('Error:', error);

            // Show error state
            btnText.textContent = 'Error en el análisis';
            submitBtn.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';

            // Show error message
            alert(`Error: ${error.message}`);

            // Reset button
            setTimeout(() => {
                btnText.textContent = originalText;
                submitBtn.style.background = '';
                submitBtn.style.opacity = '1';
                submitBtn.disabled = false;
            }, 2000);
        }
    });

    // Display Results Function
    function displayResults(data) {
        const runId = data.run_id || 'N/A';
        const pdfPath = data.pdf_path || '';
        const jsonPath = data.json_report || '';

        // Set message
        resultsMessage.textContent = `Análisis completado exitosamente para Run ID: ${runId}`;

        // Set PDF link - usar el endpoint de descarga
        if (pdfPath && runId) {
            pdfLink.href = `${API_BASE}/api/v1/apify/facebook/pdf/${runId}`;
            pdfLink.style.display = 'flex';
        } else {
            pdfLink.style.display = 'none';
        }

        // Set JSON link - mantener formato actual si existe endpoint, sino ocultar
        if (jsonPath) {
            const jsonFilename = jsonPath.split('\\').pop().split('/').pop();
            jsonLink.href = `${API_BASE}/api/v1/apify/facebook/saved/${runId}/reports/${jsonFilename}`;
            jsonLink.style.display = 'flex';
        } else {
            jsonLink.style.display = 'none';
        }

        // Show results section
        resultsSection.classList.remove('hidden');

        // Reinitialize icons
        lucide.createIcons();

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Función para descargar PDF automáticamente
    async function downloadPDF(runId) {
        try {
            const pdfUrl = `${API_BASE}/api/v1/apify/facebook/pdf/${runId}`;
            
            // Descargar el PDF
            const response = await fetch(pdfUrl);
            
            if (!response.ok) {
                console.error('Error descargando PDF:', response.statusText);
                return;
            }
            
            // Obtener el blob
            const blob = await response.blob();
            
            // Crear URL temporal y descargar
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Reporte_Analisis_Completo_${runId}.pdf`;
            document.body.appendChild(a);
            a.click();
            
            // Limpiar
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            console.log('PDF descargado exitosamente');
        } catch (error) {
            console.error('Error al descargar PDF automáticamente:', error);
            // No mostrar error al usuario, solo log
        }
    }

    // Helper: Shake animation for validation error
    function shakeElement(element) {
        element.style.animation = 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both';
        element.style.borderColor = '#ef4444';

        setTimeout(() => {
            element.style.animation = '';
            element.style.borderColor = '';
        }, 500);
    }

    // Add shake keyframes dynamically
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
        @keyframes shake {
            10%, 90% { transform: translate3d(-1px, 0, 0); }
            20%, 80% { transform: translate3d(2px, 0, 0); }
            30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
            40%, 60% { transform: translate3d(4px, 0, 0); }
        }
    `;
    document.head.appendChild(styleSheet);
});
