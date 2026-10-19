import sqlite3
import hashlib

DB_USUARIOS = "usuarios_sistema.db"

def conectar_usuarios():
    conn = sqlite3.connect(DB_USUARIOS)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            sucursal TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def inicializar_usuario_admin_por_defecto():
    """Crea un usuario administrador por defecto si la tabla está vacía."""
    conn = conectar_usuarios()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        pass_default = hash_password("1234")
        # Por defecto el admin pertenece a Tienda Chela pero como dueña tiene acceso global
        cursor.execute("INSERT INTO usuarios (username, password, rol, sucursal, activo) VALUES (?, ?, ?, ?, 1)",
                       ("admin", pass_default, "Propietaria (Dueña)", "Tienda Chela"))
        conn.commit()
    conn.close()

def verificar_credenciales(username, password):
    conn = conectar_usuarios()
    cursor = conn.cursor()
    pass_enc = hash_password(password)
    cursor.execute("SELECT rol, sucursal, activo FROM usuarios WHERE username = ? AND password = ?", (username, pass_enc))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        rol, sucursal, activo = resultado
        if activo == 1:
            return rol, sucursal  # <-- Asegúrate de que devuelva solo estos dos valores
            
    return None, None  # <-- Y aquí también dos valores nulos