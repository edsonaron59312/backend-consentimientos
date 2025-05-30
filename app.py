import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify # Se quitaron flash, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import json # Importado para el logging
from datetime import datetime, date
import time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from apscheduler.schedulers.background import BackgroundScheduler
import calendar
from sqlalchemy import func, extract
import pyodbc
from functools import wraps
from flask_cors import CORS

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/crud_python'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_super_segura_cambiala_por_favor_2025_v3_api_final_logging_v2' # ¡CAMBIA ESTO!
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True 

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Google Sheets (Tu configuración...)
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET_ID = '19F6sTYpNKHKaw7M6j4mpl0fgdLNB0nCotOXhvC52Tyg'
SHEET_NAME = 'Hoja1'

# --- SQL Server Connection Details (Tu configuración...) ---
SQL_SERVER_IP = '172.23.8.7'
SQL_DATABASE_NAME = 'BD_PYC'
SQL_USERNAME = 'evelasqueza'
SQL_PASSWORD = 'Sales2025$'
SQL_DRIVER = '{SQL Server}'


# --- DATABASE MODELS ---
class AuditorMovistar(UserMixin, db.Model):
    __tablename__ = 'auditores_movistar'
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(80), nullable=False, default='auditor')
    nombre_completo = db.Column(db.String(150), nullable=False)
    dni_auditor = db.Column(db.String(15), unique=True, nullable=False)
    data_source = db.Column(db.String(10), nullable=False, default='sheet')
    logs = db.relationship('LogAuditoria', backref='auditor_realizo_accion', lazy=True, foreign_keys='LogAuditoria.usuario_id')

    def set_password(self, contrasena):
        self.contrasena_hash = generate_password_hash(contrasena, method='scrypt')

    def check_password(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)

    def to_dict(self): 
        return {
            'id': self.id, 'correo': self.correo, 'rol': self.rol,
            'nombre_completo': self.nombre_completo, 'dni_auditor': self.dni_auditor,
            'data_source': self.data_source
        }
    def __repr__(self): return f'<Auditor {self.correo}>'

class EscuchaMovistar(db.Model):
    __tablename__ = 'escuchas_movistar'
    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(20))
    dni_asesor = db.Column(db.String(15))
    asesor = db.Column(db.String(150))
    campana = db.Column(db.String(100))
    supervisor = db.Column(db.String(150))
    coordinador = db.Column(db.String(150))
    tipifica_bien = db.Column(db.String(10))
    cliente_desiste = db.Column(db.String(10))
    observaciones = db.Column(db.Text, nullable=True)
    dni_auditor = db.Column(db.String(15)) # DNI del auditor que registró la escucha
    nombre_auditor = db.Column(db.String(150)) # Nombre del auditor que registró la escucha
    fecha_registro = db.Column(db.TIMESTAMP, server_default=db.func.now())
    
    def to_dict(self):
        return {
            'id': self.id, 'telefono': self.telefono, 'dni_asesor': self.dni_asesor,
            'asesor': self.asesor, 'campana': self.campana, 'supervisor': self.supervisor,
            'coordinador': self.coordinador, 'tipifica_bien': self.tipifica_bien,
            'cliente_desiste': self.cliente_desiste, 'observaciones': self.observaciones,
            'dni_auditor': self.dni_auditor, 'nombre_auditor': self.nombre_auditor,
            'fecha_registro': self.fecha_registro.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_registro else None
        }

