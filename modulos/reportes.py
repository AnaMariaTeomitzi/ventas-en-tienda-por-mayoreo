import streamlit as st
import pandas as pd
from datetime import datetime
import os
from .base_datos import COMPRAS_FILE, obtener_historial_ventas

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
            try:
                # OBTENEMOS EL HISTORIAL DIRECTAMENTE DESDE LA BASE DE DATOS DE TURSO
                df_v = obtener_historial_ventas()
                
                if df_v is not None and not df_v.empty:
                    # --- FILTRO POR RANGO DE FECHAS ---
                    st.markdown("#### 📅 Filtrar Ventas por Rango de Fechas")
                    
                    if "Fecha" in df_v.columns:
                        df_v["Fecha_dt"] = pd.to_datetime(df_v["Fecha"], errors='coerce')
                        
                        min_fecha = df_v["Fecha_dt"].min().date() if not df_v["Fecha_dt"].isna().all() else datetime.now().date()
                        max_fecha = df_v["Fecha_dt"].max().date() if not df_v["Fecha_dt"].isna().all() else datetime.now().date()

                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            fecha_inicio = st.date_input("Fecha de Inicio", value=min_fecha, format="YYYY-MM-DD")
                        with col_f2:
                            fecha_fin = st.date_input("Fecha de Fin", value=max_fecha, format="YYYY-MM-DD")

                        mask_fecha = (df_v["Fecha_dt"].dt.date >= fecha_inicio) & (df_v["Fecha_dt"].dt.date <= fecha_fin)
                        df_v_filtrado = df_v.loc[mask_fecha].copy()
                        df_v_filtrado = df_v_filtrado.drop(columns=["Fecha_dt"], errors="ignore")
                    else:
                        df_v_filtrado = df_v.copy()
                    # ----------------------------------

                    if not df_v_filtrado.empty:
                        total_ingresos = pd.to_numeric(df_v_filtrado["Total_Venta"], errors='coerce').sum()
                        total_costos_v = pd.to_numeric(df_v_filtrado["Costo_Total"], errors='coerce').sum()
                        total_ganancias = pd.to_numeric(df_v_filtrado["Ganancia"], errors='coerce').sum()

                        col_m1, col_m2, col_m3 = st.columns(3)
                        col_m1.metric("💵 Ingresos Totales", f"${total_ingresos:,.2f} MXN")
                        col_m2.metric("📉 Costo Total de Ventas", f"${total_costos_v:,.2f} MXN")
                        col_m3.metric("⭐ Ganancia Neta", f"${total_ganancias:,.2f} MXN")

                        st.markdown("---")
                        st.dataframe(df_v_filtrado, use_container_width=True)

                        csv_ventas = df_v_filtrado.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Descargar Reporte Filtrado en CSV",
                            data=csv_ventas,
                            file_name=f"reporte_ventas_{fecha_inicio}_al_{fecha_fin}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning("⚠️ No se encontraron ventas registradas en el rango de fechas seleccionado.")
                else:
                    st.info("Aún no hay registros de ventas en la base de datos.")
            except Exception as e:
                st.error(f"Error al leer o filtrar el registro de ventas: {e}")

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
