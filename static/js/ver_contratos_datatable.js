// DataTable AJAX para contratos con eliminación
$(document).ready(function() {
    var table = $('#tabla-contratos').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/api/contratos',
            type: 'POST',
            data: function(d) {
                // Puedes agregar filtros extra aquí si los necesitas
                return d;
            }
        },
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100],
        columns: [
            { data: 'id' },
            { data: 'nombre_cliente' },
            { data: 'tipo_documento' },
            { data: 'numero_documento' },
            { data: 'celular' },
            { data: 'lugar_nacimiento_cliente' },
            { data: 'fecha_nacimiento_cliente' },
            { data: 'correo_cliente' },
            { data: 'plan_nombre' },
            { data: 'plan_precio' },
            { data: 'ciclo_final_dia' },
            { data: 'prorrateo_dia_aplicado' },
            { data: 'fecha_cierre_calculada' },
            { data: 'prorrateo_total_calculado' },
            { data: 'fecha_activacion_calculada' },
            { data: 'fecha_pago_calculada' },
            { data: 'fecha_formulario_hoy' },
            { data: 'fecha_registro_sistema' },
            { data: 'registrado_por' },
            { data: 'acciones', orderable: false, searchable: false }
        ],
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json'
        }
    });

    // Eliminar registro
    $('#tabla-contratos').on('click', '.btn-eliminar', function() {
        var id = $(this).data('id');
        if (confirm('¿Seguro que deseas eliminar este contrato?')) {
            $.ajax({
                url: '/api/contratos/' + id + '/delete',
                type: 'DELETE',
                success: function(resp) {
                    table.ajax.reload(null, false);
                },
                error: function(xhr) {
                    alert('Error al eliminar el contrato.');
                }
            });
        }
    });
});
