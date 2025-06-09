# tu_proyecto/routes/ciclos_prorrateos_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import datetime, date
import decimal
import locale 
import re # Para validaciones con expresiones regulares

from extensions import db
from flask_login import current_user, login_required

from models.prorrateo_models import CicloDisponible, Plan, ContratoProrrateo, CicloRegla
from services.services_calculos import obtener_detalles_calculados

# Configurar locale para español (para nombre del mes)
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Spanish_Spain') # Windows
        except locale.Error:
             try:
                locale.setlocale(locale.LC_TIME, 'Spanish') # Windows
             except locale.Error:
                current_app.logger.warning("ADVERTENCIA DE LOCALE: No se pudo establecer el locale a español para los nombres de los meses. Se usarán los nombres por defecto.")

ciclos_prorrateos_bp = Blueprint('ciclos_prorrateos_html', __name__, template_folder='../templates')

@ciclos_prorrateos_bp.route('/ingreso-ciclos-html', methods=['GET'])
@login_required
def mostrar_formulario_ingreso_ciclos():
    try:
        # print("DEBUG PYTHON (GET /ingreso-ciclos-html): ----- INICIO -----")
        contrato_id_to_edit = request.args.get('contrato_id_to_edit', type=int)
        form_data_to_populate = {} 
        
        if contrato_id_to_edit:
            contrato_existente = db.session.get(ContratoProrrateo, contrato_id_to_edit)
            if contrato_existente:
                # print(f"DEBUG PYTHON - Editando contrato ID: {contrato_id_to_edit}")
                form_data_to_populate = {
                    'nombre_cliente': contrato_existente.nombre_cliente,
                    'tipo_documento': contrato_existente.tipo_documento,
                    'numero_documento': contrato_existente.numero_documento,
                    'celular': contrato_existente.celular,
                    'lugar_nacimiento_cliente': contrato_existente.lugar_nacimiento_cliente,
                    'fecha_nacimiento_cliente': contrato_existente.fecha_nacimiento_cliente.isoformat() if contrato_existente.fecha_nacimiento_cliente else '',
                    'correo_cliente': contrato_existente.correo_cliente,
                    'fecha_hoy': contrato_existente.fecha_formulario_hoy.isoformat() if contrato_existente.fecha_formulario_hoy else date.today().strftime('%Y-%m-%d'),
                    'ciclo_base_seleccionado': contrato_existente.ciclo_base_seleccionado,
                    'plan_id': str(contrato_existente.plan_id),
                    'ciclo_final_dia_manual': str(contrato_existente.ciclo_final_dia) if contrato_existente.ciclo_final_dia is not None else ''
                }
            else:
                flash(f"Contrato con ID {contrato_id_to_edit} no encontrado para editar.", "warning")
                contrato_id_to_edit = None 
        
        planes_from_db = Plan.query.order_by(Plan.nombre).all()
        # print(f"DEBUG PYTHON - Planes desde la BD (cantidad: {len(planes_from_db)})")
        # if not planes_from_db: print("DEBUG PYTHON - ADVERTENCIA: No se encontraron PLANES en la BD.")

        ciclos_dias_db_from_db = CicloDisponible.query.order_by(CicloDisponible.dia).all()
        # print(f"DEBUG PYTHON - Ciclos Días desde la BD (cantidad: {len(ciclos_dias_db_from_db)})")
        # if not ciclos_dias_db_from_db: print("DEBUG PYTHON - ADVERTENCIA: No se encontraron DÍAS DE CICLO en la BD.")
        
        ciclos_a_pasar_plantilla = [c.dia for c in ciclos_dias_db_from_db]
        # print(f"DEBUG PYTHON - Lista 'ciclos_disponibles' para plantilla: {ciclos_a_pasar_plantilla}")
        
        ciclo_base_opts_actual = ["CICLO_00", "CICLO_99", "CICLO_25"]
        # print(f"DEBUG PYTHON - Ciclo Base Opciones (estático actual): {ciclo_base_opts_actual}")
        
        today_date_str_default = date.today().strftime('%Y-%m-%d')
        # print(f"DEBUG PYTHON - Fecha Hoy para plantilla (default): {today_date_str_default}")
        # print("DEBUG PYTHON (GET /ingreso-ciclos-html): ----- FIN DATOS PARA PLANTILLA -----")

        return render_template('ingreso_ciclos.html',
                               planes=planes_from_db,
                               ciclos_disponibles=ciclos_a_pasar_plantilla,
                               ciclo_base_opciones=ciclo_base_opts_actual, 
                               today_date=today_date_str_default,
                               form_data_to_edit=form_data_to_populate,
                               contrato_id_being_edited=contrato_id_to_edit
                               ) 
    except Exception as e:
        current_app.logger.error(f"Error CRÍTICO al cargar el formulario: {str(e)}", exc_info=True)
        flash(f"Error muy grave al cargar el formulario. Consulte los logs.", "danger")
        return redirect(url_for('dashboard'))

