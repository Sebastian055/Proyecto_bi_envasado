-- =============================================================================
-- FASE 8: CONSULTAS SQL ANALÍTICAS PARA PREGUNTAS DE NEGOCIO
-- =============================================================================

-- 1. ¿Cuáles son los 3 códigos de paro que generan mayor pérdida de tiempo?
SELECT 
    cp.codigo_general,
    cp.descripcion_general,
    ROUND(SUM(fp.tiempo_paro_minutos), 2) AS total_minutos_paro,
    ROUND(SUM(fp.tiempo_paro_minutos) / 60.0, 2) AS total_horas_paro
FROM fact_paros fp
JOIN dim_codigo_paro cp ON fp.codigo_paro_key = cp.codigo_paro_key
GROUP BY cp.codigo_general, cp.descripcion_general
ORDER BY total_minutos_paro DESC
LIMIT 3;

-- 2. ¿Qué líneas o máquinas presentan el mayor o menor rendimiento de producción?
SELECT 
    m.codigo_linea,
    m.nombre_linea,
    ROUND(SUM(fph.horas_trabajadas), 2) AS total_horas_operadas,
    ROUND(SUM(fph.pacas_producidas), 2) AS total_pacas_producidas,
    ROUND(SUM(fph.meta_pacas_hora), 2) AS total_meta_pacas,
    ROUND(SUM(fph.pacas_producidas) / NULLIF(SUM(fph.horas_trabajadas), 0), 2) AS pacas_por_hora,
    COALESCE(
        ROUND((SUM(fph.pacas_producidas) / NULLIF(SUM(fph.meta_pacas_hora), 0)) * 100, 2), 
        0.00
    ) AS porcentaje_cumplimiento
FROM fact_produccion_hora fph
JOIN dim_maquina m ON fph.maquina_key = m.maquina_key
GROUP BY m.codigo_linea, m.nombre_linea
ORDER BY total_horas_operadas DESC;

-- 3. ¿Cuál es la evolución mensual de las paradas por servicios (Cod 03: aire, energía)?
SELECT 
    dt.anio,
    dt.mes,
    dt.nombre_mes,
    m.codigo_linea,
    ROUND(SUM(fp.tiempo_paro_minutos), 2) AS minutos_paro_servicios
FROM fact_paros fp
JOIN dim_tiempo dt ON fp.fecha_key = dt.fecha_key
JOIN dim_maquina m ON fp.maquina_key = m.maquina_key
JOIN dim_codigo_paro cp ON fp.codigo_paro_key = cp.codigo_paro_key
WHERE cp.codigo_general = '[03]' OR cp.codigo_general = '03'
GROUP BY dt.anio, dt.mes, dt.nombre_mes, m.codigo_linea
ORDER BY dt.anio ASC, dt.mes ASC, m.codigo_linea ASC;

-- 4. ¿Qué operarias o turnos registran mayor tiempo en ajustes operativos (Cod 05)?
WITH AjustesPorOperario AS (
    SELECT 
        m.codigo_linea,
        o.nombre_operario,
        dt.turno,
        ROUND(SUM(fp.tiempo_paro_minutos), 2) AS total_minutos_ajuste
    FROM fact_paros fp
    JOIN dim_maquina m ON fp.maquina_key = m.maquina_key
    JOIN dim_operario o ON fp.operario_key = o.operario_key
    JOIN dim_tiempo dt ON fp.fecha_key = dt.fecha_key
    JOIN dim_codigo_paro cp ON fp.codigo_paro_key = cp.codigo_paro_key
    WHERE cp.codigo_general = '[05]' OR cp.codigo_general = '05'
    GROUP BY m.codigo_linea, o.nombre_operario, dt.turno
)
SELECT 
    codigo_linea,
    nombre_operario,
    turno,
    total_minutos_ajuste,
    DENSE_RANK() OVER (
        PARTITION BY codigo_linea 
        ORDER BY total_minutos_ajuste DESC
    ) AS ranking_en_linea
FROM AjustesPorOperario
ORDER BY codigo_linea ASC, ranking_en_linea ASC;

-- 5. ¿Cuál es el volumen de producción y tiempo de paro mes a mes comparado entre 2024 y 2025?
WITH ProdMensual AS (
    SELECT 
        dt.anio,
        dt.mes,
        dt.nombre_mes,
        ROUND(SUM(fph.pacas_producidas), 2) AS pacas_actuales
    FROM fact_produccion_hora fph
    JOIN dim_tiempo dt ON fph.fecha_key = dt.fecha_key
    GROUP BY dt.anio, dt.mes, dt.nombre_mes
),
ParosMensual AS (
    SELECT 
        dt.anio,
        dt.mes,
        ROUND(SUM(fp.tiempo_paro_minutos), 2) AS minutos_paro_actuales
    FROM fact_paros fp
    JOIN dim_tiempo dt ON fp.fecha_key = dt.fecha_key
    GROUP BY dt.anio, dt.mes
),
ConsolidadoMensual AS (
    SELECT 
        pm.anio,
        pm.mes,
        pm.nombre_mes,
        COALESCE(pm.pacas_actuales, 0) AS pacas_actuales,
        COALESCE(prm.minutos_paro_actuales, 0) AS minutos_paro_actuales
    FROM ProdMensual pm
    LEFT JOIN ParosMensual prm ON pm.anio = prm.anio AND pm.mes = prm.mes
)
SELECT 
    anio,
    mes,
    nombre_mes,
    pacas_actuales,
    LAG(pacas_actuales, 12) OVER (ORDER BY anio ASC, mes ASC) AS pacas_anio_anterior,
    ROUND(
        pacas_actuales - LAG(pacas_actuales, 12) OVER (ORDER BY anio ASC, mes ASC), 2
    ) AS var_pacas_interanual,
    minutos_paro_actuales,
    LAG(minutos_paro_actuales, 12) OVER (ORDER BY anio ASC, mes ASC) AS minutos_paro_anio_anterior,
    ROUND(
        minutos_paro_actuales - LAG(minutos_paro_actuales, 12) OVER (ORDER BY anio ASC, mes ASC), 2
    ) AS var_paros_interanual
FROM ConsolidadoMensual
ORDER BY anio ASC, mes ASC;
