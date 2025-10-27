// automation.js
const months = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

function formatDateToSpanish(dateStr) {
    if (!dateStr) return '[Fecha]';
    try {
        const [year, month, day] = dateStr.split('-').map(Number);
        return `${day} ${months[month - 1]} ${year}`;
    } catch {
        return '[Fecha Inválida]';
    }
}

function updatePreview() {
    const sprintNumber = document.getElementById('sprint_number').value.trim();
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    const portfolioPreview = `Sprint ${sprintNumber || '[Número]'} - ${formatDateToSpanish(startDate)} al ${formatDateToSpanish(endDate)}`;
    document.getElementById('portfolio_preview').textContent = portfolioPreview;

    document.getElementById('sprint_preview').textContent = sprintNumber || '[Sprint Number]';
    document.getElementById('sprint_preview2').textContent = sprintNumber || '[Sprint Number]';
}

function initializeForm() {
    // Filtrar caracteres no numéricos en tiempo real
    document.getElementById('sprint_number').addEventListener('input', function(e) {
        e.target.value = e.target.value.replace(/[^0-9]/g, '').slice(0, 5);
        updatePreview();
    });

    // Inicializar Flatpickr para selector de rango de fechas
    flatpickr("#date_range", {
        mode: "range",
        dateFormat: "Y-m-d",
        locale: "es",
        onClose: function(selectedDates, dateStr, instance) {
            if (selectedDates.length === 2) {
                document.getElementById('start_date').value = selectedDates[0].toISOString().split('T')[0];
                document.getElementById('end_date').value = selectedDates[0].toISOString().split('T')[0];
                updatePreview();
            }
        }
    });

    // Manejar el envío del formulario
    document.getElementById('automation-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const sprintNumber = document.getElementById('sprint_number').value.trim();
        const startDate = document.getElementById('start_date').value;
        const endDate = document.getElementById('end_date').value;

        // Validaciones
        if (!sprintNumber || !/^\d{1,5}$/.test(sprintNumber)) {
            alert('El número de sprint es obligatorio y debe ser un número válido (no negativo, máximo 5 dígitos).');
            return;
        }
        if (!startDate) {
            alert('La fecha de inicio es obligatoria.');
            return;
        }
        if (!endDate) {
            alert('La fecha de fin es obligatoria.');
            return;
        }
        if (new Date(endDate) <= new Date(startDate)) {
            alert('La fecha de fin debe ser posterior a la fecha de inicio.');
            return;
        }

        // Mostrar indicador de carga
        document.getElementById('loading').style.display = 'block';
        document.getElementById('results_table').style.display = 'none';
        document.getElementById('results_body').innerHTML = '';

        const formData = new FormData();
        formData.append('sprint_number', sprintNumber);
        formData.append('start_date', startDate);
        formData.append('end_date', endDate);

        try {
            const response = await fetch('/run', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            document.getElementById('loading').style.display = 'none';

            // Manejar error
            if (result.error) {
                alert(`Error: ${result.error}`);
                return;
            }

            // Mostrar mensaje de éxito (o fallback si no hay mensaje)
            const successMessage = result.message || `Automatización completada para Sprint ${sprintNumber} (${formatDateToSpanish(startDate)} - ${formatDateToSpanish(endDate)})`;
            alert(successMessage);

            // Mostrar resultados en la tabla
            if (Array.isArray(result.results) && result.results.length > 0) {
                const tbody = document.getElementById('results_body');
                result.results.forEach(item => {
                    // Validar que el item tenga todas las propiedades necesarias
                    if (!item.type || !item.name || !item.team || !item.url) {
                        console.error('Datos incompletos en item:', item);
                        return;
                    }
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.type}</td>
                        <td class="name-cell">${item.name}</td>
                        <td>${item.team}</td>
                        <td class="url-cell"><a href="${item.url}" target="_blank">${item.url}</a></td>
                    `;
                    tbody.appendChild(row);
                });
                document.getElementById('results_table').style.display = 'block';
            } else {
                alert('No se recibieron resultados válidos del servidor.');
            }

            // Restablecer el formulario
            const form = document.getElementById('automation-form');
            form.reset();
            document.getElementById('date_range').value = '';
            document.getElementById('start_date').value = '';
            document.getElementById('end_date').value = '';
            updatePreview();
        } catch (error) {
            document.getElementById('loading').style.display = 'none';
            alert(`Error en la comunicación con el servidor: ${error.message}`);
            console.error('Error en fetch:', error);
        }
    });
}

// Inicializar cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', () => {
    updatePreview();
    initializeForm();
});