@ciclos_prorrateos_bp.route('/ingreso-ciclos-html', methods=['POST'])
@login_required
def procesar_formulario_ingreso_ciclos():
    planes_data = Plan.query.order_by(Plan.nombre).all()
    ciclos_dias_data_db = CicloDisponible.query.order_by(CicloDisponible.dia).all()
    ciclos_disponibles_list = [c.dia for c in ciclos_dias_data_db]
    ciclo_base_opciones_list = ["CICLO_00", "CICLO_99", "CICLO_25"]
    fecha_hoy_repopulate = request.form.get('fecha_hoy', date.today().strftime('%Y-%m-%d'))
    
    contrato_id_a_actualizar_str = request.form.get('contrato_id_a_actualizar')
    form_data_for_template = request.form 

    try:
        # print(f"DEBUG PYTHON (POST /ingreso-ciclos-html): ----- INICIO (ID para actualizar: {contrato_id_a_actualizar_str}) -----")
        nombre_cliente = request.form.get('nombre_cliente','').strip()
        tipo_documento = request.form.get('tipo_documento')
        numero_documento = request.form.get('numero_documento','').strip()
        celular = request.form.get('celular','').strip()
        lugar_nacimiento_cliente = request.form.get('lugar_nacimiento_cliente','').strip()
        fecha_nacimiento_cliente_str = request.form.get('fecha_nacimiento_cliente')
        correo_cliente = request.form.get('correo_cliente','').strip()
        fecha_hoy_str = request.form.get('fecha_hoy')
        ciclo_base_sel = request.form.get('ciclo_base_seleccionado')
        plan_id_str = request.form.get('plan_id')
        ciclo_final_manual_str = request.form.get('ciclo_final_dia_manual')
        
        # print(f"DEBUG PYTHON POST - Datos recibidos: cliente='{nombre_cliente}', plan_id='{plan_id_str}', etc...")

        errors = []
        # --- VALIDACIONES REFORZADAS ---
        if not nombre_cliente: 
            errors.append("Nombre del Cliente es requerido.")
        elif not re.match(r"^[a-zA-ZñÑáéíóúÁÉÍÓÚ\s']+$", nombre_cliente): # Permite letras, espacios y apóstrofes
             errors.append("Nombre del Cliente solo debe contener letras, espacios o apóstrofes.")
        
        if not numero_documento:
            errors.append("Número de Documento es requerido.")
        elif not numero_documento.isdigit():
            errors.append("Número de Documento debe ser completamente numérico.")
        elif tipo_documento == 'DNI' and len(numero_documento) != 8:
            errors.append("El DNI debe tener exactamente 8 dígitos.")
        elif tipo_documento == 'RUC' and len(numero_documento) != 11:
            errors.append("El RUC debe tener exactamente 11 dígitos.")
        elif tipo_documento in ['CE', 'PASAPORTE'] and len(numero_documento) > 12:
            errors.append("El número de documento CE o PASAPORTE no debe exceder los 12 dígitos.")

        if not celular: 
            errors.append("Celular (Línea) es requerido.")
        elif not celular.isdigit() or len(celular) != 9:
            errors.append("Celular debe ser numérico y tener exactamente 9 dígitos.")

        if lugar_nacimiento_cliente and not re.match(r"^[a-zA-ZñÑáéíóúÁÉÍÓÚ\s.,'-]+$", lugar_nacimiento_cliente):
            errors.append("Lugar de Nacimiento solo debe contener letras, espacios y los siguientes caracteres: . , ' -")
        
        # Validaciones existentes
        if not fecha_hoy_str: errors.append("Fecha de Referencia es requerida.")
        if not ciclo_base_sel: errors.append("Lógica de Ciclo Base es requerida.")
        if not plan_id_str: errors.append("Plan es requerido.")
        if ciclo_base_sel == "CICLO_00" and not ciclo_final_manual_str:
            errors.append("Día de Ciclo Final (Manual) es requerido para CICLO_00.")
        if correo_cliente and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", correo_cliente):
            errors.append("Formato de Correo Electrónico (Cliente) inválido.")

        fecha_nacimiento_cliente_obj = None
        if fecha_nacimiento_cliente_str:
            try:
                fecha_nacimiento_cliente_obj = datetime.strptime(fecha_nacimiento_cliente_str, '%Y-%m-%d').date()
                if fecha_nacimiento_cliente_obj >= date.today():
                    errors.append("Fecha de Nacimiento no puede ser hoy o una fecha futura.")
            except ValueError:
                errors.append("Formato de Fecha de Nacimiento inválido. Use YYYY-MM-DD.")
        
        if errors:
            # Mostrar los errores SOLO en la misma vista, no persistir tras redirect
            return render_template('ingreso_ciclos.html', planes=planes_data, ciclos_disponibles=ciclos_disponibles_list,
                                   ciclo_base_opciones=ciclo_base_opciones_list, today_date=fecha_hoy_repopulate,
                                   form_data_to_edit=form_data_for_template, errors=errors)

        # --- Conversión de datos y lógica de negocio ---
        fecha_hoy_obj = datetime.strptime(fecha_hoy_str, '%Y-%m-%d').date()
        plan_id_int = int(plan_id_str)
        ciclo_final_manual_int = int(ciclo_final_manual_str) if ciclo_final_manual_str and ciclo_final_manual_str.isdigit() else None
        
        calculos, error_msg = obtener_detalles_calculados(
            fecha_hoy_obj, ciclo_base_sel, plan_id_int, ciclo_final_manual_int
        )
        if error_msg or not calculos:
            flash(error_msg or "Error interno: no se pudieron obtener los detalles calculados.", "danger")
            return render_template('ingreso_ciclos.html', planes=planes_data, ciclos_disponibles=ciclos_disponibles_list,
                                   ciclo_base_opciones=ciclo_base_opciones_list, today_date=fecha_hoy_repopulate, form_data_to_edit=form_data_for_template, contrato_id_being_edited=contrato_id_a_actualizar_str)
        
        # --- Lógica de Guardar o Actualizar Contrato ---
        contrato_final = None
        if contrato_id_a_actualizar_str and contrato_id_a_actualizar_str.isdigit():
            # print(f"DEBUG PYTHON POST - Intentando actualizar contrato ID: {contrato_id_a_actualizar_str}")
            contrato_a_actualizar = db.session.get(ContratoProrrateo, int(contrato_id_a_actualizar_str))
            if contrato_a_actualizar:
                contrato_a_actualizar.nombre_cliente = nombre_cliente
                contrato_a_actualizar.tipo_documento = tipo_documento
                contrato_a_actualizar.numero_documento = numero_documento
                contrato_a_actualizar.celular = celular
                contrato_a_actualizar.lugar_nacimiento_cliente = lugar_nacimiento_cliente
                contrato_a_actualizar.fecha_nacimiento_cliente = fecha_nacimiento_cliente_obj
                contrato_a_actualizar.correo_cliente = correo_cliente
                contrato_a_actualizar.plan_id = plan_id_int
                contrato_a_actualizar.ciclo_base_seleccionado = ciclo_base_sel
                contrato_a_actualizar.ciclo_final_dia = calculos['ciclo_final_dia_calculado']
                contrato_a_actualizar.prorrateo_dia_aplicado = decimal.Decimal(calculos['prorrateo_dia_aplicado'])
                contrato_a_actualizar.fecha_cierre_calculada = date.fromisoformat(calculos['fecha_cierre'])
                contrato_a_actualizar.prorrateo_total_calculado = decimal.Decimal(calculos['prorrateo_total'])
                contrato_a_actualizar.fecha_activacion_calculada = date.fromisoformat(calculos['fecha_activacion'])
                contrato_a_actualizar.fecha_pago_calculada = date.fromisoformat(calculos['fecha_pago'])
                contrato_a_actualizar.fecha_formulario_hoy = fecha_hoy_obj
                flash_message = "Contrato actualizado exitosamente!"
                contrato_final = contrato_a_actualizar
                # print(f"DEBUG PYTHON POST - Contrato ID {contrato_final.id} actualizado.")
            else:
                flash(f"Error: No se encontró el contrato con ID {contrato_id_a_actualizar_str} para actualizar. Se creará uno nuevo.", "warning")
                contrato_id_a_actualizar_str = None 
        
        if not contrato_final: 
            # print("DEBUG PYTHON POST - Creando nuevo contrato.")
            nuevo_registro = ContratoProrrateo(
                nombre_cliente=nombre_cliente, tipo_documento=tipo_documento, numero_documento=numero_documento,
                celular=celular, lugar_nacimiento_cliente=lugar_nacimiento_cliente,
                fecha_nacimiento_cliente=fecha_nacimiento_cliente_obj, correo_cliente=correo_cliente,
                plan_id=plan_id_int, user_id=current_user.id, ciclo_base_seleccionado=ciclo_base_sel,
                ciclo_final_dia=calculos['ciclo_final_dia_calculado'],
                prorrateo_dia_aplicado=decimal.Decimal(calculos['prorrateo_dia_aplicado']),
                fecha_cierre_calculada=date.fromisoformat(calculos['fecha_cierre']),
                prorrateo_total_calculado=decimal.Decimal(calculos['prorrateo_total']),
                fecha_activacion_calculada=date.fromisoformat(calculos['fecha_activacion']),
                fecha_pago_calculada=date.fromisoformat(calculos['fecha_pago']),
                fecha_formulario_hoy=fecha_hoy_obj
            )
            db.session.add(nuevo_registro)
            flash_message = "Registro de ciclos y prorrateo guardado exitosamente!"
            contrato_final = nuevo_registro 
        
        db.session.commit()
        # print(f"DEBUG PYTHON POST - Operación completada. Redirigiendo a speech del contrato ID: {contrato_final.id}")
        flash(flash_message, "success")
        return redirect(url_for('.mostrar_contrato_speech_page', contrato_id=contrato_final.id))

    except ValueError as ve: 
        flash(f"Error en los datos de entrada: {str(ve)}. Por favor, verifica los valores.", "danger")
        current_app.logger.error(f"ValueError en procesar: {str(ve)}", exc_info=True) 
        db.session.rollback()
        return render_template('ingreso_ciclos.html', planes=planes_data, ciclos_disponibles=ciclos_disponibles_list,
                               ciclo_base_opciones=ciclo_base_opciones_list, today_date=fecha_hoy_repopulate, form_data_to_edit=form_data_for_template, contrato_id_being_edited=contrato_id_a_actualizar_str)
    except KeyError as ke: 
        flash(f"Error interno: falta un dato calculado '{str(ke)}'.", "danger")
        current_app.logger.error(f"KeyError en procesar (dict 'calculos'): {str(ke)}", exc_info=True) 
        db.session.rollback()
        return render_template('ingreso_ciclos.html', planes=planes_data, ciclos_disponibles=ciclos_disponibles_list,
                               ciclo_base_opciones=ciclo_base_opciones_list, today_date=fecha_hoy_repopulate, form_data_to_edit=form_data_for_template, contrato_id_being_edited=contrato_id_a_actualizar_str)
    except Exception as e: 
        db.session.rollback()
        current_app.logger.error(f"Error general al procesar formulario: {str(e)}", exc_info=True)
        flash(f"Error inesperado al procesar el formulario. Por favor, intente de nuevo.", "danger")
        return render_template('ingreso_ciclos.html', planes=planes_data, ciclos_disponibles=ciclos_disponibles_list,
                               ciclo_base_opciones=ciclo_base_opciones_list, today_date=fecha_hoy_repopulate, form_data_to_edit=form_data_for_template, contrato_id_being_edited=contrato_id_a_actualizar_str)

