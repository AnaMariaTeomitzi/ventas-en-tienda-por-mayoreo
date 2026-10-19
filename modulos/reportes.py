import streamlit as st
import pandas as pd
from datetime import datetime
import os
from .base_datos import VENTAS_FILE, COMPRAS_FILE

def mostrar(df_catalogo, acceso_propietaria):
    if not acceso_propietaria:
        st.error("⛔ Acceso denegado. Esta sección requiere la contraseña de Propietaria.")
    else:
        st.title("📊 Reportes de Ventas, Ganancias y Control de Deudas")

        tab_ventas, tab_deudas_prov, tab_inventario = st.tabs([
            "📈 Reporte de Ventas y Ganancias",
            "📑 Cuentas por Pagar (Proveedores)",
            "📦 Estado del Inventario"
        ])

        with tab_ventas:
            st.markdown("### 📈 Historial General de Ventas")
            if os.path.exists(VENTAS_FILE):
                try:
                    df_v = pd.read_csv(VENTAS_FILE)
                    if not df_v.empty:
                        total_ingresos = df_v["Total_Venta"].sum()
                        total_costos_v = df_v["Costo_Total"].sum()
                        total_ganancias = df_v["Ganancia"].sum()

                        col_m1, col_m2, col_m3 = st.columns(3)
                        col_m1.metric("💵 Ingresos Totales", f"${total_ingresos:,.2f} MXN")
                        col_m2.metric("📉 Costo Total de Ventas", f"${total_costos_v:,.2f} MXN")
                        col_m3.metric("⭐ Ganancia Neta", f"${total_ganancias:,.2f} MXN")

                        st.markdown("---")
                        st.dataframe(df_v, use_container_width=True)

                        csv_ventas = df_v.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Reporte de Ventas en CSV",
                            data=csv_ventas,
                            file_name=f"reporte_ventas_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.info("Aún no hay registros en el archivo de ventas.")
                except Exception as e:
                    st.error(f"Error al leer el registro de ventas: {e}")
            else:
                st.info("No hay transacciones registradas todavía.")

        with tab_deudas_prov:
            st.markdown("### 📑 Control de Cuentas por Pagar a Proveedores")
            if os.path.exists(COMPRAS_FILE):
                try:
                    df_compras = pd.read_csv(COMPRAS_FILE)
                    if not df_compras.empty:
                        deuda_total_prov = df_compras[df_compras["Estado"] == "Pendiente"]["Saldo_Adeudado"].sum()
                        st.metric("⚠️ Deuda Total Pendiente a Proveedores", f"${deuda_total_prov:,.2f} MXN")

                        st.markdown("---")
                        st.dataframe(df_compras, use_container_width=True)

                        st.markdown("### 💸 Registrar Abono o Pago a Proveedor")
                        proveedores_pendientes = df_compras[df_compras["Estado"] == "Pendiente"]["Proveedor"].unique().tolist()
                        
                        if proveedores_pendientes:
                            prov_sel = st.selectbox("Selecciona Proveedor con adeudo:", proveedores_pendientes)
                            compras_prov = df_compras[(df_compras["Proveedor"] == prov_sel) & (df_compras["Estado"] == "Pendiente")]
                            
                            opciones_compra_id = compras_prov["Fecha_Hora"].astype(str) + " - " + compras_prov["Producto"].astype(str) + " (Saldo: $" + compras_prov["Saldo_Adeudado"].astype(str) + ")"
                            compra_adeudar_str = st.selectbox("Selecciona la factura o compra:", opciones_compra_id)

                            if compra_adeudar_str:
                                idx_compra_real = opciones_compra_id[opciones_compra_id == compra_adeudar_str].index[0]
                                saldo_actual_linea = float(df_compras.loc[idx_compra_real, "Saldo_Adeudado"])
                                
                                monto_abono = st.number_input("Monto a abonar ($):", min_value=0.0, max_value=saldo_actual_linea, value=saldo_actual_linea, step=50.0)

                                if st.button("✅ Aplicar Abono / Liquidar", use_container_width=True):
                                    nuevo_saldo = saldo_actual_linea - monto_abono
                                    df_compras.loc[idx_compra_real, "Saldo_Adeudado"] = nuevo_saldo
                                    df_compras.loc[idx_compra_real, "Monto_Pagado"] = float(df_compras.loc[idx_compra_real, "Monto_Pagado"]) + monto_abono
                                    if nuevo_saldo <= 0:
                                        df_compras.loc[idx_compra_real, "Estado"] = "Pagado"
                                    
                                    df_compras.to_csv(COMPRAS_FILE, index=False)
                                    st.success(f"¡Abono registrado correctamente! Saldo restante: ${nuevo_saldo:,.2f} MXN")
                                    st.rerun()
                        else:
                            st.success("🎉 ¡No hay deudas pendientes con proveedores actualmente!")
                    else:
                        st.info("No hay registros de compras.")
                except Exception as e:
                    st.error(f"Error al leer compras: {e}")
            else:
                st.info("No hay historial de compras registrado.")

        with tab_inventario:
            st.markdown("### 📦 Inventario General Valuado")
            if not df_catalogo.empty:
                df_inv = df_catalogo.copy()
                df_inv["Valor_Costo_Total"] = df_inv["Stock"] * df_inv["Costo"]
                df_inv["Valor_Venta_Total"] = df_inv["Stock"] * df_inv["Precio_Menudeo"]

                val_total_almacen = df_inv["Valor_Costo_Total"].sum()
                val_potencial_venta = df_inv["Valor_Venta_Total"].sum()

                c_inv1, c_inv2 = st.columns(2)
                c_inv1.metric("📦 Inversión en Almacén (Costo)", f"${val_total_almacen:,.2f} MXN")
                c_inv2.metric("🏷️ Valor Potencial de Venta (Menudeo)", f"${val_potencial_venta:,.2f} MXN")

                st.markdown("---")
                st.dataframe(df_inv, use_container_width=True)
            else:
                st.warning("El catálogo está vacío.")