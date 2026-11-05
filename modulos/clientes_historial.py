import streamlit as st
import pandas as pd
from .base_datos import obtener_historial_ventas

def mostrar(acceso_propietaria):
    if not acceso_propietaria:
        st.error("⛔ Acceso denegado. Esta sección requiere la contraseña de Propietaria.")
    else:
        st.title("👥 Historial de Compras por Cliente")
        try:
            # Obtenemos el historial directamente desde la base de datos (Turso o SQLite)
            df_ventas_h = obtener_historial_ventas()
            
            if df_ventas_h is not None and not df_ventas_h.empty and "Cliente" in df_ventas_h.columns:
                clientes_lista = df_ventas_h["Cliente"].dropna().unique().tolist()
                
                if clientes_lista:
                    cliente_sel = st.selectbox("Selecciona un cliente para ver su historial:", clientes_lista)
                    
                    # Filtro seguro normalizando textos
                    df_cte_detalles = df_ventas_h[df_ventas_h["Cliente"].astype(str).str.strip().str.lower() == str(cliente_sel).strip().lower()]
                    
                    total_invertido_cte = pd.to_numeric(df_cte_detalles["Total_Venta"], errors='coerce').sum()
                    total_ganancia_cte = pd.to_numeric(df_cte_detalles["Ganancia"], errors='coerce').sum()

                    col_ch1, col_ch2 = st.columns(2)
                    col_ch1.metric(f"Total Compras de {cliente_sel}", f"${total_invertido_cte:,.2f} MXN")
                    col_ch2.metric("Ganancia Generada", f"${total_ganancia_cte:,.2f} MXN")

                    st.markdown("---")
                    st.dataframe(df_cte_detalles, use_container_width=True)
                else:
                    st.info("No hay clientes registrados en las ventas.")
            else:
                st.info("Aún no hay ventas registradas en la base de datos.")
        except Exception as e:
            st.error(f"Error al leer el historial por cliente: {e}")
