document.addEventListener('DOMContentLoaded', (event) => {
    console.log("¡El DOM está listo! El script está escuchando.");

    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');
    const sistemaInput = document.getElementById('sistema');

    // Detectar el sistema según la URL
    let sistema = '';
    if (window.location.pathname.includes('login_claro')) {
        sistema = 'claro';
    } else if (window.location.pathname.includes('login_colpensiones')) {
        sistema = 'colpensiones';
    } else if (window.location.pathname.includes('login_asana')) {
        sistema = 'asana';
    } else if (window.location.pathname.includes('login_posweb')) {
        sistema = 'POSWEB';
    } else if (window.location.pathname.includes('login_larebaja')) {
        sistema = 'larebaja';
    } else if (window.location.pathname.includes('login_mensajeros')) {
        sistema = 'mensajeros';
    } else if (window.location.pathname.includes('login_docuseal')) {
        sistema = 'DocusealOP';
    }
    if (sistemaInput) {
        sistemaInput.value = sistema;
    }

    // If a "forgot password" link exists, add the sistema as a query param so the form knows the context
    try {
        const forgotLink = document.getElementById('forgotLink');
        if (forgotLink && sistema) {
            const url = new URL(forgotLink.href, window.location.origin);
            url.searchParams.set('sistema', sistema);
            forgotLink.href = url.toString();
        }
    } catch (e) {
        console.debug('No se pudo ajustar el enlace de olvido de contraseña:', e);
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const sistema = sistemaInput ? sistemaInput.value : '';

            const loginData = {
                username: username,
                password: password,
                sistema: sistema
            };

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(loginData)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    errorMessage.textContent = errorData.message || 'Error de autenticación.';
                    return;
                }

                const data = await response.json();

                if (data.success) {
                    errorMessage.textContent = '';
                    window.location.href = data.redirect_url;
                } else {
                    errorMessage.textContent = data.message;
                }
            } catch (error) {
                errorMessage.textContent = 'Hubo un error de conexión con el servidor.';
            }
        });
    }
});