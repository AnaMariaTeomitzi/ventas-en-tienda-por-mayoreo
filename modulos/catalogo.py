import streamlit as st
import pandas as pd
import os
from .base_datos import CATALOGO_FILE, HISTORIAL_COSTOS_FILE, limpiar_y_preparar_catalogo, registrar_en_historial, leer_archivo_catalogo, conectar_db

def mostrar(df_catalogo, acceso_propietaria):
    # --- ESTILO EJECUTIVO Y CORPORATIVO ---
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stButton button {
            border-radius: 6px;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📦 Gestión de Productos y Edición Ejecutiva")

    # Limpiar cualquier columna "Unnamed" o vacía que venga del Excel o CSV
    if df_catalogo is not None and not df_catalogo.empty:
        df_catalogo = df_catalogo.loc[:, ~df_catalogo.columns.str.contains('^Unnamed', na=False)]

    # --- MOSTRAR MENSAJE DE ÉXITO PERSISTENTE SI EXISTE ---
    if "mensaje_exito" in st.session_state and st.session_state.mensaje_exito:
        st.success(st.session_state.mensaje_exito)
        st.toast(st.session_state.mensaje_exito, icon="✅")
        st.session_state.mensaje_exito = None  # Limpiar después de mostrar

    # Normalizar nombres de columnas a minúsculas temporalmente para búsqueda segura
    cols_lower = {c.lower(): c for c in df_catalogo.columns}
    sku_col = cols_lower.get("sku", "SKU")
    prod_col = cols_lower.get("producto", cols_lower.get("nombre", "Producto"))

    # --- BUSCADOR DINÁMICO EJECUTIVO ---
    st.markdown("---")
    col_bs1, col_bs2 = st.columns([3, 1])
    with col_bs1:
        busqueda = st.text_input("🔍 Búsqueda rápida por nombre o SKU:", "").strip().lower()
    with col_bs2:
        st.markdown(f"<div style='text-align: right; padding-top: 28px;'><span style='color: #666; font-size: 14px;'>Total registros: <b>{len(df_catalogo)}</b></span></div>", unsafe_allow_html=True)
    
    df_filtrado = df_catalogo.copy()
    if busqueda:
        condicion = False
        if sku_col in df_filtrado.columns:
            condicion = condicion | df_filtrado[sku_col].astype(str).str.lower().str.contains(busqueda, na=False)
        if prod_col in df_filtrado.columns:
            condicion = condicion | df_filtrado[prod_col].astype(str).str.lower().str.contains(busqueda, na=False)
        
        df_filtrado = df_filtrado[condicion]

    if acceso_propietaria:
        tab_editar, tab_subir, tab_restaurar = st.tabs([
            "✏️ Edición de Precios y Control", 
            "📤 Importar Catálogo (Excel / CSV)", 
            "⏪ Historial y Respaldos"
        ])

        with tab_editar:
            st.markdown("### 💼 Panel Ejecutivo de Actualización de Precios")
            st.info("💡 **Consejo gerencial:** Utiliza la búsqueda superior para filtrar un artículo y editar sus valores con confirmación de seguridad detallada.")
            
            # --- ALERTA Y EDICIÓN INDIVIDUAL POR PRODUCTO BUSCADO ---
            if busqueda and not df_filtrado.empty:
                st.markdown("---")
                st.markdown("<div style='background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-left: 5px solid #1976d2;'>", unsafe_allow_html=True)
                st.write(f"🔍 **Producto localizado bajo la búsqueda:** `{busqueda}`")
                
                opciones_prod = df_filtrado[sku_col].astype(str) + " - " + df_filtrado[prod_col].astype(str)
                prod_elegido_str = st.selectbox("Seleccione el producto para auditar o modificar sus tarifas:", opciones_prod)
                
                if prod_elegido_str:
                    sku_sel = prod_elegido_str.split(" - ")[0]
                    idx_original = df_catalogo[df_catalogo[sku_col].astype(str) == sku_sel].index[0]
                    row_prod = df_catalogo.loc[idx_original]
                    
                    with st.form(f"form_alerta_precio_{sku_sel}"):
                        st.markdown(f"#### 🏷️ Ajuste de Tarifas para: **{row_prod.get('Producto')}** (SKU: `{sku_sel}`)")
                        
                        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
                        with col_p1:
                            nv_costo = st.number_input("Costo ($)", value=float(row_prod.get("Costo", 0.0)), step=1.0)
                        with col_p2:
                            nv_men = st.number_input("Menudeo ($)", value=float(row_prod.get("Precio_Menudeo", 0.0)), step=1.0)
                        with col_p3:
                            nv_m1 = st.number_input("Mayoreo 1 ($)", value=float(row_prod.get("Precio_Mayoreo_1", 0.0)), step=1.0)
                        with col_p4:
                            nv_m2 = st.number_input("Mayoreo 2 ($)", value=float(row_prod.get("Precio_Mayoreo_2", 0.0)), step=1.0)
                        with col_p5:
                            nv_esp = st.number_input("Especial ($)", value=float(row_prod.get("Precio_Especial", 0.0)), step=1.0)
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            guardar_ind = st.form_submit_button("💾 Guardar Cambios de este Producto", type="primary", use_container_width=True)
                        with col_btn2:
                            dejar_igual = st.form_submit_button("↩️ Cancelar / Mantener Valores", use_container_width=True)

                        if guardar_ind:
                            try:
                                registrar_en_historial(df_catalogo)
                                df_catalogo.at[idx_original, "Costo"] = nv_costo
                                df_catalogo.at[idx_original, "Precio_Menudeo"] = nv_men
                                df_catalogo.at[idx_original, "Precio_Mayoreo_1"] = nv_m1
                                df_catalogo.at[idx_original, "Precio_Mayoreo_2"] = nv_m2
                                df_catalogo.at[idx_original, "Precio_Especial"] = nv_esp
                                
                                # --- SINCRONIZACIÓN DIRECTA TURSO Y CSV ---
                                tipo, conn = conectar_db()
                                if tipo == "turso":
                                    conn.execute("DELETE FROM catalogo_productos;")
                                    for _, r in df_catalogo.iterrows():
                                        conn.execute(
                                            "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                                            (str(r.get("SKU", "")), str(r.get("Producto", "")), float(r.get("Costo", 0)), float(r.get("Precio_Menudeo", 0)), float(r.get("Precio_Mayoreo_1", 0)), float(r.get("Precio_Mayoreo_2", 0)), float(r.get("Precio_Especial", 0)), int(r.get("Stock", 100)))
                                        )
                                else:
                                    df_catalogo.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
                                
                                df_catalogo.to_csv(CATALOGO_FILE, index=False)
                                st.cache_data.clear()
                                
                                st.session_state.mensaje_exito = f"✅ ¡Actualización exitosa en Turso! Producto: '{row_prod.get('Producto')}' | Menudeo: ${nv_men:,.2f} | Mayoreo 1: ${nv_m1:,.2f}."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar el producto en Turso: {e}")
                        
                        if dejar_igual:
                            st.info("ℹ️ Se mantuvieron los precios originales sin alteraciones.")
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")

            # --- TABLA GENERAL DE EDICIÓN ---
            st.markdown("#### 📋 Matriz General de Inventario y Precios")
            df_editado = st.data_editor(
                df_filtrado, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_catalogo"
            )

            if st.button("💾 Guardar Todos los Cambios del Catálogo General", type="primary", use_container_width=True):
                try:
                    df_final = df_catalogo.copy()
                    df_final.update(df_editado)
                    
                    filas_nuevas = df_editado.loc[~df_editado.index.isin(df_catalogo.index)]
                    if not filas_nuevas.empty:
                        df_final = pd.concat([df_final, filas_nuevas], ignore_index=True)

                    registrar_en_historial(df_catalogo)
                    
                    # --- SINCRONIZACIÓN DIRECTA GENERAL TURSO Y CSV ---
                    tipo, conn = conectar_db()
                    if tipo == "turso":
                        conn.execute("DELETE FROM catalogo_productos;")
                        for _, r in df_final.iterrows():
                            conn.execute(
                                "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                                (str(r.get("SKU", "")), str(r.get("Producto", "")), float(r.get("Costo", 0)), float(r.get("Precio_Menudeo", 0)), float(r.get("Precio_Mayoreo_1", 0)), float(r.get("Precio_Mayoreo_2", 0)), float(r.get("Precio_Especial", 0)), int(r.get("Stock", 100)))
                            )
                    else:
                        df_final.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
                    
                    df_final.to_csv(CATALOGO_FILE, index=False)
                    st.cache_data.clear()
                    
                    st.session_state.mensaje_exito = "✅ ¡Matriz general guardada, sincronizada en Turso y actualizada con éxito!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar los cambios generales en Turso: {e}")

        with tab_subir:
            st.markdown("### 📤 Carga Masiva de Catálogo (Excel / CSV)")
            st.info("Sube tu archivo corporativo .xlsx o .csv para actualizar de manera masiva los costos y precios.")
            
            archivo_subido = st.file_uploader("Selecciona el documento de respaldo", type=["xlsx", "xls", "csv"], key="uploader_excel")
            if archivo_subido is not None:
                try:
                    registrar_en_historial(df_catalogo)
                    df_crudo = leer_archivo_catalogo(archivo_subido)
                    
                    if df_crudo is not None and not df_crudo.empty:
                        df_limpio = limpiar_y_preparar_catalogo(df_crudo)
                        
                        tipo, conn = conectar_db()
                        if tipo == "turso":
                            conn.execute("DELETE FROM catalogo_productos;")
                            for _, r in df_limpio.iterrows():
                                conn.execute(
                                    "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                                    (str(r.get("SKU", "")), str(r.get("Producto", "")), float(r.get("Costo", 0)), float(r.get("Precio_Menudeo", 0)), float(r.get("Precio_Mayoreo_1", 0)), float(r.get("Precio_Mayoreo_2", 0)), float(r.get("Precio_Especial", 0)), int(r.get("Stock", 100)))
                                )
                        else:
                            df_limpio.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
                        
                        df_limpio.to_csv(CATALOGO_FILE, index=False)
                        st.cache_data.clear()
                        
                        st.session_state.mensaje_exito = "✅ ¡Catálogo masivo importado y sincronizado en Turso correctamente!"
                        st.rerun()
                    else:
                        st.error("El archivo proporcionado está vacío o presenta un formato incompatible.")
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")

        with tab_restaurar:
            st.markdown("### ⏪ Auditoría y Restauración de Versiones Anteriores")
            st.warning("Si requieres revertir algún cambio tarifario, selecciona la fecha y hora exacta del respaldo corporativo previo.")

            if os.path.exists(HISTORIAL_COSTOS_FILE):
                try:
                    df_hist_all = pd.read_csv(HISTORIAL_COSTOS_FILE)
                    if "Fecha_Actualizacion" in df_hist_all.columns:
                        fechas_disponibles = df_hist_all["Fecha_Actualizacion"].dropna().unique().tolist()
                        fechas_disponibles.reverse()

                        if fechas_disponibles:
                            fecha_sel = st.selectbox("Seleccione el punto de restauración deseado:", fechas_disponibles)
                            df_respaldo_sel = df_hist_all[df_hist_all["Fecha_Actualizacion"] == fecha_sel]

                            st.markdown(f"#### 📋 Vista previa del respaldo: **{fecha_sel}**")
                            st.dataframe(df_respaldo_sel.drop(columns=["Fecha_Actualizacion"], errors="ignore"), use_container_width=True)

                            if st.button("⏪ Confirmar y Revertir Catálogo a esta Versión", type="primary", use_container_width=True):
                                registrar_en_historial(df_catalogo)
                                cols_base = [c for c in df_respaldo_sel.columns if c != "Fecha_Actualizacion"]
                                df_restaurado = df_respaldo_sel[cols_base].copy()
                                
                                tipo, conn = conectar_db()
                                if tipo == "turso":
                                    conn.execute("DELETE FROM catalogo_productos;")
                                    for _, r in df_restaurado.iterrows():
                                        conn.execute(
                                            "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                                            (str(r.get("SKU", "")), str(r.get("Producto", "")), float(r.get("Costo", 0)), float(r.get("Precio_Menudeo", 0)), float(r.get("Precio_Mayoreo_1", 0)), float(r.get("Precio_Mayoreo_2", 0)), float(r.get("Precio_Especial", 0)), int(r.get("Stock", 100)))
                                        )
                                else:
                                    df_restaurado.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
                                
                                df_restaurado.to_csv(CATALOGO_FILE, index=False)
                                st.cache_data.clear()

                                st.session_state.mensaje_exito = f"✅ ¡Catálogo revertido y sincronizado en Turso a la versión del {fecha_sel}!"
                                st.rerun()
                        else:
                            st.info("No existen respaldos previos registrados en el historial.")
                    else:
                        st.info("El archivo de historial no cuenta con la estructura requerida.")
                except Exception as e:
                    st.error(f"Error al consultar el historial: {e}")
            else:
                st.info("Aún no se cuenta con un registro histórico de respaldos.")

    else:
        st.markdown("### 📋 Consulta Ejecutiva de Catálogo y Tarifas")
        columnas_empleado = [col for col in df_filtrado.columns if col.lower() not in ["costo", "costo_unitario", "unnamed: 0"]]
        
        # --- CONSULTA RÁPIDA DE PRECIOS PARA EMPLEADOS ---
        if busqueda and not df_filtrado.empty:
            st.markdown("---")
            st.markdown(f"<div style='background-color: #f1f8e9; padding: 12px; border-radius: 8px; border-left: 5px solid #7cb342;'>", unsafe_allow_html=True)
            st.write(f"🔍 **Consulta de tarifas para la búsqueda:** `{busqueda}`")
            
            opciones_prod_emp = df_filtrado[sku_col].astype(str) + " - " + df_filtrado[prod_col].astype(str)
            prod_sel_emp = st.selectbox("Selecciona un artículo para consultar sus niveles de precio:", opciones_prod_emp, key="sel_emp_prod")
            
            if prod_sel_emp:
                sku_emp = prod_sel_emp.split(" - ")[0]
                row_emp = df_filtrado[df_filtrado[sku_col].astype(str) == sku_emp].iloc[0]
                
                st.markdown(f"#### 🏷️ Artículo: **{row_emp.get(prod_col)}** (SKU: `{sku_emp}`)")
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                col_e1.metric("💵 Menudeo", f"${float(row_emp.get('Precio_Menudeo', 0.0)):,.2f}")
                col_e2.metric("⭐ Mayoreo 1", f"${float(row_emp.get('Precio_Mayoreo_1', 0.0)):,.2f}")
                col_e3.metric("⭐ Mayoreo 2", f"${float(row_emp.get('Precio_Mayoreo_2', 0.0)):,.2f}")
                col_e4.metric("🌟 Especial", f"${float(row_emp.get('Precio_Especial', 0.0)):,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")

        st.dataframe(df_filtrado[columnas_empleado], use_container_width=True)
