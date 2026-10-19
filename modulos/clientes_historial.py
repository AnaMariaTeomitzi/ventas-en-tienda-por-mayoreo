import streamlit as st
import pandas as pd
import os
from .base_datos import VENTAS_FILE

def mostrar(acceso_propietaria):
    if not acceso_propietaria:
        st.error("⛔ Acceso denegado. Esta sección requiere la contraseña de Propietaria.")
    else:
        st.title("👥 Historial de Compras por Cliente")
        if os.path.exists(VENTAS_FILE):
            try:
                df_ventas_h = pd.read_csv(VENTAS_FILE)
                clientes_lista = df_ventas_h["Cliente"].dropna().unique().tolist()
                
                if clientes_lista:
                    cliente_sel = st.selectbox("Selecciona un cliente para ver su historial:", clientes_lista)
                    df_cte_detalles = df_ventas_h[df_ventas_h["Cliente"] == cliente_sel]
                    
                    total_invertido_cte = df_cte_detalles["Total_Venta"].sum()
                    total_ganancia_cte = df_cte_detalles["Ganancia"].sum()

                    col_ch1, col_ch2 = st.columns(2)
                    col_ch1.metric(f"Total Compras de {cliente_sel}", f"${total_invertido_cte:,.2f} MXN")
                    col_ch2.metric("Ganancia Generada", f"${total_ganancia_cte:,.2f} MXN")

                    st.markdown("---")
                    st.dataframe(df_cte_detalles, use_container_width=True)
                else:
                    st.info("No hay clientes registrados en las ventas.")
            except Exception as e:
                st.error(f"Error al leer el historial por cliente: {e}")
        else:
            st.info("Aún no hay ventas registradas.")