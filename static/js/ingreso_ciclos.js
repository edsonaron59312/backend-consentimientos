// static/js/ingreso_ciclos.js
document.addEventListener('DOMContentLoaded', function () {
    console.log('ingreso_ciclos.js: DOMContentLoaded - Script iniciado.');

    // --- ELEMENTOS DEL DOM ---
    const form = document.getElementById('formIngresoCiclos');
    
    // CAMBIO: Añadidos elementos para validación en tiempo real
    const numeroDocumentoInput = document.getElementById('numero_documento');
    const nombreClienteInput = document.getElementById('nombre_cliente');
    const celularInput = document.getElementById('celular');
    
    // Elementos existentes
    const cicloBaseSelect = document.getElementById('ciclo_base_seleccionado');
    const cicloFinalManualDiv = document.getElementById('divCicloFinalManual');
    const cicloFinalManualSelect = document.getElementById('ciclo_final_dia_manual');
    const supervisorMsgEl = document.getElementById('supervisorMsg');
    const planSelect = document.getElementById('plan_id');
    const fechaHoyInput = document.getElementById('fecha_hoy');

    const displayCicloFinalDia = document.getElementById('display_ciclo_final_aplicado');
    const displayProrrateoDia = document.getElementById('display_prorrateo_dia');
    const displayFechaCierre = document.getElementById('display_fecha_cierre');
    const displayProrrateoTotal = document.getElementById('display_prorrateo_total');
    const displayFechaActivacion = document.getElementById('display_fecha_activacion');
    const displayFechaPago = document.getElementById('display_fecha_pago');

    // --- DATOS INICIALES ---
    let ciclosDisponibles = [];
    if (cicloFinalManualSelect) {
        ciclosDisponibles = Array.from(cicloFinalManualSelect.options)
                                 .filter(opt => opt.value)
                                 .map(opt => parseInt(opt.value));
        console.log('ingreso_ciclos.js: Ciclos disponibles (manual) cargados del DOM:', ciclosDisponibles);
    } else {
        console.warn('ingreso_ciclos.js: Elemento cicloFinalManualSelect no encontrado.');
    }
    
    // =========================================================================
    // --- NUEVO: VALIDACIÓN DE ENTRADA EN TIEMPO REAL ---
    // =========================================================================

    function enforceNumericOnly(event) {
        // Esta función se asegura de que solo se puedan escribir números en el campo.
        const input = event.target;
        input.value = input.value.replace(/\D/g, ''); // \D es cualquier caracter que NO sea un dígito
    }

    function enforceTextOnly(event) {
        // Esta función se asegura de que solo se puedan escribir letras, espacios y apóstrofes.
        const input = event.target;
        // La expresión regular permite letras del alfabeto inglés y español (con acentos y ñ), espacios y apóstrofes.
        input.value = input.value.replace(/[^a-zA-ZñÑáéíóúÁÉÍÓÚüÜ\s\']/g, '');
    }

    // Aplicar los "escuchadores de eventos" a los inputs correspondientes.
    // El evento 'input' se dispara cada vez que el usuario escribe o pega algo.
    if (numeroDocumentoInput) {
        numeroDocumentoInput.addEventListener('input', enforceNumericOnly);
    }
    if (celularInput) {
        celularInput.addEventListener('input', function(e) {
            // Solo números
            enforceNumericOnly(e);
            // Forzar que el primer dígito sea 9
            if (celularInput.value.length === 1 && celularInput.value !== '9') {
                celularInput.value = '';
            }
            // Limitar a 9 dígitos
            if (celularInput.value.length > 9) {
                celularInput.value = celularInput.value.slice(0, 9);
            }
        });
        // Validación extra al pegar
        celularInput.addEventListener('paste', function(e) {
            setTimeout(function() {
                if (celularInput.value.length > 0 && celularInput.value[0] !== '9') {
                    celularInput.value = '';
                }
                if (celularInput.value.length > 9) {
                    celularInput.value = celularInput.value.slice(0, 9);
                }
            }, 0);
        });
    }
    if (nombreClienteInput) {
        nombreClienteInput.addEventListener('input', enforceTextOnly);
    }

    // =========================================================================
    // --- LÓGICA DE CÁLCULO (Sin cambios en su funcionamiento interno) ---
    // =========================================================================

    function parseDateString(dateString) {
        if (!dateString) { console.warn("parseDateString: dateString vacío"); return null; } 
        const parts = dateString.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; 
            const day = parseInt(parts[2], 10);
            if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
                const dateObj = new Date(year, month, day);
                if (dateObj.getFullYear() === year && dateObj.getMonth() === month && dateObj.getDate() === day) {
                    return dateObj;
                }
            }
        }
        console.warn("Invalid date string provided to parseDateString:", dateString);
        return null;
    }

    function formatDateToDisplay(dateObj) {
        if (!dateObj || !(dateObj instanceof Date) || isNaN(dateObj.getTime())) { console.warn("formatDateToDisplay: dateObj inválido", dateObj); return 'N/A';} 
        const day = String(dateObj.getDate()).padStart(2, '0');
        const month = String(dateObj.getMonth() + 1).padStart(2, '0'); 
        const year = dateObj.getFullYear();
        return `${day}/${month}/${year}`;
    }

    function addMonths(date, months) {
        const d = new Date(date);
        const originalDay = d.getDate();
        d.setMonth(d.getMonth() + months);
        if (d.getDate() !== originalDay) {
             d.setDate(0); 
        }
        return d;
    }
    
    function getLastDayOfMonth(year, month) {
        return new Date(year, month + 1, 0).getDate();
    }

    function calcularCicloFinalDiaLogica(cicloBaseCode, hoyParam, ciclosDispList, cicloFinalDiaManual) {
        if (!hoyParam || !(hoyParam instanceof Date) || isNaN(hoyParam.getTime())) {
            console.warn("Invalid hoyParam in calcularCicloFinalDiaLogica", hoyParam); return null;
        }
        if (cicloBaseCode === "CICLO_00") { return cicloFinalDiaManual ? parseInt(cicloFinalDiaManual) : null; }
        else if (cicloBaseCode === "CICLO_25") { return 23; }
        else if (cicloBaseCode === "CICLO_99") {
            if (!ciclosDispList || ciclosDispList.length === 0) { console.warn("CICLO_99: No hay ciclosDispList"); return null; } 
            const sortedCiclos = [...ciclosDispList].sort((a, b) => a - b);
            const diaHoy = hoyParam.getDate();
            for (const diaCiclo of sortedCiclos) { if (diaCiclo >= diaHoy) return diaCiclo; }
            return sortedCiclos.length > 0 ? sortedCiclos[0] : null; 
        }
        return null;
    }

    function calcularFechaCierre(hoyParam, cicloFinalDiaParam) {
        if (!hoyParam || !(hoyParam instanceof Date) || isNaN(hoyParam.getTime()) || cicloFinalDiaParam === null || isNaN(parseInt(cicloFinalDiaParam))) {
            console.warn("Invalid params in calcularFechaCierre", hoyParam, cicloFinalDiaParam); return null;
        }
        let year = hoyParam.getFullYear(); let month = hoyParam.getMonth();
        let diaCicloValidoActual = Math.min(cicloFinalDiaParam, getLastDayOfMonth(year, month));
        let fechaCicloMesActual = new Date(year, month, diaCicloValidoActual);
        if (hoyParam.getTime() > fechaCicloMesActual.getTime()) {
            let fechaSiguienteMes = addMonths(new Date(year, month, 1), 1);
            let diaCicloValidoSiguiente = Math.min(cicloFinalDiaParam, getLastDayOfMonth(fechaSiguienteMes.getFullYear(), fechaSiguienteMes.getMonth()));
            return new Date(fechaSiguienteMes.getFullYear(), fechaSiguienteMes.getMonth(), diaCicloValidoSiguiente);
        } else { return fechaCicloMesActual; }
    }

    function calcularProrrateoTotal(hoyParam, fechaCierreParam, prorrateoDiaDecimal) {
        if (!hoyParam || !(hoyParam instanceof Date) || isNaN(hoyParam.getTime()) ||
            !fechaCierreParam || !(fechaCierreParam instanceof Date) || isNaN(fechaCierreParam.getTime()) ||
            prorrateoDiaDecimal === null || isNaN(parseFloat(prorrateoDiaDecimal))) {
            console.warn("Invalid params in calcularProrrateoTotal", hoyParam, fechaCierreParam, prorrateoDiaDecimal); return null;
        }
        if (fechaCierreParam.getTime() < hoyParam.getTime()) { console.warn("Fecha de cierre es anterior a hoy en calcularProrrateoTotal"); return 0.00; }
        const hoyClone = new Date(hoyParam.getFullYear(), hoyParam.getMonth(), hoyParam.getDate());
        const cierreClone = new Date(fechaCierreParam.getFullYear(), fechaCierreParam.getMonth(), fechaCierreParam.getDate());
        const diffTime = cierreClone.getTime() - hoyClone.getTime();
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
        const diasAProrratear = diffDays + 1; 
        const total = Math.max(0, diasAProrratear) * prorrateoDiaDecimal;
        return parseFloat(total.toFixed(2)); 
    }

    function calcularFechaActivacion(fechaCierreParam) {
        if (!fechaCierreParam || !(fechaCierreParam instanceof Date) || isNaN(fechaCierreParam.getTime())) return null;
        const fa = new Date(fechaCierreParam); fa.setDate(fa.getDate() + 1); return fa;
    }

    function calcularFechaPago(fechaActivacionParam, cicloFinalDiaParam) {
        if (!fechaActivacionParam || !(fechaActivacionParam instanceof Date) || isNaN(fechaActivacionParam.getTime()) ||
            cicloFinalDiaParam === null || isNaN(parseInt(cicloFinalDiaParam))) { return null; }
        let diasASumar = 16; 
        if (cicloFinalDiaParam <= 15) diasASumar = 15;
        else if (cicloFinalDiaParam === 17) diasASumar = 17;
        const fp = new Date(fechaActivacionParam); fp.setDate(fp.getDate() + diasASumar); return fp;
    }

    // --- FUNCIÓN PRINCIPAL DE ACTUALIZACIÓN DE CÁLCULOS ---
    function updateCalculations() {
        console.log('ingreso_ciclos.js: updateCalculations() iniciada.'); 

        const cicloBase = cicloBaseSelect ? cicloBaseSelect.value : null; 
        const cicloManualVal = cicloFinalManualSelect ? cicloFinalManualSelect.value : null; 
        const planOption = planSelect ? planSelect.options[planSelect.selectedIndex] : null; 
        const prorrateoDiaBaseStr = planOption ? planOption.dataset.prorrateoDia : null;
        const hoyDateObj = fechaHoyInput ? parseDateString(fechaHoyInput.value) : null; 

        console.log('ingreso_ciclos.js: Valores leídos:', {cicloBase, cicloManualVal, prorrateoDiaBaseStr, hoyDateObj: hoyDateObj ? hoyDateObj.toISOString().split('T')[0] : 'null o inválida' }); 

        if (!cicloBase || !prorrateoDiaBaseStr || !hoyDateObj || (cicloBase === "CICLO_00" && !cicloManualVal)) {
            console.log('ingreso_ciclos.js: Datos básicos incompletos, limpiando campos de display.'); 
            if(displayCicloFinalDia) displayCicloFinalDia.value = 'N/A';
            if(displayProrrateoDia) displayProrrateoDia.value = 'N/A';
            if(displayFechaCierre) displayFechaCierre.value = 'N/A';
            if(displayProrrateoTotal) displayProrrateoTotal.value = 'N/A';
            if(displayFechaActivacion) displayFechaActivacion.value = 'N/A';
            if(displayFechaPago) displayFechaPago.value = 'N/A';
            return;
        }
        
        const prorrateoDia = parseFloat(prorrateoDiaBaseStr);
        // Prorrateo por Día (Plan) - solo si hay datos válidos, en 2 decimales
        if (!isNaN(prorrateoDia) && prorrateoDia !== null && prorrateoDia !== undefined) {
            displayProrrateoDia.value = `S/. ${prorrateoDia.toFixed(2)}`;
        } else {
            displayProrrateoDia.value = 'N/A';
        }

        // Día de Ciclo Final Aplicado - siempre mostrar si hay datos válidos
        const cicloFinalDiaManualParsed = cicloManualVal ? parseInt(cicloManualVal) : null;
        const cicloFinalDiaCalculado = calcularCicloFinalDiaLogica(cicloBase, hoyDateObj, ciclosDisponibles, cicloFinalDiaManualParsed);
        if (displayCicloFinalDia) {
            if (cicloFinalDiaCalculado !== null && !isNaN(cicloFinalDiaCalculado)) {
                displayCicloFinalDia.value = String(cicloFinalDiaCalculado).padStart(2, '0');
            } else {
                displayCicloFinalDia.value = 'N/A';
            }
        }
        console.log('ingreso_ciclos.js: cicloFinalDiaCalculado:', cicloFinalDiaCalculado); 
        
        if (cicloFinalDiaCalculado === null || isNaN(cicloFinalDiaCalculado)) {
            console.log('ingreso_ciclos.js: cicloFinalDiaCalculado es null o NaN, limpiando campos dependientes.'); 
            if(displayFechaCierre) displayFechaCierre.value = 'N/A';
            if(displayProrrateoTotal) displayProrrateoTotal.value = 'N/A';
            if(displayFechaActivacion) displayFechaActivacion.value = 'N/A';
            if(displayFechaPago) displayFechaPago.value = 'N/A';
            return;
        }

        // Realizar cálculos y mostrar resultados solo si cicloFinalDiaCalculado es válido
        const fechaCierre = calcularFechaCierre(hoyDateObj, cicloFinalDiaCalculado);
        if(displayFechaCierre) displayFechaCierre.value = (fechaCierre && !isNaN(fechaCierre.getTime())) ? formatDateToDisplay(fechaCierre) : 'N/A';
        console.log('ingreso_ciclos.js: fechaCierre:', fechaCierre ? formatDateToDisplay(fechaCierre) : 'N/A'); 

        const prorrateoTotal = calcularProrrateoTotal(hoyDateObj, fechaCierre, prorrateoDia);
        if(displayProrrateoTotal) displayProrrateoTotal.value = (prorrateoTotal !== null && !isNaN(prorrateoTotal)) ? `S/. ${prorrateoTotal.toFixed(2)}` : 'N/A';
        
        const fechaActivacion = calcularFechaActivacion(fechaCierre);
        if(displayFechaActivacion) displayFechaActivacion.value = (fechaActivacion && !isNaN(fechaActivacion.getTime())) ? formatDateToDisplay(fechaActivacion) : 'N/A';

        const fechaPago = calcularFechaPago(fechaActivacion, cicloFinalDiaCalculado);
        if(displayFechaPago) displayFechaPago.value = (fechaPago && !isNaN(fechaPago.getTime())) ? formatDateToDisplay(fechaPago) : 'N/A';
        console.log('ingreso_ciclos.js: Cálculos finales mostrados.'); 
    }

    // --- MANEJADORES DE EVENTOS ---
    if (cicloBaseSelect) {
        cicloBaseSelect.addEventListener('change', function() {
            console.log('ingreso_ciclos.js: Evento change en cicloBaseSelect, valor:', this.value); 
            const selectedValue = this.value;
            if (selectedValue === "CICLO_00") {
                if(cicloFinalManualDiv) cicloFinalManualDiv.style.display = 'block';
                if(cicloFinalManualSelect) cicloFinalManualSelect.required = true;
                if(supervisorMsgEl) supervisorMsgEl.textContent = 'Consultar con el supervisor.';
            } else {
                if(cicloFinalManualDiv) cicloFinalManualDiv.style.display = 'none';
                if(cicloFinalManualSelect) {
                    cicloFinalManualSelect.required = false;
                    cicloFinalManualSelect.value = ''; 
                }
                if(supervisorMsgEl) supervisorMsgEl.textContent = '';
            }
            updateCalculations(); 
        });
    } else { console.warn("ingreso_ciclos.js: Elemento cicloBaseSelect no encontrado."); } 

    // --- ASIGNACIÓN DE LISTENERS (Sin cambios) ---
    if (fechaHoyInput) { fechaHoyInput.addEventListener('change', updateCalculations); } else { console.warn("ingreso_ciclos.js: Elemento fechaHoyInput no encontrado."); } 
    if (planSelect) { planSelect.addEventListener('change', updateCalculations); } else { console.warn("ingreso_ciclos.js: Elemento planSelect no encontrado."); } 
    if (cicloFinalManualSelect) { cicloFinalManualSelect.addEventListener('change', updateCalculations); } else { console.warn("ingreso_ciclos.js: Elemento cicloFinalManualSelect no encontrado al asignar listener."); } 

    // --- INICIALIZACIÓN ---
    if (fechaHoyInput && !fechaHoyInput.value) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0'); 
        const day = String(today.getDate()).padStart(2, '0');
        fechaHoyInput.value = `${year}-${month}-${day}`;
        console.log('ingreso_ciclos.js: Fecha de hoy establecida por defecto:', fechaHoyInput.value); 
    }
    
    if (cicloBaseSelect) { 
         console.log('ingreso_ciclos.js: Disparando evento change inicial en cicloBaseSelect.'); 
         cicloBaseSelect.dispatchEvent(new Event('change'));
    } else {
        console.log('ingreso_ciclos.js: cicloBaseSelect no encontrado para disparo inicial, llamando a updateCalculations directamente.'); 
        updateCalculations();
    }
});
