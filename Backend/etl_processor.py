import pandas as pd

class ETLProcessor:
    def __init__(self, filepath):
        self.filepath = filepath

    def get_raw_data(self):
        """Lee el archivo subido (CSV o Excel)"""
        if self.filepath.endswith('.csv'):
            return pd.read_csv(self.filepath)
        else:
            return pd.read_excel(self.filepath)

    def run_etl(self):
        """Limpia y transforma los datos a prueba de errores de formato"""
        df = self.get_raw_data()
        
        # 1. Eliminar duplicados
        df = df.drop_duplicates()
        
        # 2. Limpieza exhaustiva: Forzar a numérico las columnas de cálculo
        # Si Excel coló texto o fechas por error, esto lo convierte a NaN (Nulo)
        columnas_numericas = ['nota_promedio', 'puntaje_estres', 'inasistencias_lms', 'indice_sentimiento']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 3. Tratamiento de nulos (imputación por la media en notas)
        if 'nota_promedio' in df.columns:
            media = df['nota_promedio'].mean()
            # Si toda la columna era texto/fechas y la media falla, usamos 14 por defecto
            media = round(media, 2) if pd.notna(media) else 14.0 
            df['nota_promedio'] = df['nota_promedio'].fillna(media)
            
        # 4. Normalizar fechas si existen
        if 'fecha_registro' in df.columns:
            df['fecha_norm'] = pd.to_datetime(df['fecha_registro'], errors='coerce').dt.strftime('%Y-%m-%d')
            
        return df