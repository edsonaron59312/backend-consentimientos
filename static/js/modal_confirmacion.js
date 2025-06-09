// Modal de doble paso: confirmación de datos y éxito
// Requiere Bootstrap 5

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('formIngresoCiclos');
    if (!form) return;

    // Crear modal de confirmación si no existe
    if (!document.getElementById('modalConfirmacionDatos')) {
        const modalHtml = `
        <div class="modal fade" id="modalConfirmacionDatos" tabindex="-1" aria-labelledby="modalConfirmacionDatosLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content text-center p-3">
              <div class="modal-body">
                <div class="mb-3">
                  <div style="width:70px;height:70px;margin:auto;border:3px solid #b0bec5;border-radius:50%;display:flex;align-items:center;justify-content:center;">
                    <i class="bi bi-question-lg" style="font-size:2.5rem;color:#90a4ae;"></i>
                  </div>
                </div>
                <h4 class="mb-2 fw-bold">¿Confirmar Registro?</h4>
                <div class="mb-2">
                  <span>Estás a punto de registrar al cliente:</span><br>
                  <span class="fw-bold" id="conf-nombre-cliente">-</span><br>
                  <span>DNI/CE: <span class="fw-bold" id="conf-dni-cliente">-</span></span>
                </div>
                <div class="mb-3">
                  <span>¿Estás seguro de que los datos son correctos?</span>
                </div>
                <div class="d-flex justify-content-center gap-2">
                  <button type="button" class="btn btn-primary" id="btnConfirmarRegistro">Sí, ¡Registrar!</button>
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">No, revisar</button>
                </div>
              </div>
            </div>
          </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    // Crear modal de éxito si no existe
    if (!document.getElementById('modalEnvioExitoso')) {
        const modalHtml = `
        <div class="modal fade" id="modalEnvioExitoso" tabindex="-1" aria-labelledby="modalEnvioExitosoLabel" aria-hidden="true">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content text-center p-3">
              <div class="modal-body">
                <div class="mb-3">
                  <i class="bi bi-check-circle-fill" style="font-size:3rem;color:#43a047;"></i>
                </div>
                <h4 class="mb-2 fw-bold">¡Enviado correctamente!</h4>
                <div class="mb-2">
                  <span>El formulario fue enviado correctamente.</span>
                </div>
                <div class="d-flex justify-content-center">
                  <button type="button" class="btn btn-success" data-bs-dismiss="modal">Aceptar</button>
                </div>
              </div>
            </div>
          </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // Interceptar submit
    form.addEventListener('submit', function(e) {
        // Si ya hay input hidden de confirmación, dejar pasar
        if (form.querySelector('[name="confirm_envio"]')) return;
        e.preventDefault();
        // Obtener datos del formulario
        const nombre = form.querySelector('#nombre_cliente')?.value || '-';
        const dni = form.querySelector('#numero_documento')?.value || '-';
        document.getElementById('conf-nombre-cliente').textContent = nombre;
        document.getElementById('conf-dni-cliente').textContent = dni;
        // Mostrar modal de confirmación
        const modalConfirm = new bootstrap.Modal(document.getElementById('modalConfirmacionDatos'));
        modalConfirm.show();

        // Botón de confirmar
        const btnConfirmar = document.getElementById('btnConfirmarRegistro');
        const onConfirmar = function() {
            // Marcar para evitar loop
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'confirm_envio';
            input.value = '1';
            form.appendChild(input);
            modalConfirm.hide();
            btnConfirmar.removeEventListener('click', onConfirmar);
            // Mostrar modal de éxito después de un pequeño delay
            setTimeout(() => {
                const modalExito = new bootstrap.Modal(document.getElementById('modalEnvioExitoso'));
                modalExito.show();
                // Al cerrar el modal de éxito, enviar el formulario realmente
                const btnAceptar = document.querySelector('#modalEnvioExitoso .btn-success');
                const onAceptar = function() {
                    btnAceptar.removeEventListener('click', onAceptar);
                    form.submit();
                };
                btnAceptar.addEventListener('click', onAceptar);
            }, 300);
        };
        btnConfirmar.addEventListener('click', onConfirmar);
    });
});
