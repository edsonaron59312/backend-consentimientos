# /backend-consentimientos/models/prorrateo_models.py
from extensions import db 
import decimal
from sqlalchemy.sql import func 

class CicloDisponible(db.Model):
    __tablename__ = 'ciclos_disponibles_prorrateo'
    id = db.Column(db.Integer, primary_key=True)
    dia = db.Column(db.Integer, unique=True, nullable=False)

    def to_dict(self):
        return self.dia

class Plan(db.Model):
    __tablename__ = 'planes_prorrateo'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    prorrateo_dia_base = db.Column(db.Numeric(10, 4), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'precio': str(self.precio),
            'prorrateo_dia_base': str(self.prorrateo_dia_base)
        }

class CicloRegla(db.Model):
    __tablename__ = 'ciclo_reglas_prorrateo'
    id = db.Column(db.Integer, primary_key=True)
    ciclo_base_code = db.Column(db.String(10), unique=True, nullable=False) 
    logica_descripcion = db.Column(db.String(255), nullable=False)
    mensaje_guia = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'ciclo_base_code': self.ciclo_base_code,
            'logica_descripcion': self.logica_descripcion,
            'mensaje_guia': self.mensaje_guia
        }

class ContratoProrrateo(db.Model):
    __tablename__ = 'contratos_prorrateo'
    id = db.Column(db.Integer, primary_key=True)
    
    nombre_cliente = db.Column(db.String(200), nullable=False)
    tipo_documento = db.Column(db.String(50))
    numero_documento = db.Column(db.String(50))
    celular = db.Column(db.String(20), nullable=True) 
    
    # --- CAMPOS AÑADIDOS ---
    lugar_nacimiento_cliente = db.Column(db.String(100), nullable=True)
    fecha_nacimiento_cliente = db.Column(db.Date, nullable=True)
    correo_cliente = db.Column(db.String(120), nullable=True)
    # -------------------------

    plan_id = db.Column(db.Integer, db.ForeignKey('planes_prorrateo.id'), nullable=False)
    plan = db.relationship('Plan', backref=db.backref('contratos_prorrateos', lazy=True))
    
    ciclo_base_seleccionado = db.Column(db.String(10), nullable=False)
    ciclo_final_dia = db.Column(db.Integer, nullable=False)

    prorrateo_dia_aplicado = db.Column(db.Numeric(10, 4))
    fecha_cierre_calculada = db.Column(db.Date)
    prorrateo_total_calculado = db.Column(db.Numeric(10, 2))
    fecha_activacion_calculada = db.Column(db.Date)
    fecha_pago_calculada = db.Column(db.Date)
    
    fecha_formulario_hoy = db.Column(db.Date) 
    fecha_registro_sistema = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    user = db.relationship('User', backref=db.backref('contratos_prorrateos', lazy=True)) 

    def to_dict(self): # Asegúrate de incluir los nuevos campos aquí también
        return {
            'id': self.id,
            'nombre_cliente': self.nombre_cliente,
            'tipo_documento': self.tipo_documento,
            'numero_documento': self.numero_documento,
            'celular': self.celular,
            'lugar_nacimiento_cliente': self.lugar_nacimiento_cliente, # <-- NUEVO
            'fecha_nacimiento_cliente': self.fecha_nacimiento_cliente.isoformat() if self.fecha_nacimiento_cliente else None, # <-- NUEVO
            'correo_cliente': self.correo_cliente, # <-- NUEVO
            'plan_nombre': self.plan.nombre if self.plan else None,
            'plan_precio': str(self.plan.precio) if self.plan else None,
            'ciclo_base_seleccionado': self.ciclo_base_seleccionado,
            'ciclo_final_dia': self.ciclo_final_dia,
            'prorrateo_dia_aplicado': str(self.prorrateo_dia_aplicado) if self.prorrateo_dia_aplicado is not None else None,
            'fecha_cierre_calculada': self.fecha_cierre_calculada.isoformat() if self.fecha_cierre_calculada else None,
            'prorrateo_total_calculado': str(self.prorrateo_total_calculado) if self.prorrateo_total_calculado is not None else None,
            'fecha_activacion_calculada': self.fecha_activacion_calculada.isoformat() if self.fecha_activacion_calculada else None,
            'fecha_pago_calculada': self.fecha_pago_calculada.isoformat() if self.fecha_pago_calculada else None,
            'fecha_formulario_hoy': self.fecha_formulario_hoy.isoformat() if self.fecha_formulario_hoy else None,
            'fecha_registro_sistema': self.fecha_registro_sistema.isoformat() if self.fecha_registro_sistema else None,
            'registrado_por_usuario_id': self.user_id
        }