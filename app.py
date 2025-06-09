# /backend-consentimientos/app.py

# --- IMPORTACIONES ESENCIALES Y DE TERCEROS ---
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date 
import json
import decimal

# --- IMPORTA DESDE TU ARCHIVO extensions.py ---
from extensions import db, login_manager

# --- CONFIGURACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__) # Por defecto, static_folder='static', static_url_path='/static'
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"])
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://evelasqueza:Sales2025$@172.23.8.7:1433/BDD_PROCESOS_DESARROLLO?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave_secreta_muy_fuerte_y_unica_para_produccion_v4_ciclos'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False # True para producción con HTTPS

# --- INICIALIZACIÓN DE EXTENSIONES FLASK CON LA APP ---
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login_page' 
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"

migrate = Migrate(app, db)

# --- MODELOS DE BASE DE DATOS ---
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    nombre_auditor = db.Column(db.String(100), nullable=False)
    dni_auditor = db.Column(db.String(20), unique=True, nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='auditor')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime, nullable=True)
    activo = db.Column(db.Boolean, default=True)

    def set_password(self, contrasena):
        self.contrasena_hash = generate_password_hash(contrasena)

    def check_password(self, contrasena):
        return check_password_hash(self.contrasena_hash, contrasena)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_auditor": self.nombre_auditor,
            "nombre_completo": self.nombre_auditor,
            "dni_auditor": self.dni_auditor,
            "correo": self.correo,
            "rol": self.rol,
            "fecha_registro": self.fecha_registro.isoformat() if self.fecha_registro else None,
            "ultimo_login": self.ultimo_login.isoformat() if self.ultimo_login else None,
            "activo": self.activo
        }

class LogAuditoria(db.Model):
    __tablename__ = 'log_auditoria'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_nombre = db.Column(db.String(100), nullable=True)
    accion = db.Column(db.String(255), nullable=False)
    detalle = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    direccion_ip = db.Column(db.String(45), nullable=True)
    user = db.relationship('User', backref=db.backref('logs_auditoria', lazy='dynamic'))

    def to_dict(self):
        # ... (igual que antes)
        return {
            'id': self.id, 'user_id': self.user_id, 'user_nombre': self.user_nombre,
            'accion': self.accion, 'detalle': self.detalle,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'direccion_ip': self.direccion_ip
        }

from models.prorrateo_models import CicloDisponible, Plan, ContratoProrrateo
from routes.api_contratos import api_contratos_bp

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'admin':
            flash("Acceso no autorizado. Se requiere rol de administrador.", "danger")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required_api(f):
    # ... (igual que antes)
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(success=False, message="Autenticación requerida."), 401
        if current_user.rol != 'admin':
            return jsonify(success=False, message="Acceso no autorizado. Se requiere rol de administrador."), 403
        return f(*args, **kwargs)
    return decorated_function

def registrar_log(accion, detalle=None, user_obj=None):
    # ... (igual que antes, considera añadir app.app_context() si da errores fuera de request)
    try:
        ip_addr = request.remote_addr if request else None
        usuario_actual_obj = user_obj if user_obj else (current_user if current_user.is_authenticated else None)
        nombre_usuario_log = usuario_actual_obj.nombre_auditor if usuario_actual_obj else "Sistema"
        id_usuario_log = usuario_actual_obj.id if usuario_actual_obj else None
        detalle_json = json.dumps(detalle, ensure_ascii=False, default=str) if detalle is not None else None
        log_entry = LogAuditoria(user_id=id_usuario_log, user_nombre=nombre_usuario_log, accion=accion, detalle=detalle_json, direccion_ip=ip_addr)
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"!!! Error Crítico al registrar log de auditoría: {e} !!!")
        db.session.rollback() # Es buena idea hacer rollback aquí

# --- IMPORTACIÓN Y REGISTRO DE BLUEPRINTS ---
from routes.ciclos_prorrateos_routes import ciclos_prorrateos_bp
# SUGERENCIA: Si 'ciclos_prorrateos_bp' sirve principalmente páginas HTML, considera un prefijo como '/formularios' en lugar de '/api'.
# Ejemplo: app.register_blueprint(ciclos_prorrateos_bp, url_prefix='/formularios/ciclos')
# El prefijo actual '/api/ciclos-prorrateos' funciona, pero es menos convencional para HTML.
app.register_blueprint(ciclos_prorrateos_bp, url_prefix='/api/ciclos-prorrateos') 

