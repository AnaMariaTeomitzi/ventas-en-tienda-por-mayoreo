import hashlib
import streamlit as st
from .base_datos import conectar_db

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def inicializar_usuario_admin_por_defecto():
    """Crea un usuario administrador por defecto si la tabla está vacía en Turso."""
    tipo, conn = conectar_db()
    pass_default = hash_password("1234")
    
    try:
        if tipo == "turso":
            # Asegurar que la tabla exista
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    sucursal TEXT NOT NULL,
                    activo INTEGER DEFAULT 1
                );
            """)
            rs = conn.execute("SELECT COUNT(*) FROM usuarios;")
            count = rs.rows[0][0] if rs.rows else 0
            if count == 0:
                conn.execute(
                    "INSERT INTO usuarios (username, password, rol, sucursal, activo) VALUES (?, ?, ?, ?, 1)",
                    ("admin", pass_default, "Propietaria (Dueña)", "Tienda Chela")
                )
        else:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    sucursal TEXT NOT NULL,
                    activo INTEGER DEFAULT 1
                );
            """)
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO usuarios (username, password, rol, sucursal, activo) VALUES (?, ?, ?, ?, 1)",
                    ("admin", pass_default, "Propietaria (Dueña)", "Tienda Chela")
                )
                conn.commit()
    except Exception as e:
        st.error(f"Error al inicializar admin por defecto: {e}")

def verificar_credenciales(username, password):
    tipo, conn = conectar_db()
    pass_enc = hash_password(password)
    
    try:
        if tipo == "turso":
            # Usamos LOWER(username) para evitar problemas con mayúsculas/minúsculas
            rs = conn.execute(
                "SELECT rol, sucursal, activo FROM usuarios WHERE LOWER(username) = LOWER(?) AND password = ?",
                (username.strip(), pass_enc)
            )
            rows = rs.rows
            if rows:
                rol, sucursal, activo = rows[0]
                if int(activo) == 1:
                    return rol, sucursal
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rol, sucursal, activo FROM usuarios WHERE LOWER(username) = LOWER(?) AND password = ?",
                (username.strip(), pass_enc)
            )
            resultado = cursor.fetchone()
            if resultado:
                rol, sucursal, activo = resultado
                if int(activo) == 1:
                    return rol, sucursal
    except Exception as e:
        st.error(f"Error al verificar credenciales: {e}")
    
    return None, None
