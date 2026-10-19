import streamlit as st
import pandas as pd
from datetime import datetime
import os
from .base_datos import VENTAS_FILE

def mostrar():
    st.title("🔄 Registro de Devoluciones de Clientes")

    if os.path.exists(VENTAS_FILE):
        try:
            df_ventas = pd.read_csv(VENTAS_FILE)
            clientes_disponibles = df_ventas["Cliente"].dropna().unique().tolist()
            
            if clientes_disponibles:
                col_dev1, col_dev2 = st.columns(2)
                with col_dev1:
                    cliente_dev = st.selectbox("Selecciona el Cliente que devuelve:", clientes_disponibles)
                
                df_ventas_cliente = df_ventas[df_ventas["Cliente"] == cliente_dev]

                with col_dev2:
                    opciones_compras_cliente = df_ventas_cliente["Fecha_Hora"].astype(str) + " - " + df_ventas_cliente["Producto"].astype(str) + " (Cant: " + df_ventas_cliente["Cantidad"].astype(str) + ")"
                    venta_seleccionada_str = st.selectbox("Selecciona el artículo de su compra:", opciones_compras_cliente)

                if venta_seleccionada_str:
                    idx_venta = opciones_compras_cliente[opciones_compras_cliente == venta_seleccionada_str].index[0]
                    prod_info = df_ventas.loc[idx_venta]

                    st.markdown(f"### 📋 Detalles del Artículo a Devolver")
                    st.write(f"**Producto:** {prod_info['Producto']} | **SKU:** {prod_info['SKU']}")
                    st.write(f"**Precio Unitario Pagado:** ${float(prod_info['Precio_Unitario']):,.2f} MXN | **Cantidad comprada:** {prod_info['Cantidad']}")

                    cant_a_devolver = st.number_input("Cantidad de piezas a devolver", min_value=1, max_value=int(abs(float(prod_info['Cantidad']))), value=1, step=1)
                    motivo_dev = st.text_input("Motivo de la devolución (Opcional)", value="Devolución por cambio / defecto")

                    if st.button("🔄 Confirmar y Registrar Devolución", use_container_width=True):
                        ahora = datetime.now()
                        p_unit = float(prod_info['Precio_Unitario'])
                        c_unit = float(prod_info['Costo_Unitario'])
                        
                        monto_restar = p_unit * cant_a_devolver
                        ganancia_restar = (p_unit - c_unit) * cant_a_devolver
                        costo_restar = c_unit * cant_a_devolver

                        nueva_devolucion = pd.DataFrame([{
                            "Fecha_Hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                            "Fecha": ahora.strftime("%Y-%m-%d"),
                            "Cliente": cliente_dev,
                            "SKU": prod_info['SKU'],
                            "Producto": f"[DEVOLUCIÓN] {prod_info['Producto']}",
                            "Nivel_Precio": prod_info['Nivel_Precio'],
                            "Precio_Unitario": p_unit,
                            "Costo_Unitario": c_unit,
                            "Cantidad": -cant_a_devolver,
                            "Total_Venta": -monto_restar,
                            "Costo_Total": -costo_restar,
                            "Ganancia": -ganancia_restar,
                            "Motivo": motivo_dev
                        }])

                        nueva_devolucion.to_csv(VENTAS_FILE, mode='a', header=False, index=False)
                        st.success(f"Devolución registrada correctamente.")
                        st.rerun()
            else:
                st.info("No hay clientes en el registro de ventas.")
        except Exception as e:
            st.info("Aún no hay suficientes datos de ventas registrados.")
    else:
        st.info("Aún no existen ventas registradas en el sistema para procesar devoluciones.")