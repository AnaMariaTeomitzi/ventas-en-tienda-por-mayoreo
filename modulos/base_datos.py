import pandas as pd
from datetime import datetime
import os
import streamlit as st
import libsql_client

def conectar_db():
    """Crea un cliente síncrono de Turso usando libsql-client de forma segura."""
    try:
        turso_url = st.secrets["TURSO_URL"]
        turso_token = st.secrets["TURSO_AUTH_TOKEN"]
        url_http = turso_url.replace("libsql://", "https://")
        client = libsql_client.create_client_sync(url=url_http, auth_token=turso_token)
        return client
    except Exception as e:
        st.sidebar.warning(f"Modo local por red: {e}")
        return None
        
def inicializar_tablas():
    """Crea las tablas necesarias en Turso si no existen."""
    client = conectar_db()
    if not client:
        return
    try:
        client.execute("""
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
        
        client.execute("""
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
        
        client.execute("""
            CREATE TABLE IF NOT EXISTS clientes_recurrentes (
                Cliente TEXT PRIMARY KEY
            );
        """)
    except Exception as e:
        st.error(f"Error al inicializar tablas: {e}")
    finally:
        client.close()

# Inicializar tablas al cargar el módulo
#inicializar_tablas()

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
    """Obtiene el catálogo directamente desde Turso."""
    client = conectar_db()
    if not client:
        return cargar_catalogo_defecto()
    try:
        rs = client.execute("SELECT * FROM catalogo_productos;")
        client.close()
        rows = rs.rows
        if not rows:
            df = cargar_catalogo_defecto()
            guardar_catalogo_db(df)
            return df
        # Convertir a DataFrame de Pandas usando los nombres de columnas
        columns = rs.columns
        df = pd.DataFrame(rows, columns=columns)
        return df
    except Exception:
        if client:
            client.close()
        return cargar_catalogo_defecto()

def guardar_catalogo_db(df):
    client = conectar_db()
    if not client:
        return
    try:
        # Reemplazar catálogo: borramos y reinsertamos
        client.execute("DELETE FROM catalogo_productos;")
        for _, row in df.iterrows():
            client.execute(
                "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (str(row["SKU"]), str(row["Producto"]), float(row["Costo"]), float(row["Precio_Menudeo"]), float(row["Precio_Mayoreo_1"]), float(row["Precio_Mayoreo_2"]), float(row["Precio_Especial"]), int(row["Stock"]))
            )
    except Exception as e:
        st.error(f"Error al guardar catálogo: {e}")
    finally:
        client.close()

def obtener_clientes_recurrentes_lista():
    client = conectar_db()
    if not client:
        return []
    try:
        rs = client.execute("SELECT Cliente FROM clientes_recurrentes;")
        client.close()
        return [str(row[0]).strip() for row in rs.rows if row[0] and str(row[0]).strip()]
    except Exception:
        if client:
            client.close()
        return []

def guardar_cliente_recurrente(nuevo_cliente):
    cliente_clean = nuevo_cliente.strip()
    if not cliente_clean:
        return False
    client = conectar_db()
    if not client:
        return False
    try:
        client.execute("INSERT OR IGNORE INTO clientes_recurrentes (Cliente) VALUES (?);", (cliente_clean,))
        client.close()
        return True
    except Exception:
        if client:
            client.close()
        return False

def eliminar_cliente_recurrente(cliente_eliminar):
    client = conectar_db()
    if not client:
        return False
    try:
        client.execute("DELETE FROM clientes_recurrentes WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_eliminar.strip(),))
        client.close()
        return True
    except Exception:
        if client:
            client.close()
        return False

def guardar_venta_db(df_ventas):
    """Guarda los registros de venta en Turso."""
    client = conectar_db()
    if not client:
        return False
    try:
        for _, row in df_ventas.iterrows():
            client.execute(
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
        client.close()
        return True
    except Exception as e:
        if client:
            client.close()
        st.error(f"Error al guardar venta: {e}")
        return False

def obtener_historial_ventas():
    """Obtiene todas las ventas desde Turso."""
    client = conectar_db()
    if not client:
        return pd.DataFrame()
    try:
        rs = client.execute("SELECT * FROM registro_ventas;")
        client.close()
        rows = rs.rows
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows, columns=rs.columns)
    except Exception:
        if client:
            client.close()
        return pd.DataFrame()
