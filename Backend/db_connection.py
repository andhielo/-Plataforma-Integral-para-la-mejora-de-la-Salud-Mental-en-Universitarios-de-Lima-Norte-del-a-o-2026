import pyodbc
import pandas as pd
from datetime import datetime

class DatabaseConnection:
    def __init__(self):
        self.conn_str = (
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=.\SQLEXPRESS;' 
            r'DATABASE=BienestarUniversitarioDW;'
            r'UID=sa;'
            r'PWD=ucv123;'
        )

    def cargar_dw(self, df):
        """Carga los datos a todas las dimensiones y la tabla de hechos SIN dejar nulos"""
        try:
            conn = pyodbc.connect(self.conn_str)
            cursor = conn.cursor()

            for index, row in df.iterrows():
                # 1. Dim_Estudiante
                codigo = str(row.get('codigo_uni', ''))
                cursor.execute("SELECT sk_estudiante FROM Dim_Estudiante WHERE codigo_uni = ?", (codigo,))
                res_est = cursor.fetchone()
                if not res_est:
                    cursor.execute("""
                        INSERT INTO Dim_Estudiante (codigo_uni, nombre, genero, edad, ciclo_academico, condicion_socioeconomica)
                        OUTPUT INSERTED.sk_estudiante
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        codigo, 
                        str(row.get('nombre', '')), 
                        str(row.get('genero', '')), 
                        int(row.get('edad', 0)), 
                        str(row.get('ciclo_academico', '')), 
                        str(row.get('condicion_socioeconomica', ''))
                    ))
                    sk_estudiante = cursor.fetchone()[0]
                else:
                    sk_estudiante = res_est[0]

                # 2. Dim_Carrera (¡AHORA INCLUYE FACULTAD Y ÁREA!)
                carrera = str(row.get('nombre_carrera', 'No Especificada'))
                facultad = str(row.get('facultad', 'No Especificada'))
                area = str(row.get('area_academica', 'No Especificada'))
                
                cursor.execute("SELECT sk_carrera FROM Dim_Carrera WHERE nombre_carrera = ?", (carrera,))
                res_car = cursor.fetchone()
                if not res_car:
                    cursor.execute("""
                        INSERT INTO Dim_Carrera (nombre_carrera, facultad, area_academica) 
                        OUTPUT INSERTED.sk_carrera 
                        VALUES (?, ?, ?)
                    """, (carrera, facultad, area))
                    sk_carrera = cursor.fetchone()[0]
                else:
                    sk_carrera = res_car[0]
                    
                # 3. Dim_Nivel_Riesgo (¡AHORA INCLUYE DESCRIPCIONES AUTOMÁTICAS!)
                riesgo = str(row.get('nivel_riesgo', 'Estable'))
                
                # Asignamos una intervención automática según el riesgo
                if riesgo == 'Crítico':
                    intervencion = 'Derivar a Psicología / Contactar urgencia'
                elif riesgo == 'Observación':
                    intervencion = 'Monitoreo preventivo / Enviar recursos'
                else:
                    intervencion = 'Sin acción requerida'
                    
                fuente = 'Modelo Machine Learning (Python)'

                cursor.execute("SELECT sk_riesgo FROM Dim_Nivel_Riesgo WHERE categoria_riesgo = ?", (riesgo,))
                res_rie = cursor.fetchone()
                if not res_rie:
                    cursor.execute("""
                        INSERT INTO Dim_Nivel_Riesgo (categoria_riesgo, descripcion_intervencion, fuente_alerta) 
                        OUTPUT INSERTED.sk_riesgo 
                        VALUES (?, ?, ?)
                    """, (riesgo, intervencion, fuente))
                    sk_riesgo = cursor.fetchone()[0]
                else:
                    sk_riesgo = res_rie[0]
                    
                # 4. Dim_Tiempo (¡AHORA DESGLOSA LA FECHA DEL EXCEL!)
                # Toma la fecha de registro del CSV, si no hay, toma la de hoy
                fecha_str = str(row.get('fecha_registro', datetime.now().strftime('%Y-%m-%d')))
                try:
                    fecha_obj = pd.to_datetime(fecha_str)
                except:
                    fecha_obj = datetime.now()
                    
                sk_tiempo = int(fecha_obj.strftime('%Y%m%d'))
                dia_semana = fecha_obj.strftime('%A')
                mes = int(fecha_obj.month)
                anio = int(fecha_obj.year)
                semana = int(fecha_obj.isocalendar()[1])
                es_feriado = 0 # 0 por defecto
                
                cursor.execute("SELECT sk_tiempo FROM Dim_Tiempo WHERE sk_tiempo = ?", (sk_tiempo,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO Dim_Tiempo (sk_tiempo, fecha, dia_semana, mes, anio, es_feriado, semana_del_semestre) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (sk_tiempo, fecha_obj.date(), dia_semana, mes, anio, es_feriado, semana))

                # 5. Fact_Monitoreo_Bienestar (¡AHORA INCLUYE LA ASISTENCIA!)
                asistencia_flag = int(float(row.get('asistencia_cita_flag', 0)))
                
                cursor.execute("""
                    INSERT INTO Fact_Monitoreo_Bienestar 
                    (sk_estudiante, sk_tiempo, sk_carrera, sk_riesgo, puntaje_estres, inasistencias_lms, indice_sentimiento, asistencia_cita_flag, nota_promedio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sk_estudiante, sk_tiempo, sk_carrera, sk_riesgo,
                    float(row.get('puntaje_estres', 0)),
                    int(row.get('inasistencias_lms', 0)),
                    float(row.get('indice_sentimiento', 0)),
                    asistencia_flag,
                    float(row.get('nota_promedio', 0))
                ))

            conn.commit()
            cursor.close()
            conn.close()
            return True, "Carga exitosa al DW sin nulos"
        except Exception as e:
            return False, str(e)

    def obtener_historial(self):
        """Recupera el historial completo desde SQL Server uniendo las tablas (Star Schema)"""
        try:
            conn = pyodbc.connect(self.conn_str)
            sql = """
                SELECT 
                    e.codigo_uni, e.nombre, e.ciclo_academico,
                    c.nombre_carrera,
                    r.categoria_riesgo as nivel_riesgo,
                    f.puntaje_estres, f.nota_promedio, f.indice_sentimiento, f.inasistencias_lms,
                    f.asistencia_cita_flag
                FROM Fact_Monitoreo_Bienestar f
                JOIN Dim_Estudiante e ON f.sk_estudiante = e.sk_estudiante
                JOIN Dim_Carrera c ON f.sk_carrera = c.sk_carrera
                JOIN Dim_Nivel_Riesgo r ON f.sk_riesgo = r.sk_riesgo
            """
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                df = pd.read_sql(sql, conn)
                
            conn.close()
            return True, df
        except Exception as e:
            return False, str(e)