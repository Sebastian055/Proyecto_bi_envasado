import os
import re
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables del entorno (.env)
load_dotenv()

DB_USER = os.getenv("PGUSER", os.getenv("DB_USER", "postgres"))
DB_PASS = os.getenv("PGPASSWORD", os.getenv("DB_PASS", "tu_contraseña_aqui"))
DB_HOST = os.getenv("PGHOST", os.getenv("DB_HOST", "localhost"))
DB_PORT = os.getenv("PGPORT", os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", os.getenv("DB_NAME", "bi_envasado"))

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)


def ejecutar_etl():
    print("==================================================")
    print("      INICIANDO PIPELINE DE ETL (FASE 7)         ")
    print("==================================================")

    # ---------------------------------------------------------
    # 1. EXTRAER DATOS CON DETECCIÓN DINÁMICA DE ENCABEZADO
    # ---------------------------------------------------------
    path_excel = r"C:\Users\FAMILIA\Downloads\SEGUIMIENTO TEMPERAS Y VINILOS Actividad.xlsm"
    print(f"\n[1/5] Extrayendo datos desde: {path_excel}...")

    hoja_destino = "Base De Datos"
    df_preview = pd.read_excel(path_excel, sheet_name=hoja_destino, nrows=15, header=None)
    header_row = 0
    for idx, row in df_preview.iterrows():
        valores = [str(val).lower().strip() for val in row.values if pd.notna(val)]
        texto_fila = " ".join(valores)
        if any(kw in texto_fila for kw in ["operaria", "operario", "máquina", "maquina", "referencia", "día", "dia"]):
            header_row = idx
            break

    df_raw = pd.read_excel(path_excel, sheet_name=hoja_destino, header=header_row)
    df_raw.columns = [str(col).replace("\n", " ").strip() for col in df_raw.columns]
    conteo_inicial = len(df_raw)
    print(f"-> Registros iniciales en Excel: {conteo_inicial} filas")

    # ---------------------------------------------------------
    # 2. LIMPIEZA Y TRANSFORMACIÓN
    # ---------------------------------------------------------
    print("\n[2/5] Limpiando y transformando datos...")

    col_fecha = next((c for c in df_raw.columns if any(kw in c.lower() for kw in ["día", "dia", "fecha"])), None) or df_raw.columns[0]
    df = df_raw.dropna(subset=[col_fecha]).copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=[col_fecha])

    col_op = next((c for c in df.columns if any(kw in c.lower() for kw in ["operar", "operad"])), "Operario")
    col_maq = next((c for c in df.columns if any(kw in c.lower() for kw in ["máquina", "maquina", "linea"])), "Maquina")
    col_ref = next((c for c in df.columns if any(kw in c.lower() for kw in ["referencia", "producto"])), "Referencia")

    df[col_op] = df[col_op].astype(str).str.strip().str.title()
    df[col_ref] = df[col_ref].astype(str).str.strip()
    df[col_maq] = df[col_maq].astype(str).str.strip()

    col_horas = next((c for c in df.columns if "horas" in c.lower()), None)
    col_meta = next((c for c in df.columns if "meta" in c.lower()), None)
    col_pacas = next((c for c in df.columns if "pacas" in c.lower() or "producidas" in c.lower()), None)
    col_turno = next((c for c in df.columns if "turno" in c.lower()), None)

    df["Horas trabajadas"] = pd.to_numeric(df[col_horas], errors="coerce").fillna(0) if col_horas else 0
    df["Meta por hora"] = pd.to_numeric(df[col_meta], errors="coerce").fillna(0) if col_meta else 0
    df["Pacas producidas"] = pd.to_numeric(df[col_pacas], errors="coerce").fillna(0) if col_pacas else 0
    df["Turno"] = pd.to_numeric(df[col_turno], errors="coerce").fillna(1).astype(int) if col_turno else 1

    conteo_final = len(df)
    print(f"-> Registros limpios tras depuración: {conteo_final} filas")

    # ---------------------------------------------------------
    # 3. CARGAR TABLAS DE DIMENSIONES (IDEMPOTENTE)
    # ---------------------------------------------------------
    print("\n[3/5] Procesando y poblando Tablas de Dimensiones...")

    with engine.begin() as conn:
        # A. DIM_TIEMPO
        print(" -> Procesando dim_tiempo...")
        df_tiempo = pd.DataFrame()
        df_tiempo["fecha"] = df[col_fecha].dt.date
        df_tiempo["anio"] = df[col_fecha].dt.year
        df_tiempo["mes"] = df[col_fecha].dt.month

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        df_tiempo["nombre_mes"] = df_tiempo["mes"].map(meses_es)
        df_tiempo["dia"] = df[col_fecha].dt.day
        df_tiempo["turno"] = df["Turno"]
        df_tiempo["hora"] = df[col_fecha].dt.hour

        df_tiempo["fecha_key"] = (
            df_tiempo["anio"].astype(str)
            + df_tiempo["mes"].astype(str).str.zfill(2)
            + df_tiempo["dia"].astype(str).str.zfill(2)
            + df_tiempo["hora"].astype(str).str.zfill(2)
        ).astype(int)

        dim_tiempo = df_tiempo.drop_duplicates(subset=["fecha_key"]).copy()
        
        # Inserción segura idempotente para dim_tiempo
        for _, r in dim_tiempo.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dim_tiempo (fecha_key, fecha, anio, mes, nombre_mes, dia, turno, hora)
                    VALUES (:fecha_key, :fecha, :anio, :mes, :nombre_mes, :dia, :turno, :hora)
                    ON CONFLICT (fecha_key) DO NOTHING;
                """),
                r.to_dict()
            )

        # B. DIM_MAQUINA
        print(" -> Procesando dim_maquina...")
        for maq in df[col_maq].unique():
            conn.execute(
                text("INSERT INTO dim_maquina (codigo_linea, nombre_linea) VALUES (:linea, :nombre) ON CONFLICT (codigo_linea) DO NOTHING;"),
                {"linea": maq, "nombre": f"Línea de Envasado {maq}"}
            )

        # C. DIM_OPERARIO
        print(" -> Procesando dim_operario...")
        for i, op in enumerate(df[col_op].unique(), start=1):
            conn.execute(
                text("""
                    INSERT INTO dim_operario (codigo_operario, nombre_operario, fecha_inicio, activo) 
                    VALUES (:codigo, :nombre, '2024-01-01', TRUE)
                    ON CONFLICT DO NOTHING;
                """),
                {"codigo": f"OP-{i:03d}", "nombre": op}
            )

        # D. DIM_PRODUCTO
        print(" -> Procesando dim_producto...")
        for prod in df[col_ref].unique():
            capacidad = re.findall(r"\d+", str(prod))
            cap_val = int(capacidad[0]) if capacidad else None
            color_val = str(prod).split()[0] if str(prod) else "Estándar"

            conn.execute(
                text("""
                    INSERT INTO dim_producto (referencia, color, capacidad_cc) 
                    VALUES (:ref, :color, :cap) ON CONFLICT (referencia) DO NOTHING;
                """),
                {"ref": str(prod), "color": color_val, "cap": cap_val}
            )

        # E. DIM_CODIGO_PARO
        print(" -> Procesando dim_codigo_paro...")
        codigos_base = [
            ("01", "Falla del sistema electromecánico y/o de control"),
            ("02", "Espera de soporte de mantenimiento"),
            ("03", "Novedad en los sistemas de potencia (Aire, energía, vapor)"),
            ("04", "Mantenimiento preventivo"),
            ("05", "Ajuste operativo"),
            ("06", "Limpieza por derrame operativo"),
            ("07", "Alistamiento de máquina / Cambio de referencia"),
            ("08", "Capacitación / Reunión"),
            ("09", "Falta de operario"),
            ("10", "Paro por ventaja / Evacuación"),
            ("11", "Reproceso"),
            ("12", "Materia prima defectuosa"),
            ("13", "En espera por el aval del laboratorio de microbiología"),
            ("14", "Falta de materia prima"),
            ("15", "Cambio de insumos (Roscadores, O'ring, Etiquetas)"),
            ("16", "Aprovisionamiento y aseo de la zona de trabajo y la máquina"),
            ("17", "Pausa activa"),
            ("18", "Desinfección")
        ]
        for cod, desc in codigos_base:
            conn.execute(
                text("""
                    INSERT INTO dim_codigo_paro (codigo_general, descripcion_general) 
                    VALUES (:cod, :desc) ON CONFLICT DO NOTHING;
                """),
                {"cod": f"[{cod}]", "desc": desc}
            )

    # ---------------------------------------------------------
    # 4. CARGAR TABLAS DE HECHOS
    # ---------------------------------------------------------
    print("\n[4/5] Cargando Tablas de Hechos...")

    dim_maquina_db = pd.read_sql("SELECT maquina_key, codigo_linea FROM dim_maquina", engine)
    dim_operario_db = pd.read_sql("SELECT operario_key, nombre_operario FROM dim_operario WHERE activo = TRUE", engine)
    dim_producto_db = pd.read_sql("SELECT producto_key, referencia FROM dim_producto", engine)
    dim_paro_db = pd.read_sql("SELECT codigo_paro_key, codigo_general FROM dim_codigo_paro", engine)

    df["fecha_key"] = (
        df[col_fecha].dt.year.astype(str)
        + df[col_fecha].dt.month.astype(str).str.zfill(2)
        + df[col_fecha].dt.day.astype(str).str.zfill(2)
        + df[col_fecha].dt.hour.astype(str).str.zfill(2)
    ).astype(int)

    # A. FACT_PRODUCCION_HORA
    fact_prod = (
        df.merge(dim_maquina_db, left_on=col_maq, right_on="codigo_linea")
        .merge(dim_operario_db, left_on=col_op, right_on="nombre_operario")
        .merge(dim_producto_db, left_on=col_ref, right_on="referencia")
    )

    fact_prod_clean = pd.DataFrame({
        "fecha_key": fact_prod["fecha_key"],
        "maquina_key": fact_prod["maquina_key"],
        "operario_key": fact_prod["operario_key"],
        "producto_key": fact_prod["producto_key"],
        "horas_trabajadas": fact_prod["Horas trabajadas"],
        "meta_pacas_hora": fact_prod["Meta por hora"],
        "pacas_producidas": fact_prod["Pacas producidas"]
    }).drop_duplicates(subset=["fecha_key", "maquina_key", "operario_key", "producto_key"])

    # Limpiar e insertar produccion de forma limpia
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_produccion_hora RESTART IDENTITY CASCADE;"))
    fact_prod_clean.to_sql("fact_produccion_hora", engine, if_exists="append", index=False)
    print(f" -> Cargas exitosas en fact_produccion_hora: {len(fact_prod_clean)} filas.")

    # B. FACT_PAROS
    cols_paros = [c for c in df.columns if "cod" in c.lower()]
    col_obs = next((c for c in df.columns if "observa" in c.lower()), None)

    if cols_paros:
        id_vars = ["fecha_key", col_maq, col_op]
        if col_obs:
            id_vars.append(col_obs)

        df_paros_melt = df.melt(
            id_vars=id_vars,
            value_vars=cols_paros,
            var_name="codigo_excel",
            value_name="tiempo_paro_minutos"
        )

        df_paros_melt["tiempo_paro_minutos"] = pd.to_numeric(df_paros_melt["tiempo_paro_minutos"], errors="coerce").fillna(0)
        df_paros_melt = df_paros_melt[df_paros_melt["tiempo_paro_minutos"] > 0].copy()

        df_paros_melt["codigo_general"] = df_paros_melt["codigo_excel"].str.extract(r"(\[\d+\]|\d+)")
        df_paros_melt["codigo_general"] = df_paros_melt["codigo_general"].apply(
            lambda x: f"[{str(x).zfill(2)}]" if not str(x).startswith("[") else x
        )

        fact_paros = (
            df_paros_melt.merge(dim_maquina_db, left_on=col_maq, right_on="codigo_linea")
            .merge(dim_operario_db, left_on=col_op, right_on="nombre_operario")
            .merge(dim_paro_db, left_on="codigo_general", right_on="codigo_general")
        )

        fact_paros_clean = pd.DataFrame({
            "fecha_key": fact_paros["fecha_key"],
            "maquina_key": fact_paros["maquina_key"],
            "operario_key": fact_paros["operario_key"],
            "codigo_paro_key": fact_paros["codigo_paro_key"],
            "tiempo_paro_minutos": fact_paros["tiempo_paro_minutos"],
            "observacion": fact_paros[col_obs] if col_obs else None
        })

        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE fact_paros RESTART IDENTITY CASCADE;"))
        fact_paros_clean.to_sql("fact_paros", engine, if_exists="append", index=False)
        print(f" -> Cargas exitosas en fact_paros: {len(fact_paros_clean)} eventos de paro.")

    # ---------------------------------------------------------
    # 5. CONCILIACIÓN DE TOTALES
    # ---------------------------------------------------------
    print("\n[5/5] Conciliando totales contra la fuente (Excel vs PostgreSQL)...")
    total_pacas_excel = df["Pacas producidas"].sum()

    with engine.connect() as conn:
        total_pacas_pg = conn.execute(text("SELECT SUM(pacas_producidas) FROM fact_produccion_hora")).scalar() or 0

    print(f"-> Total Pacas en Excel:      {total_pacas_excel:,.2f}")
    print(f"-> Total Pacas en PostgreSQL: {total_pacas_pg:,.2f}")

    if abs(total_pacas_excel - total_pacas_pg) < 0.01:
        print("\n ¡CONCILIACIÓN EXITOSA! Los datos cargados coinciden al 100%.")
    else:
        print("\n ADVERTENCIA: Existen diferencias por descarte de registros nulos en la fuente.")


if __name__ == "__main__":
    ejecutar_etl()
