import pandas as pd
from datetime import datetime
import os
import sqlite3
import streamlit as st

def conectar_db():
    """Conecta directamente a Turso en la nube."""
    turso_url = st.secrets["TURSO_URL"]
    turso_token = st.secrets["TURSO_AUTH_TOKEN"]
    import libsql
    conn = libsql.connect(turso_url, auth_token=turso_token)
    st.sidebar.success("Conectado a Turso (Nube) ☁️")
    return conn

def inicializar_tablas():
    """Crea las tablas necesarias en Turso o SQLite si no existen."""
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Tabla de Catálogo
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
    
    # Tabla de Ventas
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
    
    # Tabla de Clientes Recurrentes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes_recurrentes (
            Cliente TEXT PRIMARY KEY
        );
    """)
    
    conn.commit()
    conn.close()

# Inicializar tablas al cargar el módulo
inicializar_tablas()

# Definición de archivos y variables de respaldo
CATALOGO_FILE = "catalogo_productos.csv"
CLIENTES_RECURRENTES_FILE = "clientes_recurrentes.csv"
HISTORIAL_COSTOS_FILE = "historial_costos.csv"
VENTAS_FILE = "registro_ventas.csv"
COMPRAS_FILE = "compras.csv"

def limpiar_y_preparar_catalogo(df):
    df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False, na=False)]
    return df

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
    """Obtiene el catálogo directamente desde la base de datos."""
    conn = conectar_db()
    try:
        df = pd.read_sql("SELECT * FROM catalogo_productos", conn)
        conn.close()
        if df.empty:
            df = cargar_catalogo_defecto()
            guardar_catalogo_db(df)
        return df
    except Exception:
        conn.close()
        return cargar_catalogo_defecto()

def guardar_catalogo_db(df):
    conn = conectar_db()
    df.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
    conn.close()

def obtener_clientes_recurrentes_lista():
    conn = conectar_db()
    try:
        df_cr = pd.read_sql("SELECT Cliente FROM clientes_recurrentes", conn)
        conn.close()
        return [c.strip() for c in df_cr["Cliente"].dropna().unique().tolist() if c.strip()]
    except Exception:
        conn.close()
        return []

def guardar_cliente_recurrente(nuevo_cliente):
    cliente_clean = nuevo_cliente.strip()
    if not cliente_clean:
        return False
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO clientes_recurrentes (Cliente) VALUES (?);", (cliente_clean,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def eliminar_cliente_recurrente(cliente_eliminar):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM clientes_recurrentes WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_eliminar.strip(),))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def guardar_venta_db(df_ventas):
    """Guarda los registros de venta directamente en la tabla de Turso."""
    conn = conectar_db()
    try:
        df_ventas.to_sql("registro_ventas", conn, if_exists="append", index=False)
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def obtener_historial_ventas():
    """Obtiene todas las ventas desde Turso para cálculos de cliente."""
    conn = conectar_db()
    try:
        df = pd.read_sql("SELECT * FROM registro_ventas", conn)
        conn.close()
        return df
    except Exception:
        conn.close()
        return pd.DataFrame()
