import pandas as pd

class RiesgoPredictor:
    @staticmethod
    def reglas_diagnostico(row):
        """Lógica del modelo para diagnosticar el riesgo del estudiante"""
        # Usamos .get() por si el Excel subido no tiene alguna columna
        estres = float(row.get('puntaje_estres', 0))
        lms = float(row.get('inasistencias_lms', 0))
        sentimiento = float(row.get('indice_sentimiento', 0))

        if estres > 85 or lms > 12 or sentimiento < -0.7:
            return 'Crítico'
        elif estres > 60 or lms > 5 or sentimiento < 0:
            return 'Observación'
        else:
            return 'Estable'

    def aplicar_modelo(self, df):
        """Aplica la clasificación a todo el DataFrame"""
        df['nivel_riesgo'] = df.apply(self.reglas_diagnostico, axis=1)
        return df