import streamlit as st
import pandas as pd

# Importar funciones desde la carpeta modulos
from modulos.base_datos import obtener_catalogo, CATALOGO_FILE, HISTORIAL_COSTOS_FILE, VENTAS_FILE, COMPRAS_FILE, limpiar_y_preparar_catalogo, registrar_en_historial
from modulos.usuarios_db import inicializar_usuario_admin_por_defecto, verificar_credenciales

# Importar módulos de secciones
from modulos import catalogo, ventas, devoluciones, compras, reportes, clientes_historial, clientes_recurrentes, gestion_usuarios

st.set_page_config(page_title="Sistema de Ventas - Textil", layout="wide")

# Asegurar usuario admin inicial
inicializar_usuario_admin_por_defecto()

# --- ESTADO DE SESIÓN EN STREAMLIT ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = ""
    st.session_state.sucursal = ""

# --- PANTALLA DE ACCESO (SI NO HA INICIADO SESIÓN) ---
if not st.session_state.autenticado:
    st.title("🔒 Sistema de Control Textil")
    st.subheader("Acceso Restringido a Personal Autorizado")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.write("Por favor, ingresa tus credenciales:")
            input_user = st.text_input("Usuario").strip()
            input_pass = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Iniciar Sesión", type="primary")

            if submit_login:
                rol_verificado, sucursal_verificada = verificar_credenciales(input_user, input_pass)
                if rol_verificado:
                    st.session_state.autenticado = True
                    st.session_state.usuario = input_user
                    st.session_state.rol = rol_verificado
                    st.session_state.sucursal = sucursal_verificada
                    st.success("¡Acceso concedido!")
                    st.rerun()
                else:
                    st.error("Usuario, contraseña incorrectos o cuenta desactivada.")
    
    # Detenemos la ejecución aquí para que nadie vea nada más
    st.stop()

# =========================================================================
# A PARTIR DE AQUÍ, SOLO SE MUESTRA EL SISTEMA SI YA INICIÓ SESIÓN
# =========================================================================

usuario_actual = st.session_state.usuario
rol_usuario = st.session_state.rol
sucursal_usuario = st.session_state.sucursal
acceso_propietaria = (rol_usuario == "Propietaria (Dueña)")

# --- SIDEBAR: MENÚ Y CONFIGURACIÓN ---
st.sidebar.title("📌 Menú Principal")
st.sidebar.success(f"👤 Sesión: {usuario_actual}\n📍 Sucursal: {sucursal_usuario}\n🛡️ Rol: {rol_usuario}")

if st.sidebar.button("🚪 Cerrar Sesión", type="secondary"):
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = ""
    st.session_state.sucursal = ""
    st.rerun()

st.sidebar.divider()

# Selector de sucursal activa para la operación
SUCURSALES_DISPONIBLES = ["Tienda Chela", "Tienda Santa Ana", "Tienda Ixcotla"]

if acceso_propietaria:
    st.sidebar.subheader("🏪 Sucursal Activa (Dueña)")
    sucursal_activa = st.sidebar.selectbox("Selecciona sucursal de trabajo:", SUCURSALES_DISPONIBLES)
    
    opciones_disponibles = [
        "📦 Catálogo y Excel", 
        "🛒 Registrar Venta", 
        "🔄 Registrar Devolución",
        "📥 Registrar Compra / Proveedor", 
        "📊 Reportes y Deudas",
        "👥 Historial por Cliente",
        "⭐ Gestión Clientes Recurrentes",
        "👥 Gestión de Usuarios"
    ]
else:
    # Si es empleado, opera estrictamente en su sucursal asignada
    sucursal_activa = sucursal_usuario if sucursal_usuario in SUCURSALES_DISPONIBLES else "Tienda Chela"
    st.sidebar.info(f"📍 Operando en: **{sucursal_activa}**")
    
    opciones_disponibles = [
        "📦 Catálogo y Excel", 
        "🛒 Registrar Venta", 
        "🔄 Registrar Devolución"
    ]

opcion_menu = st.sidebar.radio("Selecciona una sección:", opciones_disponibles)

st.sidebar.divider()
st.sidebar.header("⚙️ Umbrales de Mayoreo ($)")

if acceso_propietaria:
    monto_mayoreo_1 = st.sidebar.number_input("Mayoreo 1 desde:", value=1000.0, step=100.0)
    monto_mayoreo_2 = st.sidebar.number_input("Mayoreo 2 desde:", value=2500.0, step=100.0)
    monto_especial = st.sidebar.number_input("Precio Especial desde:", value=5000.0, step=100.0)
    st.sidebar.success("🔓 Umbrales editables")
else:
    monto_mayoreo_1 = 1000.0
    monto_mayoreo_2 = 2500.0
    monto_especial = 5000.0
    st.sidebar.info(f"🔒 Umbrales actuales:\n- M1: ${monto_mayoreo_1:,.0f}\n- M2: ${monto_mayoreo_2:,.0f}\n- Esp:${monto_especial:,.0f}")

# Cargar catálogo actual
df_catalogo = obtener_catalogo()

# --- ENRUTAMIENTO A MÓDULOS ---
if opcion_menu == "📦 Catálogo y Excel":
    catalogo.mostrar(df_catalogo, acceso_propietaria)

elif opcion_menu == "🛒 Registrar Venta":
    ventas.mostrar(df_catalogo, monto_mayoreo_1, monto_mayoreo_2, monto_especial, sucursal_activa)

elif opcion_menu == "🔄 Registrar Devolución":
    devoluciones.mostrar()

elif opcion_menu == "📥 Registrar Compra / Proveedor":
    compras.mostrar(df_catalogo, acceso_propietaria)

elif opcion_menu == "📊 Reportes y Deudas":
    reportes.mostrar(df_catalogo, acceso_propietaria)

elif opcion_menu == "👥 Historial por Cliente":
    clientes_historial.mostrar(acceso_propietaria)

elif opcion_menu == "⭐ Gestión Clientes Recurrentes":
    clientes_recurrentes.mostrar(acceso_propietaria)

elif opcion_menu == "👥 Gestión de Usuarios":
    if acceso_propietaria:
        gestion_usuarios.mostrar()
    else:
        st.warning("Acceso restringido.")