# --- RUTAS DE TU APLICACIÓN (LOGIN, DASHBOARD, ETC.) ---
@app.route('/')
def home_redirect():
    # ... (igual que antes)
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    # ... (igual que antes)
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        user = User.query.filter_by(correo=correo).first()
        if user and user.check_password(contrasena):
            if user.activo:
                remember_me = request.form.get('remember_me_html') == 'y' 
                login_user(user, remember=remember_me)
                user.ultimo_login = datetime.utcnow()
                db.session.commit()
                registrar_log("INICIO_SESION_EXITOSO_HTML", {"usuario": user.correo})
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'warning')
                registrar_log("INICIO_SESION_FALLIDO_HTML", {"usuario": correo, "motivo": "Cuenta desactivada"})
        else:
            flash('Credenciales incorrectas. Por favor, inténtalo de nuevo.', 'danger')
            registrar_log("INICIO_SESION_FALLIDO_HTML", {"usuario": correo, "motivo": "Credenciales incorrectas"})
        return redirect(url_for('login_page'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    # ... (igual que antes)
    if current_user.is_authenticated:
         return jsonify(success=True, message="Ya estás logueado.", user=current_user.to_dict())
    data = request.get_json()
    if not data: return jsonify(success=False, message="No se recibieron datos JSON."), 400
    correo = data.get('correo')
    contrasena = data.get('contrasena')
    if not correo or not contrasena: return jsonify(success=False, message="Correo y contraseña son requeridos."), 400
    user = User.query.filter_by(correo=correo).first()
    if user and user.check_password(contrasena):
        if user.activo:
            login_user(user, remember=data.get('remember_me', False))
            user.ultimo_login = datetime.utcnow()
            db.session.commit()
            registrar_log("API_INICIO_SESION_EXITOSO", {"usuario": user.correo})
            return jsonify(success=True, message="Login exitoso", user=user.to_dict())
        else:
            registrar_log("API_INICIO_SESION_FALLIDO", {"usuario": correo, "motivo": "Cuenta desactivada"})
            return jsonify(success=False, message='Tu cuenta está desactivada. Contacta al administrador.'), 403
    else:
        registrar_log("API_INICIO_SESION_FALLIDO", {"usuario": correo, "motivo": "Credenciales incorrectas"})
        return jsonify(success=False, message='Credenciales incorrectas.'), 401

@app.route('/logout')
@login_required
def logout_page():
    # ... (igual que antes)
    if current_user.is_authenticated: # Esta verificación es redundante por @login_required pero no daña
        registrar_log("CIERRE_SESION_HTML", {"usuario_id": current_user.id, "usuario_correo": current_user.correo})
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login_page'))

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    # ... (igual que antes)
    if current_user.is_authenticated:
        registrar_log("API_CIERRE_SESION", {"usuario_id": current_user.id, "usuario_correo": current_user.correo})
    logout_user()
    return jsonify(success=True, message="Cierre de sesión exitoso.")

@app.route('/api/check_session', methods=['GET'])
def check_session():
    # ... (igual que antes)
    if current_user.is_authenticated:
        return jsonify(success=True, user=current_user.to_dict())
    else:
        return jsonify(success=False, message="No hay sesión activa."), 401

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    # ... (igual que antes)
    if current_user.is_authenticated:
        flash("Ya tienes una sesión activa.", "info")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nombre_auditor = request.form.get('nombre_auditor')
        dni_auditor = request.form.get('dni_auditor')
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')
        rol = request.form.get('rol', 'auditor')
        if not all([nombre_auditor, dni_auditor, correo, contrasena, confirmar_contrasena]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('register.html', form_data=request.form)
        if contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html', form_data=request.form)
        existing_user_email = User.query.filter_by(correo=correo).first()
        if existing_user_email:
            flash('El correo electrónico ya está registrado.', 'warning')
            return render_template('register.html', form_data=request.form)
        existing_user_dni = User.query.filter_by(dni_auditor=dni_auditor).first()
        if existing_user_dni:
            flash('El DNI del auditor ya está registrado.', 'warning')
            return render_template('register.html', form_data=request.form)
        new_user = User(nombre_auditor=nombre_auditor, dni_auditor=dni_auditor, correo=correo, rol=rol)
        new_user.set_password(contrasena)
        try:
            db.session.add(new_user)
            db.session.commit()
            registrado_por_info = "Sistema (auto-registro)"
            registrar_log("REGISTRO_USUARIO_NUEVO", {"nuevo_usuario_correo": new_user.correo, "registrado_por": registrado_por_info})
            flash('Usuario registrado exitosamente. Ahora puede iniciar sesión.', 'success')
            return redirect(url_for('login_page'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
            registrar_log("REGISTRO_USUARIO_FALLIDO", {"error": str(e), "datos_entrada": {"correo": correo, "dni": dni_auditor}})
            return render_template('register.html', form_data=request.form)
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # ... (igual que antes)
    try:
        return render_template('dashboard.html', current_user=current_user)
    except Exception as e:
        flash(f"Error al cargar el dashboard: {str(e)}", "danger")
        return redirect(url_for('login_page'))

@app.route('/manage_users')
@login_required
@admin_required
def manage_users_page():
    # ... (igual que antes)
    users = User.query.order_by(User.nombre_auditor).all()
    return render_template('manage_users.html', users=users, current_user=current_user)

@app.route('/api/users', methods=['GET'])
@login_required
@admin_required_api
def api_get_users():
    # ... (igual que antes)
    try:
        users = User.query.order_by(User.nombre_auditor).all()
        return jsonify(success=True, users=[user.to_dict() for user in users])
    except Exception as e:
        registrar_log("ERROR_API_GET_USERS", {"error": str(e)})
        return jsonify(success=False, message=f"Error al obtener usuarios: {str(e)}"), 500

@app.route('/api/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required_api
def api_toggle_user_active(user_id):
    # ... (igual que antes)
    user_to_toggle = db.session.get(User, user_id)
    if not user_to_toggle: return jsonify(success=False, message="Usuario no encontrado."), 404
    if user_to_toggle.id == current_user.id: return jsonify(success=False, message="No puedes cambiar tu propio estado de activación."), 403
    user_to_toggle.activo = not user_to_toggle.activo
    action = "USUARIO_ACTIVADO" if user_to_toggle.activo else "USUARIO_DESACTIVADO"
    try:
        db.session.commit()
        registrar_log(action, {"usuario_afectado_id": user_to_toggle.id, "usuario_afectado_correo": user_to_toggle.correo, "admin_id": current_user.id})
        return jsonify(success=True, message=f"Usuario {('activado' if user_to_toggle.activo else 'desactivado')} correctamente.", new_status=user_to_toggle.activo)
    except Exception as e:
        db.session.rollback()
        registrar_log(f"{action}_FALLIDO", {"error": str(e), "usuario_afectado_id": user_to_toggle.id})
        return jsonify(success=False, message=f"Error al cambiar estado del usuario: {str(e)}"), 500

@app.route('/api/users/<int:user_id>/change_role', methods=['POST'])
@login_required
@admin_required_api
def api_change_user_role(user_id):
    # ... (igual que antes)
    user_to_change = db.session.get(User, user_id)
    if not user_to_change: return jsonify(success=False, message="Usuario no encontrado."), 404
    data = request.get_json()
    new_role = data.get('new_role')
    if not new_role or new_role not in ['admin', 'auditor']: return jsonify(success=False, message="Rol inválido. Roles permitidos: 'admin', 'auditor'."), 400
    if user_to_change.id == current_user.id and new_role != 'admin': return jsonify(success=False, message="No puedes quitarte tu propio rol de administrador."), 403
    old_role = user_to_change.rol
    user_to_change.rol = new_role
    try:
        db.session.commit()
        registrar_log("CAMBIO_ROL_USUARIO", {"usuario_afectado_id": user_to_change.id, "usuario_afectado_correo": user_to_change.correo, "rol_anterior": old_role, "rol_nuevo": new_role, "admin_id": current_user.id})
        return jsonify(success=True, message="Rol de usuario cambiado correctamente.", new_role=user_to_change.rol)
    except Exception as e:
        db.session.rollback()
        registrar_log("CAMBIO_ROL_USUARIO_FALLIDO", {"error": str(e), "usuario_afectado_id": user_to_change.id})
        return jsonify(success=False, message=f"Error al cambiar rol del usuario: {str(e)}"), 500

@app.route('/api/audit_logs')
@login_required
@admin_required_api
def api_get_audit_logs():
    # ... (igual que antes)
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        logs_query = LogAuditoria.query.order_by(LogAuditoria.timestamp.desc())
        paginated_logs = logs_query.paginate(page=page, per_page=per_page, error_out=False)
        logs_data = [log.to_dict() for log in paginated_logs.items]
        return jsonify(success=True, logs=logs_data, total_logs=paginated_logs.total, current_page=paginated_logs.page, total_pages=paginated_logs.pages, per_page=paginated_logs.per_page)
    except Exception as e:
        print(f"!!! [API /api/audit_logs] ERROR: {e} !!!")
        registrar_log("ERROR_API_AUDIT_LOGS", {"error": str(e)})
        return jsonify(success=False, message=f"Error al obtener logs de auditoría: {str(e)}"), 500

# --- EJECUCIÓN DE LA APLICACIÓN FLASK ---
app.register_blueprint(api_contratos_bp)

if __name__ == "__main__":
    # Considera usar variables de entorno para debug y port en producción
    app.run(debug=True, host='0.0.0.0', port=5000) # Ahora accesible desde la red local.