# /backend-consentimientos/seed_prorrateos.py
from app import app, db # Importamos app y db de tu app.py principal
# Importamos los modelos de su nueva ubicación
from models.prorrateo_models import CicloDisponible, Plan, CicloRegla
import decimal

def seed_data_prorrateos():
    # Este script se ejecuta dentro del contexto de la aplicación Flask,
    # por lo que usará la conexión a la base de datos que esté configurada en app.py (SQL Server en este caso).
    with app.app_context():
        print("Verificando y sembrando datos para Ciclos y Prorrateos en SQL Server...")

        # --- Ciclos Disponibles ---
        ciclos_a_sembrar = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]
        try:
            ciclos_existentes_db = {c.dia for c in CicloDisponible.query.all()}
            nuevos_ciclos = 0
            for dia_ciclo in ciclos_a_sembrar:
                if dia_ciclo not in ciclos_existentes_db:
                    db.session.add(CicloDisponible(dia=dia_ciclo))
                    nuevos_ciclos += 1
            if nuevos_ciclos > 0:
                print(f"Añadidos {nuevos_ciclos} nuevos días de ciclo.")
            else:
                print("Días de ciclo disponibles ya estaban actualizados.")
        except Exception as e:
            print(f"Error al sembrar Ciclos Disponibles. ¿Las tablas ya existen? Error: {e}")
            db.session.rollback()


        # --- Planes ---
        # Cambiado el nombre para evitar conflictos con datos existentes
        planes_data = [
            {"nombre": "PLAN PRORRATEO S/39.90", "precio": decimal.Decimal("39.90")},
            {"nombre": "PLAN PRORRATEO S/49.90", "precio": decimal.Decimal("49.90")},
            {"nombre": "PLAN PRORRATEO S/65.90", "precio": decimal.Decimal("65.90")},
            # Añade más planes según tus necesidades
        ]
        try:
            nuevos_planes = 0
            for plan_info in planes_data:
                if not Plan.query.filter_by(nombre=plan_info["nombre"]).first():
                    prorrateo_calculado = round(plan_info["precio"] / 30, 4)
                    db.session.add(Plan(
                        nombre=plan_info["nombre"],
                        precio=plan_info["precio"],
                        prorrateo_dia_base=prorrateo_calculado
                    ))
                    nuevos_planes +=1
            if nuevos_planes > 0:
                 print(f"Añadidos {nuevos_planes} nuevos planes.")
            else:
                print("Planes ya estaban actualizados.")
        except Exception as e:
            print(f"Error al sembrar Planes. Error: {e}")
            db.session.rollback()
        
        # --- Reglas de Ciclo ---
        reglas_ciclo_data = [
            {"ciclo_base_code": "CICLO_00", "logica_descripcion": "APERTURA LISTA", "mensaje_guia": "Consultar con el supervisor."},
            {"ciclo_base_code": "CICLO_99", "logica_descripcion": "MAS CERCANO AL DIA DE HOY", "mensaje_guia": None},
            {"ciclo_base_code": "CICLO_25", "logica_descripcion": "ASIGNAR CICLO 23", "mensaje_guia": None},
        ]
        try:
            nuevas_reglas = 0
            for regla_info in reglas_ciclo_data:
                if not CicloRegla.query.filter_by(ciclo_base_code=regla_info["ciclo_base_code"]).first():
                    db.session.add(CicloRegla(**regla_info))
                    nuevas_reglas += 1
            if nuevas_reglas > 0:
                print(f"Añadidas {nuevas_reglas} nuevas reglas de ciclo.")
            else:
                print("Reglas de ciclo ya estaban actualizadas.")
        except Exception as e:
            print(f"Error al sembrar Reglas de Ciclo. Error: {e}")
            db.session.rollback()
            
        # Un único commit al final para todas las operaciones exitosas
        try:
            db.session.commit()
            print("Siembra de datos de prorrateos completada/verificada.")
        except Exception as e:
            print(f"Error final al hacer commit de los datos de seed: {e}")
            db.session.rollback()

if __name__ == '__main__':
    seed_data_prorrateos()