@ciclos_prorrateos_bp.route('/ver-contratos', methods=['GET'])
@login_required
def ver_contratos_page():
    try:
        # print("DEBUG PYTHON: ----- INICIO RUTA GET /ver-contratos -----")
        contratos = ContratoProrrateo.query.options(
            db.joinedload(ContratoProrrateo.plan),
            db.joinedload(ContratoProrrateo.user)
        ).order_by(ContratoProrrateo.fecha_registro_sistema.desc()).all()
        # print(f"DEBUG PYTHON - Contratos consultados para 'ver-contratos' (cantidad: {len(contratos)})")
        
        return render_template('ver_contratos.html', 
                               contratos=contratos, 
                               current_user=current_user)
    except Exception as e:
        current_app.logger.error(f"Error al cargar la página de ver contratos: {str(e)}", exc_info=True)
        flash("Error al cargar los contratos. Por favor, intente más tarde.", "danger")
        return redirect(url_for('dashboard'))

@ciclos_prorrateos_bp.route('/contrato-speech/<int:contrato_id>', methods=['GET'])
@login_required
def mostrar_contrato_speech_page(contrato_id):
    try:
        # print(f"DEBUG PYTHON: ----- INICIO RUTA GET /contrato-speech/{contrato_id} -----")
        contrato = db.session.get(ContratoProrrateo, contrato_id)
        
        if not contrato:
            flash("Contrato no encontrado.", "danger")
            # print(f"DEBUG PYTHON - Contrato con ID {contrato_id} no encontrado.")
            return redirect(url_for('.ver_contratos_page'))

        # print(f"DEBUG PYTHON - Contrato encontrado: ID={contrato.id}, Cliente='{contrato.nombre_cliente}'")
        
        dia_activacion = contrato.fecha_activacion_calculada.day if contrato.fecha_activacion_calculada else "X"
        dia_pago = contrato.fecha_pago_calculada.day if contrato.fecha_pago_calculada else "X"
        
        mes_pago_completo = ""
        if contrato.fecha_pago_calculada:
            try:
                mes_pago_completo = contrato.fecha_pago_calculada.strftime("%B")
            except ValueError:
                current_app.logger.warning(f"Locale no pudo formatear el mes para {contrato.fecha_pago_calculada}. Usando número de mes.")
                mes_pago_completo = str(contrato.fecha_pago_calculada.month)

        fecha_actual_speech = contrato.fecha_registro_sistema if contrato.fecha_registro_sistema else date.today()
        dia_actual_speech_num = fecha_actual_speech.day
        mes_actual_speech_str = ""
        try:
            mes_actual_speech_str = fecha_actual_speech.strftime("%B")
        except ValueError:
            current_app.logger.warning(f"Locale no pudo formatear el mes para {fecha_actual_speech}. Usando número de mes.")
            mes_actual_speech_str = str(fecha_actual_speech.month)

        anho_actual_speech = fecha_actual_speech.year
        
        # print(f"DEBUG PYTHON - Datos para speech: dia_activacion={dia_activacion}, dia_pago={dia_pago}, mes_pago_str='{mes_pago_completo.capitalize()}'")

        return render_template('contrato_speech.html', 
                               contrato=contrato,
                               dia_activacion=dia_activacion,
                               dia_pago=dia_pago,
                               mes_pago_str=mes_pago_completo.capitalize(),
                               dia_hoy_speech=f"{dia_actual_speech_num} de {mes_actual_speech_str.capitalize()}",
                               anho_hoy_speech=anho_actual_speech,
                               current_user=current_user)
    except Exception as e:
        current_app.logger.error(f"Error al cargar la vista del contrato speech (ID: {contrato_id}): {str(e)}", exc_info=True)
        flash("Error al generar la vista del contrato.", "danger")
        return redirect(url_for('.ver_contratos_page'))

# Endpoints API
@ciclos_prorrateos_bp.route('/config/ciclos-disponibles-json', methods=['GET'])
@login_required 
def get_ciclos_disponibles_json():
    ciclos = CicloDisponible.query.order_by(CicloDisponible.dia).all()
    return jsonify([c.dia for c in ciclos])

@ciclos_prorrateos_bp.route('/config/planes-json', methods=['GET'])
@login_required 
def get_planes_json():
    planes_obj = Plan.query.all()
    planes_list = [{'id': p.id, 'nombre': p.nombre, 'precio': float(p.precio), 
                    'prorrateo_dia_base': float(p.prorrateo_dia_base)} for p in planes_obj]
    return jsonify(planes_list)