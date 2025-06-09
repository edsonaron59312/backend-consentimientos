from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models.prorrateo_models import ContratoProrrateo, Plan
from extensions import db
from sqlalchemy.orm import joinedload

api_contratos_bp = Blueprint('api_contratos', __name__)

@api_contratos_bp.route('/api/contratos', methods=['POST'])
@login_required
def api_contratos():
    draw = int(request.form.get('draw', 1))
    start = int(request.form.get('start', 0))
    length = int(request.form.get('length', 25))
    search_value = request.form.get('search[value]', '').strip()

    query = ContratoProrrateo.query.options(joinedload(ContratoProrrateo.plan), joinedload(ContratoProrrateo.user))

    if search_value:
        like = f"%{search_value}%"
        query = query.filter(
            (ContratoProrrateo.nombre_cliente.ilike(like)) |
            (ContratoProrrateo.tipo_documento.ilike(like)) |
            (ContratoProrrateo.numero_documento.ilike(like)) |
            (ContratoProrrateo.celular.ilike(like)) |
            (ContratoProrrateo.lugar_nacimiento_cliente.ilike(like)) |
            (ContratoProrrateo.correo_cliente.ilike(like))
        )

    total_records = ContratoProrrateo.query.count()
    filtered_records = query.count()
    contratos = query.order_by(ContratoProrrateo.fecha_registro_sistema.desc()).offset(start).limit(length).all()

    data = []
    for c in contratos:
        data.append({
            'id': c.id,
            'nombre_cliente': c.nombre_cliente,
            'tipo_documento': c.tipo_documento,
            'numero_documento': c.numero_documento,
            'celular': c.celular or '',
            'lugar_nacimiento_cliente': c.lugar_nacimiento_cliente or '',
            'fecha_nacimiento_cliente': c.fecha_nacimiento_cliente.strftime('%d/%m/%Y') if c.fecha_nacimiento_cliente else '',
            'correo_cliente': c.correo_cliente or '',
            'plan_nombre': c.plan.nombre if c.plan else '',
            'plan_precio': f"S/. {float(c.plan.precio):.2f}" if c.plan and c.plan.precio else '',
            'ciclo_final_dia': c.ciclo_final_dia,
            'prorrateo_dia_aplicado': f"S/. {float(c.prorrateo_dia_aplicado or 0):.2f}",
            'fecha_cierre_calculada': c.fecha_cierre_calculada.strftime('%d/%m/%Y') if c.fecha_cierre_calculada else '',
            'prorrateo_total_calculado': f"S/. {float(c.prorrateo_total_calculado or 0):.2f}",
            'fecha_activacion_calculada': c.fecha_activacion_calculada.strftime('%d/%m/%Y') if c.fecha_activacion_calculada else '',
            'fecha_pago_calculada': c.fecha_pago_calculada.strftime('%d/%m/%Y') if c.fecha_pago_calculada else '',
            'fecha_formulario_hoy': c.fecha_formulario_hoy.strftime('%d/%m/%Y') if c.fecha_formulario_hoy else '',
            'fecha_registro_sistema': c.fecha_registro_sistema.strftime('%d/%m/%Y %H:%M') if c.fecha_registro_sistema else '',
            'registrado_por': c.user.nombre_auditor if c.user else 'Sistema/Desconocido',
            'acciones': f'<button class="btn btn-danger btn-sm btn-eliminar" data-id="{c.id}">Eliminar</button>' if current_user.rol == 'admin' else ''
        })

    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })

@api_contratos_bp.route('/api/contratos/<int:contrato_id>/delete', methods=['DELETE'])
@login_required
def eliminar_contrato(contrato_id):
    if current_user.rol != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    contrato = ContratoProrrateo.query.get_or_404(contrato_id)
    db.session.delete(contrato)
    db.session.commit()
    return jsonify({'success': True})
