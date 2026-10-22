import pandas as pd
from datetime import datetime
import os
import sqlite3
import streamlit as st

@st.cache_resource
def conectar_db():
    """Conecta a Turso de forma segura; si falla o la red tarda, usa SQLite local."""
    try:
        import libsql_client
        turso_url = st.secrets.get("TURSO_URL", "")
        turso_token = st.secrets.get("TURSO_AUTH_TOKEN", "")
        
        if turso_url and turso_token:
            url_http = turso_url.replace("libsql://", "https://")
            client = libsql_client.create_client_sync(url=url_http, auth_token=turso_token)
            return ("turso", client)
    except Exception as e:
        st.warning(f"Aviso: No se pudo conectar a Turso ({e}), usando base de datos local SQLite.")
    
    conn = sqlite3.connect("textiles_local.db", check_same_thread=False)
    return ("sqlite", conn)

def inicializar_tablas():
    """Crea las tablas necesarias de manera perezosa sin bloquear el arranque."""
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            conn.execute("""
                CREATE TABLE IF NOT EXISTS catalogo_productos (
                    SKU TEXT PRIMARY KEY,
                    Producto TEXT,
                    Costo REAL,
                    Precio_Menudeo REAL,
                    Precio_Mayoreo_1 REAL,
                    Precio_Mayoreo_2 REAL,
                    Precio_Especial REAL,
                    Stock INTEGER
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS registro_ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Fecha TEXT,
                    Sucursal TEXT,
                    Cliente TEXT,
                    SKU TEXT,
                    Producto TEXT,
                    Nivel_Precio TEXT,
                    Precio_Unitario REAL,
                    Costo_Unitario REAL,
                    Cantidad REAL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clientes_recurrentes (
                    Cliente TEXT PRIMARY KEY
                );
            """)
        else:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS catalogo_productos (
                    SKU TEXT PRIMARY KEY,
                    Producto TEXT,
                    Costo REAL,
                    Precio_Menudeo REAL,
                    Precio_Mayoreo_1 REAL,
                    Precio_Mayoreo_2 REAL,
                    Precio_Especial REAL,
                    Stock INTEGER
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registro_ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Fecha TEXT,
                    Sucursal TEXT,
                    Cliente TEXT,
                    SKU TEXT,
                    Producto TEXT,
                    Nivel_Precio TEXT,
                    Precio_Unitario REAL,
                    Costo_Unitario REAL,
                    Cantidad REAL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes_recurrentes (
                    Cliente TEXT PRIMARY KEY
                );
            """)
            conn.commit()
    except Exception as e:
        st.error(f"Error al inicializar tablas: {e}")

# Definición de archivos y variables de respaldo
CATALOGO_FILE = "catalogo_productos.csv"
CLIENTES_RECURRENTES_FILE = "clientes_recurrentes.csv"
HISTORIAL_COSTOS_FILE = "historial_costos.csv"
VENTAS_FILE = "registro_ventas.csv"
COMPRAS_FILE = "compras.csv"

def limpiar_y_preparar_catalogo(df):
    if isinstance(df, pd.DataFrame):
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        cols_validas = [c for c in df.columns if not str(c).startswith('Unnamed')]
        df = df[cols_validas]
    
    columnas_actuales = list(df.columns)
    
    renombres = {}
    for i, col in enumerate(columnas_actuales):
        c_lower = str(col).strip().lower()
        if i == 0 or 'concepto' in c_lower or 'producto' in c_lower or 'nombre' in c_lower:
            renombres[col] = 'Producto'
        elif i == 1 or 'pr' in c_lower or 'costo' in c_lower:
            renombres[col] = 'Costo'
        elif i == 2 or 'venta' in c_lower or 'menudeo' in c_lower:
            renombres[col] = 'Precio_Menudeo'
        elif i == 3 or 'mayore' in c_lower:
            renombres[col] = 'Precio_Mayoreo_1'
        elif i == 4 or 'super' in c_lower or 'especial' in c_lower:
            renombres[col] = 'Precio_Mayoreo_2'
            
    df = df.rename(columns=renombres)
    
    if 'SKU' not in df.columns:
        df.insert(0, 'SKU', [f"P{i+1:03d}" for i in range(len(df))])

    cols_requeridas = ['SKU', 'Producto', 'Costo', 'Precio_Menudeo', 'Precio_Mayoreo_1', 'Precio_Mayoreo_2', 'Precio_Especial', 'Stock']
    for c in cols_requeridas:
        if c not in df.columns:
            if c in ['Costo', 'Precio_Menudeo', 'Precio_Mayoreo_1', 'Precio_Mayoreo_2', 'Precio_Especial']:
                df[c] = 0.0
            elif c == 'Stock':
                df[c] = 100 
            else:
                df[c] = ""

    cols_num = ['Costo', 'Precio_Menudeo', 'Precio_Mayoreo_1', 'Precio_Mayoreo_2', 'Precio_Especial']
    for col in cols_num:
        if col in df.columns:
            serie = df[col]
            if isinstance(serie, pd.DataFrame):
                serie = serie.iloc[:, 0]
            serie_limpia = serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
            df[col] = pd.to_numeric(serie_limpia, errors='coerce').fillna(0.0)

    if 'Stock' in df.columns:
        serie_stock = df['Stock']
        if isinstance(serie_stock, pd.DataFrame):
            serie_stock = serie_stock.iloc[:, 0]
        serie_stock_limpia = serie_stock.astype(str).str.replace(',', '', regex=False).str.strip()
        df['Stock'] = pd.to_numeric(serie_stock_limpia, errors='coerce').fillna(100).astype(int)
                
    df = df[cols_requeridas]
    return df


    def guardar_catalogo_db(df):
    # --- LÍNEAS DE DIAGNÓSTICO (Temporal) ---
    st.write("📋 **Columnas detectadas:**", list(df.columns))
    st.write("🔍 **Primeras 3 filas:**", df.head(3))
    # ----------------------------------------
    tipo, conn = conectar_db()
    try:
        if df is None or getattr(df, 'empty', True):
            st.error("El archivo Excel está vacío o no se pudo leer.")
            return False
            
        df = limpiar_y_preparar_catalogo(df)
        
        def to_scalar(val, default=0.0, is_int=False):
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            try:
                num = pd.to_numeric(val, errors='coerce')
                if pd.isna(num):
                    return default
                return int(num) if is_int else float(num)
            except Exception:
                return str(val) if default == "" else default

        sku_col = df["SKU"]
        if isinstance(sku_col, pd.DataFrame):
            sku_col = sku_col.iloc[:, 0]
            
        sku_limpio = sku_col.astype(str).str.strip()
        sku_limpio = sku_limpio.apply(lambda x: x[:-2] if x.endswith('.0') else x)
        df["SKU"] = sku_limpio
        
        mask = (df["SKU"] != "") & (df["SKU"].str.lower() != "nan") & (df["SKU"].notna())
        df = df[mask]
        
        if df.empty:
            st.error("El archivo no contiene productos con un SKU válido para guardar.")
            return False

        if tipo == "turso":
            for _, row in df.iterrows():
                sku = str(to_scalar(row.get("SKU", ""), default="")).strip()
                producto = str(to_scalar(row.get("Producto", ""), default="")).strip()
                costo = to_scalar(row.get("Costo", 0.0), default=0.0)
                p_menudeo = to_scalar(row.get("Precio_Menudeo", 0.0), default=0.0)
                p_may1 = to_scalar(row.get("Precio_Mayoreo_1", 0.0), default=0.0)
                p_may2 = to_scalar(row.get("Precio_Mayoreo_2", 0.0), default=0.0)
                p_esp = to_scalar(row.get("Precio_Especial", 0.0), default=0.0)
                stock = to_scalar(row.get("Stock", 100), default=100, is_int=True)

                conn.execute(
                    "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    (sku, producto, costo, p_menudeo, p_may1, p_may2, p_esp, stock)
                )
        else:
            df.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
            
        # Limpiar la caché de Streamlit para forzar la recarga inmediata de los nuevos precios
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Error al guardar catálogo en la base de datos: {e}")
        return False
def limpiar_columna_numerica(serie):
    if isinstance(serie, pd.DataFrame):
        serie = serie.iloc[:, 0]
    if hasattr(serie, 'dtype') and serie.dtype == object:
        serie = serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
    return pd.to_numeric(serie, errors='coerce').fillna(0.0)

def registrar_en_historial(df):
    pass

def cargar_catalogo_defecto():
    datos = {
        "SKU": ["PROD01", "PROD02", "PROD03"],
        "Producto": ["Juego de Sábanas Matrimonial", "Edredón Ligero Sabina", "Toalla Facial Sola Textil"],
        "Costo": [130.0, 240.0, 18.0],
        "Precio_Menudeo": [250.0, 450.0, 35.0],
        "Precio_Mayoreo_1": [220.0, 400.0, 30.0],
        "Precio_Mayoreo_2": [200.0, 370.0, 26.0],
        "Precio_Especial": [180.0, 340.0, 22.0],
        "Stock": [50, 30, 100]
    }
    return pd.DataFrame(datos)

def obtener_catalogo():
    inicializar_tablas()
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            rs = conn.execute("SELECT * FROM catalogo_productos;")
            rows = rs.rows
            if not rows:
                df = cargar_catalogo_defecto()
                guardar_catalogo_db(df)
                return df
            return pd.DataFrame(rows, columns=rs.columns)
        else:
            df = pd.read_sql("SELECT * FROM catalogo_productos", conn)
            if df.empty:
                df = cargar_catalogo_defecto()
                guardar_catalogo_db(df)
            return df
    except Exception as e:
        st.error(f"Error al obtener catálogo de la BD: {e}")
        return cargar_catalogo_defecto()

def obtener_clientes_recurrentes_lista():
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            rs = conn.execute("SELECT Cliente FROM clientes_recurrentes;")
            return [str(row[0]).strip() for row in rs.rows if row[0] and str(row[0]).strip()]
        else:
            df_cr = pd.read_sql("SELECT Cliente FROM clientes_recurrentes", conn)
            return [c.strip() for c in df_cr["Cliente"].dropna().unique().tolist() if c.strip()]
    except Exception:
        return []

def guardar_cliente_recurrente(nuevo_cliente):
    cliente_clean = nuevo_cliente.strip()
    if not cliente_clean:
        return False
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            conn.execute("INSERT OR IGNORE INTO clientes_recurrentes (Cliente) VALUES (?);", (cliente_clean,))
        else:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO clientes_recurrentes (Cliente) VALUES (?);", (cliente_clean,))
            conn.commit()
        return True
    except Exception:
        return False

def eliminar_cliente_recurrente(cliente_eliminar):
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            conn.execute("DELETE FROM clientes_recurrentes WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_eliminar.strip(),))
        else:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clientes_recurrentes WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_eliminar.strip(),))
            conn.commit()
        return True
    except Exception:
        return False

def guardar_venta_db(df_ventas):
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            for _, row in df_ventas.iterrows():
                conn.execute(
                    "INSERT INTO registro_ventas (Fecha, Sucursal, Cliente, SKU, Producto, Nivel_Precio, Precio_Unitario, Costo_Unitario, Cantidad) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
                    (
                        str(row.get("Fecha", "")),
                        str(row.get("Sucursal", "")),
                        str(row.get("Cliente", "")),
                        str(row.get("SKU", "")),
                        str(row.get("Producto", "")),
                        str(row.get("Nivel_Precio", "")),
                        float(row.get("Precio_Unitario", 0.0)),
                        float(row.get("Costo_Unitario", 0.0)),
                        float(row.get("Cantidad", 0.0))
                    )
                )
        else:
            df_ventas.to_sql("registro_ventas", conn, if_exists="append", index=False)
        return True
    except Exception as e:
        st.error(f"Error al guardar venta: {e}")
        return False

def obtener_historial_ventas():
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            rs = conn.execute("SELECT * FROM registro_ventas;")
            rows = rs.rows
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(rows, columns=rs.columns)
        else:
            return pd.read_sql("SELECT * FROM registro_ventas", conn)
    except Exception:
        return pd.DataFrame()
