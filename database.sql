-- 1. CREACIÓN DE LA TABLA CON RESTRICCIONES (CONSTRAINTS)
CREATE TABLE Fact_Monitoreo_Bienestar (
    id_estudiante INT IDENTITY(1,1) PRIMARY KEY,
    codigo_uni VARCHAR(20) NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    carrera VARCHAR(100) NOT NULL,
    ciclo VARCHAR(10) NOT NULL,
    puntaje_estres INT NOT NULL,
    faltas_lms INT NOT NULL,
    nota_promedio DECIMAL(4,1) NOT NULL,
    sentimiento_ia DECIMAL(3,2) NOT NULL,
    nivel_riesgo VARCHAR(20),
    problema_detectado VARCHAR(50),
    
    -- CONSTRAINTS: Restricciones de validación de rangos de datos
    CONSTRAINT UQ_Codigo_Estudiante UNIQUE (codigo_uni),
    CONSTRAINT CK_Puntaje_Estres CHECK (puntaje_estres BETWEEN 0 AND 100),
    CONSTRAINT CK_Faltas_LMS CHECK (faltas_lms >= 0),
    CONSTRAINT CK_Nota_Promedio CHECK (nota_promedio BETWEEN 0.0 AND 20.0),
    CONSTRAINT CK_Sentimiento_IA CHECK (sentimiento_ia BETWEEN -1.00 AND 1.00)
);
GO

-- 2. CREACIÓN DEL TRIGGER (DISPARADOR) PARA ESTANDARIZAR Y CALCULAR EL RIESGO
CREATE TRIGGER TRG_Insertar_Estudiante_Bienestar
ON Fact_Monitoreo_Bienestar
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Validación para evitar duplicados en la transacción actual
    IF EXISTS (
        SELECT 1 
        FROM Fact_Monitoreo_Bienestar f
        JOIN inserted i ON f.codigo_uni = i.codigo_uni
    )
    BEGIN
        RAISERROR ('Alerta SQL: Registro duplicado bloqueado para el código universitario.', 16, 1);
        RETURN;
    END

    -- Inserción final procesando limpieza (ETL) y reglas de negocio (Motor IA)
    INSERT INTO Fact_Monitoreo_Bienestar (
        codigo_uni, 
        nombre_completo, 
        carrera, 
        ciclo, 
        puntaje_estres, 
        faltas_lms, 
        nota_promedio, 
        sentimiento_ia, 
        nivel_riesgo, 
        problema_detectado
    )
    SELECT 
        i.codigo_uni,
        UPPER(LTRIM(RTRIM(i.nombre_completo))), -- Estandariza texto eliminando espacios sucios
        UPPER(LTRIM(RTRIM(i.carrera))),         -- Estandariza carrera a mayúsculas
        i.ciclo,
        i.puntaje_estres,
        i.faltas_lms,
        i.nota_promedio,
        i.sentimiento_ia,
        
        -- Regla de negocio automatizada para determinar el Nivel de Riesgo
        CASE 
            WHEN i.puntaje_estres > 85 OR i.faltas_lms > 12 OR i.sentimiento_ia < -0.7 THEN 'Crítico'
            WHEN i.puntaje_estres > 60 OR i.faltas_lms > 5 THEN 'Observación'
            ELSE 'Estable'
         Brahm,
         
        -- Regla de negocio para asignar el problema principal estimado
        CASE 
            WHEN i.puntaje_estres > 85 OR i.faltas_lms > 12 OR i.sentimiento_ia < -0.7 
                THEN (CASE WHEN ABS(CHECKSUM(NEWID())) % 2 = 0 THEN 'Ansiedad' ELSE 'Estrés' END)
            WHEN i.puntaje_estres > 60 OR i.faltas_lms > 5 
                THEN (CASE WHEN ABS(CHECKSUM(NEWID())) % 3 = 0 THEN 'Ansiedad' WHEN ABS(CHECKSUM(NEWID())) % 3 = 1 THEN 'Estrés' ELSE 'Otros' END)
            ELSE 'Otros'
        END
    FROM inserted i;
END;
GO