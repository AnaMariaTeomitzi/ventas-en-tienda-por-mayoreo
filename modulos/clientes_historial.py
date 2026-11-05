import streamlit as st
import pandas as pd
from .base_datos import conectar_db

def mostrar(acceso_propietaria):
    st.title("👥 Historial de Compras por Cliente")
    
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            rs = conn.execute("SELECT DISTINCT Cliente FROM registro_ventas WHERE Cliente IS NOT NULL AND Cliente != '';")
            clientes = [row[0] for row in rs.rows]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Cliente FROM registro_ventas WHERE Cliente IS NOT NULL AND Cliente != '';")
            clientes = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar clientes: {e}")
        clientes = []

    if not clientes:
        st.info("No hay clientes con ventas registradas todavía.")
        return

    cliente_sel = st.selectbox("Selecciona un cliente para ver su historial:", clientes)

    if cliente_sel:
        try:
            if tipo == "turso":
                rs = conn.execute("SELECT * FROM registro_ventas WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_sel,))
                filas = rs.rows
                # Extraemos los nombres de las columnas directamente desde Turso para que coincidan al 100%
                columnas = [desc[0] for desc in rs.description] if rs.description else []
                df_cliente = pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame()
            else:
                query = "SELECT * FROM registro_ventas WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));"
                df_cliente = pd.read_sql(query, conn, params=(cliente_sel,))

            if not df_cliente.empty:
                # Limpiamos y convertimos a numérico de manera segura buscando las columnas por su nombre real
                if "Total_Venta" in df_cliente.columns:
                    df_cliente["Total_Venta"] = pd.to_numeric(df_cliente["Total_Venta"], errors='coerce').fillna(0)
                    total_compras = df_cliente["Total_Venta"].sum()
                else:
                    total_compras = 0.0

                if "Ganancia" in df_cliente.columns:
                    df_cliente["Ganancia"] = pd.to_numeric(df_cliente["Ganancia"], errors='coerce').fillna(0)
                    ganancia_total = df_cliente["Ganancia"].sum()
                else:
                    ganancia_total = 0.0
                
                # 🎁 CÁLCULO DEL FONDO NAVIDEÑO EN BASE A LA GANANCIA (Ejemplo: 10%)
                porcentaje_navideno = 0.10 
                fondo_navideno = ganancia_total * porcentaje_navideno

                st.markdown(f"### Resumen para: **{cliente_sel}**")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("💵 Total Compras", f"${total_compras:,.2f} MXN")
                col2.metric("⭐ Ganancia Generada", f"${ganancia_total:,.2f} MXN", help="Utilidad neta generada por este cliente.")
                col3.metric("🎄 Fondo Navideño (10%)", f"${fondo_navideno:,.2f} MXN", help="Porcentaje reservado exclusivamente de la ganancia para regalo o reembolso de fin de año.")

                st.markdown("---")
                st.dataframe(df_cliente, use_container_width=True)
            else:
                st.info("Este cliente no tiene compras registradas en el sistema.")

        except Exception as e:
            st.error(f"Error al generar el historial del cliente: {e}")