class LogAuditoria(db.Model):
    __tablename__ = 'logs_auditoria'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('auditores_movistar.id'), nullable=True)
    nombre_usuario = db.Column(db.String(150), nullable=True)
    correo_usuario = db.Column(db.String(120), nullable=True)
    rol_usuario = db.Column(db.String(80), nullable=True)
    accion = db.Column(db.String(255), nullable=False)
    entidad_afectada = db.Column(db.String(100), nullable=True)
    id_entidad_afectada = db.Column(db.String(50), nullable=True)
    detalles_anteriores = db.Column(db.Text, nullable=True)
    detalles_nuevos = db.Column(db.Text, nullable=True)
    direccion_ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)

    def __repr__(self): return f'<Log {self.id} - {self.accion} por {self.nombre_usuario} en {self.timestamp}>'
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'usuario_id': self.usuario_id, 'nombre_usuario': self.nombre_usuario,
            'correo_usuario': self.correo_usuario, 'rol_usuario': self.rol_usuario,
            'accion': self.accion, 'entidad_afectada': self.entidad_afectada,
            'id_entidad_afectada': self.id_entidad_afectada,
            'detalles_anteriores': json.loads(self.detalles_anteriores) if self.detalles_anteriores else None,
            'detalles_nuevos': json.loads(self.detalles_nuevos) if self.detalles_nuevos else None,
            'direccion_ip': self.direccion_ip, 'user_agent': self.user_agent
        }

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(AuditorMovistar, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify(success=False, message="Autenticación requerida para acceder a este recurso."), 401

# --- FUNCIÓN HELPER PARA LOGGING ---
def registrar_log_auditoria(accion, entidad_afectada=None, id_entidad_afectada=None, detalles_anteriores=None, detalles_nuevos=None, correo_intento_login=None):
    try:
        log_entry = LogAuditoria(
            accion=str(accion).upper(),
            entidad_afectada=str(entidad_afectada) if entidad_afectada else None,
            id_entidad_afectada=str(id_entidad_afectada) if id_entidad_afectada else None,
            detalles_anteriores=json.dumps(detalles_anteriores, ensure_ascii=False, default=str) if detalles_anteriores else None,
            detalles_nuevos=json.dumps(detalles_nuevos, ensure_ascii=False, default=str) if detalles_nuevos else None,
            direccion_ip=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        if current_user and current_user.is_authenticated:
            log_entry.usuario_id = current_user.id
            log_entry.nombre_usuario = current_user.nombre_completo
            log_entry.correo_usuario = current_user.correo
            log_entry.rol_usuario = current_user.rol
        elif correo_intento_login: 
             log_entry.correo_usuario = correo_intento_login

        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"!!! ERROR al registrar log de auditoría para la acción {accion}: {e} !!!")


# --- CACHE & HELPER FUNCTIONS ---
advisor_cache = {}
def load_advisor_cache(): 
    global advisor_cache
    try:
        start_time = time.time()
        sheet = CLIENT.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        all_values = sheet.get_all_values()
        new_cache = {}
        if len(all_values) > 1:
            for row_idx, row in enumerate(all_values[1:]):
                 data_len = len(row)
                 if data_len > 0 and row[0]:
                     dni = row[0].strip()
                     if not dni: continue
                     asesor = f"{row[1]} {row[2]}".strip() if data_len > 2 else "N/A"
                     supervisor = row[13] if data_len > 13 else "N/A"
                     coordinador = row[16] if data_len > 16 else "N/A"
                     campana = row[17] if data_len > 17 else "N/A"
                     new_cache[dni] = { 'asesor': asesor, 'supervisor': supervisor, 'coordinador': coordinador, 'campana': campana }
            advisor_cache = new_cache
            print(f"Caché de Google Sheet cargada. Asesores en caché: {len(advisor_cache)}.")
        else: print("No se encontraron datos en Google Sheets para la caché (o solo encabezado).")
    except Exception as e:
        print(f"ERROR FATAL: No se pudo cargar la caché de asesores (Google Sheet): {e}")
        advisor_cache = {}

def get_advisor_data_from_sheet(dni): return advisor_cache.get(dni)

def admin_required_api(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            return jsonify(success=False, message="Acceso denegado. Se requieren permisos de administrador."), 403
        return f(*args, **kwargs)
    return decorated_function

# --- FLASK API ROUTES ---
@app.route('/api/login', methods=['POST'])
def api_login():
    if current_user.is_authenticated:
        return jsonify(success=True, message="Ya estás autenticado.", user=current_user.to_dict())
    data = request.get_json()
    if not data: return jsonify(success=False, message="No se recibieron datos JSON."), 400
    correo = data.get('correo')
    contrasena = data.get('contrasena')
    if not correo or not contrasena: return jsonify(success=False, message="Correo y contraseña son requeridos."), 400
    
    auditor_user = AuditorMovistar.query.filter_by(correo=correo).first()
    if auditor_user and auditor_user.check_password(contrasena):
        login_user(auditor_user, remember=True)
        registrar_log_auditoria(accion="LOGIN_EXITOSO") 
        return jsonify(success=True, message='Inicio de sesión exitoso.', user=current_user.to_dict())
    else:
        registrar_log_auditoria(accion="LOGIN_FALLIDO", correo_intento_login=correo) 
        return jsonify(success=False, message='Correo o contraseña incorrectos.'), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    registrar_log_auditoria(accion="LOGOUT") 
    logout_user()
    return jsonify(success=True, message='Has cerrado sesión.')

@app.route('/api/check_session')
@login_required
def api_check_session(): return jsonify(success=True, user=current_user.to_dict())

@app.route('/api/records')
@login_required
def api_records(): 
    records_data = []
    try:
        query = EscuchaMovistar.query
        if current_user.rol == 'auditor': 
            query = query.filter_by(dni_auditor=str(current_user.dni_auditor))
        records = query.order_by(EscuchaMovistar.id.desc()).all()
        records_data = [r.to_dict() for r in records]
        return jsonify(success=True, records=records_data)
    except Exception as e:
        print(f"!!! [API /api/records] ERROR al obtener registros: {e} !!!")
        return jsonify(success=False, message=f"Error al cargar registros: {str(e)}"), 500

@app.route('/api/advisor/sheet/<dni>')
@login_required
def api_get_advisor_from_sheet_json(dni): 
    data = get_advisor_data_from_sheet(dni)
    if data: return jsonify(data)
    else: return jsonify({'error': 'DNI no encontrado en Google Sheet'}), 404

@app.route('/api/advisor/sql/<dni>')
@login_required
def api_get_sql_advisor_data_json(dni): 
    conn = None
    try:
        conn_str = ( f'DRIVER={SQL_DRIVER};SERVER={SQL_SERVER_IP};DATABASE={SQL_DATABASE_NAME};UID={SQL_USERNAME};PWD={SQL_PASSWORD};' )
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        query = "SELECT Nombres_Agente, Apellidos_Agente, Plataforma, Supervisor FROM TB_Maestra_General_Multicuentas WHERE DOC_agente = ?"
        cursor.execute(query, dni)
        row = cursor.fetchone()
        if row:
            asesor_nombre = row.Nombres_Agente if row.Nombres_Agente else ""
            asesor_apellido = row.Apellidos_Agente if row.Apellidos_Agente else ""
            data = { 'asesor': f"{asesor_nombre} {asesor_apellido}".strip(), 'campana': row.Plataforma if row.Plataforma else "N/A", 'supervisor': row.Supervisor if row.Supervisor else "N/A", 'coordinador': "Marjorie Landa Temoche" }
            return jsonify(data)
        else: return jsonify({'error': 'DNI no encontrado en la base de datos SQL'}), 404
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"!!! [API SQL DNI Search] Error de PyODBC ({sqlstate}): {ex} !!!")
        return jsonify({'error': f'Error de base de datos: {str(ex)}'}), 500
    except Exception as e:
        print(f"!!! [API SQL DNI Search] Error inesperado: {e} !!!")
        return jsonify({'error': f'Error inesperado del servidor: {str(e)}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/submit', methods=['POST'])
@login_required
def api_submit_form():
    try:
        data = request.get_json()
        if not data: return jsonify(success=False, message="No se recibieron datos JSON."), 400
        new_record = EscuchaMovistar(
            telefono=data.get('telefono'), dni_asesor=data.get('dni_asesor'),
            asesor=data.get('asesor'), campana=data.get('campana'),
            supervisor=data.get('supervisor'), coordinador=data.get('coordinador'),
            tipifica_bien=data.get('tipifica_bien'), cliente_desiste=data.get('cliente_desiste'),
            observaciones=data.get('observaciones'), dni_auditor=current_user.dni_auditor,
            nombre_auditor=current_user.nombre_completo )
        db.session.add(new_record)
        db.session.commit()
        registrar_log_auditoria(
            accion="CREACION_REGISTRO_ESCUCHA",
            entidad_afectada="EscuchaMovistar",
            id_entidad_afectada=new_record.id,
            detalles_nuevos=new_record.to_dict()
        )
        return jsonify({'success': True, 'message': 'Registro guardado.', 'record': new_record.to_dict()})
    except Exception as e:
        db.session.rollback()
        print(f"!!! [API /api/submit] Error saving to DB: {e} !!!")
        registrar_log_auditoria(accion="ERROR_CREACION_REGISTRO_ESCUCHA", detalles_nuevos={'error': str(e), 'data_enviada': data})
        return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'}), 500

@app.route('/api/dashboard_data')
@login_required
def api_dashboard_data(): 
    try:
        current_dt = datetime.now()
        year = int(request.args.get('year', current_dt.year))
        month = int(request.args.get('month', current_dt.month))
        _, num_days = calendar.monthrange(year, month)
        meses_espanol = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dias_semana_es_corto = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        month_name_str = meses_espanol[month] 
        days_in_month_data_list = [] 
        for d_num in range(1, num_days + 1):
            try:
                current_day_date = date(year, month, d_num)
                day_of_week_num = current_day_date.weekday()
                days_in_month_data_list.append({ 'day_num': d_num, 'day_name_short': dias_semana_es_corto[day_of_week_num], 'is_sunday': (day_of_week_num == 6) })
            except ValueError as ve:
                print(f"Error creando fecha para el día {d_num}/{month}/{year}: {ve}")
                continue
        start_date = datetime(year, month, 1)
        if month == 12: end_date = datetime(year + 1, 1, 1)
        else: end_date = datetime(year, month + 1, 1)
        
        dashboard_summary_data = {} 
        auditor_totals_data = {} 
        total_records_month_count = 0 
        
        auditors_query = AuditorMovistar.query
        if current_user.rol == 'auditor':
            auditors_query = auditors_query.filter_by(id=current_user.id)
        
        auditors_for_dashboard_list = auditors_query.order_by(AuditorMovistar.nombre_completo).all()

        for auditor_obj in auditors_for_dashboard_list:
            dashboard_summary_data[auditor_obj.nombre_completo] = {day_info['day_num']: 0 for day_info in days_in_month_data_list}
            auditor_totals_data[auditor_obj.nombre_completo] = 0

        base_query = EscuchaMovistar.query.filter(EscuchaMovistar.fecha_registro.between(start_date, end_date))
        if current_user.rol == 'auditor':
            base_query = base_query.filter(EscuchaMovistar.dni_auditor == current_user.dni_auditor)

        results = base_query.with_entities(
            EscuchaMovistar.nombre_auditor, 
            extract('day', EscuchaMovistar.fecha_registro).label('day'), 
            func.count(EscuchaMovistar.id).label('count')
        ).group_by(
            EscuchaMovistar.nombre_auditor, 
            extract('day', EscuchaMovistar.fecha_registro)
        ).all()
            
        for row in results:
            auditor_name = row.nombre_auditor
            day = int(row.day)
            count = int(row.count)
            if auditor_name in dashboard_summary_data:
                if day in dashboard_summary_data[auditor_name]: 
                    dashboard_summary_data[auditor_name][day] = count
                auditor_totals_data[auditor_name] += count
            if current_user.rol == 'admin' or (current_user.rol == 'auditor' and auditor_name == current_user.nombre_completo):
                 total_records_month_count += count
        return jsonify(
            success=True, dashboard_data=dashboard_summary_data, days_in_month_data=days_in_month_data_list,
            month_name=month_name_str, year_processed=year, month_processed=month, 
            auditor_totals=auditor_totals_data, total_records_month=total_records_month_count,
            num_auditors_processed=len(auditors_for_dashboard_list)
        )
    except Exception as e:
        print(f"!!! [API /api/dashboard_data] ERROR: {e} !!!")
        return jsonify(success=False, message=f"Ocurrió un error al cargar datos del dashboard: {str(e)}"), 500

@app.route('/api/users')
@login_required
@admin_required_api
def api_get_users(): 
    try:
        users = AuditorMovistar.query.order_by(AuditorMovistar.nombre_completo).all()
        users_data = [user.to_dict() for user in users]
        return jsonify(success=True, users=users_data)
    except Exception as e:
        print(f"!!! [API /api/users] ERROR: {e} !!!")
        return jsonify(success=False, message=f"Error al obtener usuarios: {str(e)}"), 500

@app.route('/api/users/<int:user_id>/change_role', methods=['POST'])
@login_required
@admin_required_api
def api_change_user_role(user_id):
    user_to_change = db.session.get(AuditorMovistar, user_id)
    data = request.get_json()
    if not data: return jsonify(success=False, message="No se recibieron datos JSON."), 400
    new_role = data.get('new_role')

    if not user_to_change: return jsonify(success=False, message='Usuario no encontrado.'), 404
    if new_role not in ['admin', 'auditor']: return jsonify(success=False, message='Rol no válido.'), 400

    admin_count = AuditorMovistar.query.filter_by(rol='admin').count()
    if (user_to_change.id == current_user.id and user_to_change.rol == 'admin' and new_role == 'auditor' and admin_count <= 1):
        return jsonify(success=False, message='No puedes quitarte el rol de administrador si eres el único.'), 403
    
    old_role_details = {'rol_anterior': user_to_change.rol} 
    try:
        user_to_change.rol = new_role
        db.session.commit()
        registrar_log_auditoria(
            accion="CAMBIO_ROL_USUARIO",
            entidad_afectada="AuditorMovistar",
            id_entidad_afectada=user_to_change.id,
            detalles_anteriores=old_role_details,
            detalles_nuevos={'rol_nuevo': new_role, 'correo_afectado': user_to_change.correo}
        )
        return jsonify(success=True, message=f'Rol de {user_to_change.nombre_completo} cambiado a {new_role}.', user=user_to_change.to_dict())
    except Exception as e:
        db.session.rollback()
        registrar_log_auditoria(accion="ERROR_CAMBIO_ROL_USUARIO", id_entidad_afectada=user_id, detalles_nuevos={'error': str(e), 'rol_intentado': new_role})
        return jsonify(success=False, message=f'Error al cambiar el rol: {str(e)}'), 500

# +++ NUEVA RUTA PARA OBTENER LOGS DE AUDITORÍA +++
@app.route('/api/audit_logs')
@login_required
@admin_required_api
def api_get_audit_logs():
    try:
        # Opcional: Añadir paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int) # 50 logs por página por defecto

        logs_query = LogAuditoria.query.order_by(LogAuditoria.timestamp.desc())
        
        # Aplicar paginación
        paginated_logs = logs_query.paginate(page=page, per_page=per_page, error_out=False)
        logs_data = [log.to_dict() for log in paginated_logs.items]
        
        return jsonify(
            success=True, 
            logs=logs_data,
            total_logs=paginated_logs.total,
            current_page=paginated_logs.page,
            total_pages=paginated_logs.pages,
            per_page=paginated_logs.per_page
        )
    except Exception as e:
        print(f"!!! [API /api/audit_logs] ERROR: {e} !!!")
        return jsonify(success=False, message=f"Error al obtener logs de auditoría: {str(e)}"), 500

# --- RUN FLASK APP ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        load_advisor_cache()

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=load_advisor_cache, trigger="interval", minutes=15)
    scheduler.start()

    import atexit
    atexit.register(lambda: scheduler.shutdown())

    app.run(host='0.0.0.0', port=5000, debug=True)
