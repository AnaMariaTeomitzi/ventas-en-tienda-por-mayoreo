import pandas as pd
from datetime import datetime
import os
import sqlite3

import streamlit as st

def conectar_db():
    """Conecta a Turso si estamos en la nube, o usa SQLite local si estás en tu PC."""
    try:
        # Intenta leer las credenciales seguras de Streamlit Secrets (en la nube)
        turso_url = st.secrets["TURSO_URL"]
        turso_token = st.secrets["TURSO_AUTH_TOKEN"]
        
        # Conexión remota para la nube
        import libsql
        conn = libsql.connect(turso_url, auth_token=turso_token)
        return conn
    except:
        # Si estás en tu PC local (donde no hay secrets configurados), usa tu SQLite local de respaldo
        conn = sqlite3.connect("textiles_local.db")
        return conn
# Definición de archivos
CATALOGO_FILE = "catalogo_productos.csv"
HISTORIAL_COSTOS_FILE = "historial_costos.csv"
VENTAS_FILE = "registro_ventas.csv"
COMPRAS_FILE = "registro_compras.csv"
CLIENTES_RECURRENTES_FILE = "clientes_recurrentes.csv"

def limpiar_y_preparar_catalogo(df):
    df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False, na=False)]
    
    def limpiar_columna_numerica(serie):
        if serie.dtype == object:
            serie = serie.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
        return pd.to_numeric(serie, errors='coerce').fillna(0.0)

    if 'SKU' not in df.columns and 'sku' not in [str(c).lower() for c in df.columns]:
        df.insert(0, 'SKU', [f"PROD{i+1:02d}" for i in range(len(df))])

    num_cols = df.shape[1]
    df.rename(columns={df.columns[1]: 'Producto'}, inplace=True)

    if num_cols > 2:
        df.rename(columns={df.columns[2]: 'Costo'}, inplace=True)
        df['Costo'] = limpiar_columna_numerica(df['Costo'])
    else:
        df['Costo'] = 0.0

    if num_cols > 3:
        df.rename(columns={df.columns[3]: 'Precio_Menudeo'}, inplace=True)
        df['Precio_Menudeo'] = limpiar_columna_numerica(df['Precio_Menudeo'])
    else:
        df['Precio_Menudeo'] = df['Costo']

    if num_cols > 4:
        df.rename(columns={df.columns[4]: 'Precio_Mayoreo_1'}, inplace=True)
        df['Precio_Mayoreo_1'] = limpiar_columna_numerica(df['Precio_Mayoreo_1'])
    else:
        df['Precio_Mayoreo_1'] = df['Precio_Menudeo']

    df['Precio_Mayoreo_2'] = df['Precio_Mayoreo_1']

    if num_cols > 5:
        df.rename(columns={df.columns[5]: 'Precio_Especial'}, inplace=True)
        df['Precio_Especial'] = limpiar_columna_numerica(df['Precio_Especial'])
        df['Precio_Especial'] = df['Precio_Especial'].apply(lambda x: 0.0 if x <= 0 else x)
    else:
        df['Precio_Especial'] = 0.0

    df['Stock'] = 100
    return df

def registrar_en_historial(df):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_copia = df.copy()
    df_copia["Fecha_Actualizacion"] = ahora
    cols_hist = [c for c in ["Fecha_Actualizacion", "SKU", "Producto", "Costo", "Precio_Menudeo", "Precio_Mayoreo_1", "Precio_Mayoreo_2", "Precio_Especial"] if c in df_copia.columns]
    df_historico_nuevo = df_copia[cols_hist]
    
    if os.path.exists(HISTORIAL_COSTOS_FILE):
        df_historico_nuevo.to_csv(HISTORIAL_COSTOS_FILE, mode='a', header=False, index=False)
    else:
        df_historico_nuevo.to_csv(HISTORIAL_COSTOS_FILE, index=False)

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
    if os.path.exists(CATALOGO_FILE):
        try:
            df = pd.read_csv(CATALOGO_FILE)
            return limpiar_y_preparar_catalogo(df)
        except:
            df = cargar_catalogo_defecto()
            df.to_csv(CATALOGO_FILE, index=False)
            return df
    else:
        df = cargar_catalogo_defecto()
        df.to_csv(CATALOGO_FILE, index=False)
        return df

def obtener_clientes_recurrentes_lista():
    if os.path.exists(CLIENTES_RECURRENTES_FILE):
        try:
            df_cr = pd.read_csv(CLIENTES_RECURRENTES_FILE)
            return [c.strip() for c in df_cr["Cliente"].dropna().unique().tolist() if c.strip()]
        except:
            return []
    return []

def guardar_cliente_recurrente(nuevo_cliente):
    cliente_clean = nuevo_cliente.strip()
    if not cliente_clean:
        return False
    lista_actual = []
    if os.path.exists(CLIENTES_RECURRENTES_FILE):
        try:
            df_cr = pd.read_csv(CLIENTES_RECURRENTES_FILE)
            lista_actual = df_cr["Cliente"].tolist()
        except:
            lista_actual = []
    if cliente_clean.lower() not in [c.lower() for c in lista_actual]:
        lista_actual.append(cliente_clean)
        pd.DataFrame({"Cliente": lista_actual}).to_csv(CLIENTES_RECURRENTES_FILE, index=False)
        return True
    return False

def eliminar_cliente_recurrente(cliente_eliminar):
    if os.path.exists(CLIENTES_RECURRENTES_FILE):
        try:
            df_cr = pd.read_csv(CLIENTES_RECURRENTES_FILE)
            df_cr = df_cr[df_cr["Cliente"].astype(str).str.strip().str.lower() != cliente_eliminar.strip().lower()]
            df_cr.to_csv(CLIENTES_RECURRENTES_FILE, index=False)
            return True
        except:
            return False
    return False