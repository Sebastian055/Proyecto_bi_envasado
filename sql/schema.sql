-- 1.1: dimension de tiempo
CREATE TABLE dim_tiempo (
    fecha_key INT PRIMARY KEY,
    fecha DATE NOT NULL,
    anio INT NOT NULL,
    mes INT NOT NULL,
    nombre_mes VARCHAR(15) NOT NULL,
    dia INT NOT NULL,
    turno INT NOT NULL CHECK (turno IN (1, 2, 3)), -- turnos laborales (1-mañana, 2-tarde, 3-noche)
    hora INT NOT NULL CHECK (hora BETWEEN 0 AND 23) -- Hora militar del día (0 a 23)
);

-- 1.2 dimension de maquinas
CREATE TABLE dim_maquina (
    maquina_key SERIAL PRIMARY KEY,
    codigo_linea VARCHAR(20) UNIQUE NOT NULL,
    nombre_linea VARCHAR(50) NOT NULL
);

-- 1.3 dimension operario
CREATE TABLE dim_operario (
    operario_key SERIAL PRIMARY KEY,
    codigo_primario VARCHAR(20) NOT NULL,
    nombre_operario VARCHAR(100) NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NULL,
    activo BOOLEAN NOT NULL
);

-- 1.4 dimension producto
CREATE TABLE dim_producto (
    producto_key SERIAL PRIMARY KEY,
    referencia VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(30) NULL,
    capacidad_cc INT NULL
);

-- 1.5 dimension codigo de paro
CREATE TABLE dim_codigo_paro (
    codigo_paro_key SERIAL PRIMARY KEY,
    codigo_general VARCHAR(10) NOT NULL,
    descripcion_general VARCHAR(150) NOT NULL,
    subcodigo VARCHAR(10) NULL,
    descripcion_subcodigo VARCHAR(150) NULL
);

-- 2.1 hecho de produccion hora a hora
CREATE TABLE fact_produccion_hora (
    fecha_prod_id SERIAL PRIMARY KEY,
    fecha_key INT NOT NULL REFERENCES dim_tiempo(fecha_key),
    maquina_key INT NOT NULL REFERENCES dim_maquina(maquina_key),
    operario_key INT NOT NULL REFERENCES dim_operario(operario_key),
    producto_key INT NOT NULL REFERENCES dim_producto(producto_key),
    horas_trabajadas NUMERIC(4,2) NOT NULL DEFAULT 1.0,
    meta_pacas_hora NUMERIC(8,2) NOT NULL DEFAULT 0.0,
    pacas_producidas NUMERIC(8,2) NOT NULL DEFAULT 0.0
);

-- 2.2 hecho de registro de paros
CREATE TABLE fact_paros (
    paro_id SERIAL PRIMARY KEY,
    fecha_key INT NOT NULL REFERENCES dim_tiempo(fecha_key),
    maquina_key INT NOT NULL REFERENCES dim_maquina(maquina_key),
    operario_key INT NOT NULL REFERENCES dim_operario(operario_key),
    codigo_paro_key INT NOT NULL REFERENCES dim_codigo_paro(codigo_paro_key),
    tiempo_paro_minutos NUMERIC(6,2) NOT NULL CHECK (tiempo_paro_minutos >= 0),
    observacion TEXT NULL
);



-- 3. optimizacion de consultas (indices)

-- indices en foreign keys para acelerar los agrupamientos (group BY) y JOINs
-- desde power BI, Grafana y consultas SQL analiticas

--optimizacion para consultas de produccion 
CREATE INDEX idx_fact_prod_tiempo ON fact_produccion_hora(fecha_key);
CREATE INDEX idx_fact_paros_maquina ON fact_produccion_hora(maquina_key);
CREATE INDEX idx_fact prod_producto ON fect_produccion_hora(producto_key);

--optimizacion para consultas de analisis de paros y tiempos perdidos
CREATE INDEX idx_fact_paros_tiempo ON fact_paros(fecha_key);
CREATE INDEX idx_fact_paros_maquina ON fact_paros(maquina_key);
CREATE INDEX idx_fact_paros_codigo ON fact_paros(codigo_paro_key);

