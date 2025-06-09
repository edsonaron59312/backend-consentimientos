# /backend-consentimientos/services/services_calculos.py
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
# Importamos los modelos desde la nueva ubicación
from models.prorrateo_models import CicloDisponible, Plan
import decimal

ctx = decimal.Context()
ctx.prec = 10 # Precisión para cálculos decimales

def calcular_ciclo_final_dia_logica(ciclo_base_code, hoy_param, ciclos_disponibles_list, ciclo_final_dia_manual=None):
    if ciclo_base_code == "CICLO_00":
        return ciclo_final_dia_manual
    elif ciclo_base_code == "CICLO_25":
        return 23
    elif ciclo_base_code == "CICLO_99":
        if not ciclos_disponibles_list:
            return None
        sorted_ciclos = sorted(ciclos_disponibles_list)
        dia_hoy = hoy_param.day
        for dia_ciclo in sorted_ciclos:
            if dia_ciclo >= dia_hoy:
                return dia_ciclo
        return sorted_ciclos[0] if sorted_ciclos else None
    return None

def calcular_fecha_cierre(hoy_param, ciclo_final_dia_param):
    if not isinstance(hoy_param, date) or not isinstance(ciclo_final_dia_param, int):
        raise ValueError("Parámetros inválidos para calcular_fecha_cierre: hoy_param debe ser date, ciclo_final_dia_param debe ser int")
    
    try:
        fecha_ciclo_mes_actual = date(hoy_param.year, hoy_param.month, ciclo_final_dia_param)
    except ValueError: # Manejo si el día es inválido para el mes actual (ej. 31 Feb)
        last_day_of_month = (date(hoy_param.year, hoy_param.month, 1) + relativedelta(months=1) - timedelta(days=1)).day
        actual_day = min(ciclo_final_dia_param, last_day_of_month)
        fecha_ciclo_mes_actual = date(hoy_param.year, hoy_param.month, actual_day)

    if hoy_param > fecha_ciclo_mes_actual:
        fecha_cierre_temp = date(hoy_param.year, hoy_param.month, 1) + relativedelta(months=1)
        try:
            fecha_cierre = date(fecha_cierre_temp.year, fecha_cierre_temp.month, ciclo_final_dia_param)
        except ValueError: # Manejo si el día es inválido para el mes siguiente
            last_day_of_next_month = (date(fecha_cierre_temp.year, fecha_cierre_temp.month, 1) + relativedelta(months=1) - timedelta(days=1)).day
            actual_day_next_month = min(ciclo_final_dia_param, last_day_of_next_month)
            fecha_cierre = date(fecha_cierre_temp.year, fecha_cierre_temp.month, actual_day_next_month)
    else:
        fecha_cierre = fecha_ciclo_mes_actual
    return fecha_cierre

def calcular_prorrateo_total(hoy_param, fecha_cierre_param, prorrateo_dia_decimal):
    if not isinstance(hoy_param, date) or \
       not isinstance(fecha_cierre_param, date) or \
       not isinstance(prorrateo_dia_decimal, decimal.Decimal):
        raise ValueError("Parámetros inválidos para calcular_prorrateo_total")

    if fecha_cierre_param < hoy_param: # No debería ocurrir si la lógica es correcta
        return decimal.Decimal("0.00")
        
    dias_a_prorratear = (fecha_cierre_param - hoy_param).days + 1
    # Asegurarse que días a prorratear no sea negativo
    total = decimal.Decimal(max(0, dias_a_prorratear)) * prorrateo_dia_decimal
    return total.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)

def calcular_fecha_activacion(fecha_cierre_param):
    if not isinstance(fecha_cierre_param, date):
        raise ValueError("Parámetro inválido para calcular_fecha_activacion")
    return fecha_cierre_param + timedelta(days=1)

def calcular_fecha_pago(fecha_activacion_param, ciclo_final_dia_param):
    if not isinstance(fecha_activacion_param, date) or not isinstance(ciclo_final_dia_param, int):
        raise ValueError("Parámetros inválidos para calcular_fecha_pago")
        
    dias_a_sumar = 16 
    if ciclo_final_dia_param <= 15:
        dias_a_sumar = 15
    elif ciclo_final_dia_param == 17:
        dias_a_sumar = 17
    return fecha_activacion_param + timedelta(days=dias_a_sumar)

def obtener_detalles_calculados(fecha_hoy_obj, ciclo_base_code, plan_id, ciclo_final_dia_manual=None):
    plan_obj = Plan.query.get(plan_id) # SQLAlchemy buscará por PK
    if not plan_obj:
        return None, "Plan no encontrado"

    prorrateo_dia_aplicado = plan_obj.prorrateo_dia_base 

    ciclos_disponibles_db = CicloDisponible.query.order_by(CicloDisponible.dia).all()
    ciclos_disponibles_list = [c.dia for c in ciclos_disponibles_db]

    ciclo_final_dia = calcular_ciclo_final_dia_logica(
        ciclo_base_code, fecha_hoy_obj, ciclos_disponibles_list, ciclo_final_dia_manual
    )
    if ciclo_final_dia is None:
        return None, f"No se pudo determinar el ciclo final para {ciclo_base_code}"

    fecha_cierre = calcular_fecha_cierre(fecha_hoy_obj, ciclo_final_dia)
    prorrateo_total = calcular_prorrateo_total(fecha_hoy_obj, fecha_cierre, prorrateo_dia_aplicado)
    fecha_activacion = calcular_fecha_activacion(fecha_cierre)
    fecha_pago = calcular_fecha_pago(fecha_activacion, ciclo_final_dia)
    
    return {
        "fecha_hoy_usada": fecha_hoy_obj.isoformat(),
        "ciclo_final_dia_calculado": ciclo_final_dia,
        "prorrateo_dia_aplicado": str(prorrateo_dia_aplicado),
        "fecha_cierre": fecha_cierre.isoformat(),
        "prorrateo_total": str(prorrateo_total),
        "fecha_activacion": fecha_activacion.isoformat(),
        "fecha_pago": fecha_pago.isoformat(),
        "mensaje_supervisor": "Consultar con el supervisor." if ciclo_base_code == "CICLO_00" else None
    }, None