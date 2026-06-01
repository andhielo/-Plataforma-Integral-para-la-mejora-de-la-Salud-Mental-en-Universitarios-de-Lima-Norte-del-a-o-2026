from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import os
import traceback

from etl_processor import ETLProcessor
from ml_predictor import RiesgoPredictor
from db_connection import DatabaseConnection

# 1. Definimos las rutas absolutas para que nunca se pierda
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Apunta a la carpeta src/
TEMPLATE_DIR = os.path.join(BASE_DIR, '../templates') # Apunta a la carpeta templates/
UPLOAD_FOLDER = os.path.join(BASE_DIR, '../data_pruebas')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
FILE_PATH = os.path.join(UPLOAD_FOLDER, 'temp_upload')

app = Flask(__name__)

# Variable global en memoria para simular el estado de la BD en esta demo
processed_df = None 

@app.route('/')
def index():
    # Sirve el archivo index.html desde la ruta absoluta
    return send_from_directory(TEMPLATE_DIR, 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        # Soportar CSV o Excel
        ext = file.filename.split('.')[-1].lower()
        full_path = f"{FILE_PATH}.{ext}"
        
        # Guardar el archivo
        file.save(full_path)
        
        # Leer para sacar estadísticas de Staging
        if ext == 'csv':
            df = pd.read_csv(full_path)
        else:
            df = pd.read_excel(full_path)
            
        return jsonify({
            'status': 'success',
            'registros': len(df),
            'file_path': full_path
        })
        
    except PermissionError:
        return jsonify({'error': 'Windows bloqueó el archivo. Asegúrate de cerrar el Excel e inténtalo de nuevo.'}), 500
    except Exception as e:
        return jsonify({'error': f'Error interno en Python: {str(e)}'}), 500

@app.route('/api/etl', methods=['POST'])
def run_etl():
    global processed_df
    data = request.json
    
    if not data or 'file_path' not in data:
        return jsonify({'error': 'No se proporcionó la ruta del archivo'}), 400
        
    file_path = data.get('file_path')
    
    try:
        # Ejecutar ETL
        etl = ETLProcessor(file_path)
        df_limpio = etl.run_etl()
        
        # Aplicar IA
        predictor = RiesgoPredictor()
        df_final = predictor.aplicar_modelo(df_limpio)
        
        # Guardar en memoria para el dashboard
        processed_df = df_final
        
        # ---> GUARDAR EN SQL SERVER <---
        db = DatabaseConnection()
        exito, mensaje = db.cargar_dw(df_final)
        if not exito:
            print(f"ADVERTENCIA SQL: {mensaje}") 
            
        return jsonify({'status': 'success', 'registros_procesados': len(df_final)})
    except Exception as e:
        error_msg = f"Error en el ETL/IA: {str(e)}\n\nDetalles técnicos:\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

@app.route('/api/data', methods=['GET'])
def get_dashboard_data():
    global processed_df
    
    # --- NUEVA LÓGICA DE RECUPERACIÓN DE SQL SERVER ---
    if processed_df is None:
        db = DatabaseConnection()
        exito, df_recuperado = db.obtener_historial()
        
        if exito and not df_recuperado.empty:
            processed_df = df_recuperado
            print("Datos recuperados exitosamente desde SQL Server.")
        else:
            return jsonify({'error': 'No hay datos en SQL Server. Sube un archivo Excel primero.'}), 400
            
    df = processed_df
    
    # --- CÁLCULOS BI PARA EL FRONTEND ---
    total = len(df)
    criticos = len(df[df['nivel_riesgo'].str.contains('Crítico', na=False)]) if 'nivel_riesgo' in df.columns else 0
    observacion = len(df[df['nivel_riesgo'].str.contains('Observación', na=False)]) if 'nivel_riesgo' in df.columns else 0
    estables = total - criticos - observacion
    
    nota_promedio = round(df['nota_promedio'].mean(), 1) if 'nota_promedio' in df.columns else 0
    sentimiento_general = round(df['indice_sentimiento'].mean(), 2) if 'indice_sentimiento' in df.columns else 0
    
    carreras_stats = []
    if 'nombre_carrera' in df.columns and 'nivel_riesgo' in df.columns:
        for carrera, group in df.groupby('nombre_carrera'):
            c_criticos = len(group[group['nivel_riesgo'].str.contains('Crítico', na=False)])
            c_obs = len(group[group['nivel_riesgo'].str.contains('Observación', na=False)])
            c_total = len(group)
            
            carreras_stats.append({
                'carrera': str(carrera),
                'criticos': int(c_criticos),
                'observacion': int(c_obs),
                'estables': int(c_total - c_criticos - c_obs),
                'pct_riesgo': round((c_criticos / c_total) * 100, 1) if c_total > 0 else 0
            })

    # Datos para la tabla del Data Warehouse (Sin límite de 50 registros)
    estudiantes_list = []
    for _, row in df.iterrows(): 
        nivel_r = str(row.get('nivel_riesgo', ''))
        riesgo_texto = 'Crítico' if 'Crítico' in nivel_r else ('Observación' if 'Observación' in nivel_r else 'Estable')
        
        # Extracción segura de la asistencia
        try:
            asistencia_val = int(float(row.get('asistencia_cita_flag', 0)))
        except:
            asistencia_val = 0
            
        estudiantes_list.append({
            'codigo': str(row.get('codigo_uni', '')),
            'nombre': str(row.get('nombre', 'Alumno Anónimo')),
            'carrera': str(row.get('nombre_carrera', '')),
            'ciclo': str(row.get('ciclo_academico', '')),
            'riesgo': riesgo_texto,
            'estres': float(row.get('puntaje_estres', 0)),
            'nota': float(row.get('nota_promedio', 0)),
            'sentimiento': float(row.get('indice_sentimiento', 0)),
            'lms': int(row.get('inasistencias_lms', 0)),
            'asistencia': asistencia_val  # <--- COLUMNA AÑADIDA AQUÍ
        })

    return jsonify({
        'resumen': {
            'total_monitoreados': int(total),
            'total_criticos': int(criticos),
            'total_observacion': int(observacion),
            'total_estables': int(estables),
            'nota_promedio': float(nota_promedio),
            'sentimiento_general': float(sentimiento_general),
            'pct_riesgo': round((criticos/total)*100, 1) if total > 0 else 0
        },
        'carreras': carreras_stats,
        'estudiantes': estudiantes_list
    })

@app.route('/api/predict', methods=['POST'])
def simular_prediccion():
    data = request.json
    estres = float(data.get('estres', 0))
    lms = float(data.get('lms', 0))
    sent = float(data.get('sentimiento', 0))
    
    if estres > 85 or lms > 12 or sent < -0.7:
        r = {"riesgo": "Crítico", "prob": 0.92, "desercion": 0.78, "cluster": 4, "color": "#ef4444"}
    elif estres > 60 or lms > 5 or sent < 0:
        r = {"riesgo": "Observación", "prob": 0.71, "desercion": 0.35, "cluster": 3, "color": "#f59e0b"}
    else:
        r = {"riesgo": "Estable", "prob": 0.85, "desercion": 0.08, "cluster": 1, "color": "#22c55e"}
        
    return jsonify(r)

if __name__ == '__main__':
    app.run(debug=True)