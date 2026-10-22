import streamlit as st

def mostrar():
    st.title("⚙️ Configuración de Impresora y Hardware")
    st.info("Configura la conexión Bluetooth y el formato del ticket térmico para tus tiendas.")

    # Inicializar preferencias en session_state si no existen
    if "config_impresora" not in st.session_state:
        st.session_state.config_impresora = {
            "nombre_dispositivo": "PT-210",
            "ancho_papel": "58mm",
            "caracteres_por_linea": 32,
            "conexion": "Bluetooth Web API (ESC/POS)"
        }

    cfg = st.session_state.config_impresora

    st.markdown("### 🖨️ Parámetros de la Impresora Térmica")

    col1, col2 = st.columns(2)
    with col1:
        nombre_dev = st.text_input(
            "Nombre del Dispositivo Bluetooth:",
            value=cfg["nombre_dispositivo"],
            help="Ejemplo: PT-210, POS-58, MTP-II"
        )
        
        ancho_papel = st.selectbox(
            "Ancho de Papel:",
            ["58mm (Portátil / Goojprt)", "80mm (Mostrador / Estándar)"],
            index=0 if cfg["ancho_papel"] == "58mm" else 1
        )

    with col2:
        cpl = 32 if "58mm" in ancho_papel else 48
        st.number_input(
            "Caracteres por línea (CPL):",
            value=cpl,
            disabled=True,
            help="58mm utiliza 32 caracteres; 80mm utiliza 48 caracteres."
        )

        tipo_conexion = st.selectbox(
            "Método de Conexión:",
            ["Bluetooth Directo (Web Bluetooth / App Nativa)", "Diálogo del Sistema (Modo Web)"]
        )

    if st.button("💾 Guardar Configuración de Impresora", use_container_width=True):
        st.session_state.config_impresora = {
            "nombre_dispositivo": nombre_dev.strip(),
            "ancho_papel": "58mm" if "58mm" in ancho_papel else "80mm",
            "caracteres_por_linea": cpl,
            "conexion": tipo_conexion
        }
        st.success("¡Configuración de impresora guardada correctamente!")

    st.markdown("---")
    st.markdown("### 🧪 Prueba de Conexión y Formato ESC/POS")
    st.write("Presiona el botón para probar la estructura del ticket en tu impresora activa.")

    if st.button("🖨️ Enviar Ticket de Prueba", use_container_width=True):
        st.info(f"Enviando señal de prueba a la impresora Bluetooth: **{nombre_dev}** ({ancho_papel})...")
