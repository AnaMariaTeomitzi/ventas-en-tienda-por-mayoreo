import streamlit as st
import pandas as pd
import os
from .base_datos import CATALOGO_FILE, HISTORIAL_COSTOS_FILE, limpiar_y_preparar_catalogo, registrar_en_historial, guardar_catalogo_db, leer_archivo_catalogo, conectar_db

def mostrar(df_catalogo, acceso_propietaria):
    st.title("📦 Gestión de Productos, Edición de Precios e Historial")

    # Limpiar cualquier columna "Unnamed" o vacía que venga del Excel o CSV
    if df_catalogo is not None and not df_catalogo.empty:
        df_catalogo = df_catalogo.loc[:, ~df_catalogo.columns.str.contains('^Unnamed', na=False)]

    # Normalizar nombres de columnas a minúsculas temporalmente para búsqueda segura si es necesario
    cols_lower = {c.lower(): c for c in df_catalogo.columns}
    sku_col = cols_lower.get("sku", "SKU")
    prod_col = cols_lower.get("producto", cols_lower.get("nombre", "Producto"))

    # --- BUSCADOR DINÁMICO ---
    st.markdown("---")
    busqueda = st.text_input("🔍 Buscar producto por nombre o SKU:", "").strip().lower()
    
    df_filtrado = df_catalogo.copy()
    if busqueda:
        condicion = False
        if sku_col in df_filtrado.columns:
            condicion = condicion | df_filtrado[sku_col].astype(str).str.lower().str.contains(busqueda, na=False)
        if prod_col in df_filtrado.columns:
            condicion = condicion | df_filtrado[prod_col].astype(str).str.lower().str.contains(busqueda, na=False)
        
        df_filtrado = df_filtrado[condicion]
    # -------------------------

    if acceso_propietaria:
        tab_editar, tab_subir, tab_restaurar = st.tabs([
            "✏️ Editar Precios Directamente", 
            "📤 Cargar Catálogo (Excel / CSV)", 
            "⏪ Restaurar Versión Anterior"
        ])

        with tab_editar:
            st.markdown("### ✏️ Edición Rápida de Precios y Productos")
            st.info("Puedes hacer doble clic en cualquier celda para cambiar precios o nombres, o utiliza la selección individual abajo para modificar un producto con advertencia.")
            
            # --- ALERTA Y EDICIÓN INDIVIDUAL POR PRODUCTO BUSCADO ---
            if busqueda and not df_filtrado.empty:
                st.markdown("---")
                st.warning(f"⚠️ **Modo de Advertencia de Precios:** Has seleccionado un producto específico (`{busqueda}`). Revisa y ajusta sus precios individualmente si deseas aplicar cambios controlados:")
                
                opciones_prod = df_filtrado[sku_col].astype(str) + " - " + df_filtrado[prod_col].astype(str)
                prod_elegido_str = st.selectbox("Selecciona el producto a auditar/modificar:", opciones_prod)
                
                if prod_elegido_str:
                    sku_sel = prod_elegido_str.split(" - ")[0]
                    idx_original = df_catalogo[df_catalogo[sku_col].astype(str) == sku_sel].index[0]
                    row_prod = df_catalogo.loc[idx_original]
                    
                    with st.form(f"form_alerta_precio_{sku_sel}"):
                        st.markdown(f"#### 🏷️ Editando: **{row_prod.get('Producto')}** (SKU: `{sku_sel}`)")
                        
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
                            guardar_ind = st.form_submit_button("💾 Aplicar Cambios Solo a Este Producto", type="primary")
                        with col_btn2:
                            dejar_igual = st.form_submit_button("↩️ Dejar Precios Como Estaban")

                        if guardar_ind:
                            try:
                                registrar_en_historial(df_catalogo)
                                df_catalogo.at[idx_original, "Costo"] = nv_costo
                                df_catalogo.at[idx_original, "Precio_Menudeo"] = nv_men
                                df_catalogo.at[idx_original, "Precio_Mayoreo_1"] = nv_m1
                                df_catalogo.at[idx_original, "Precio_Mayoreo_2"] = nv_m2
                                df_catalogo.at[idx_original, "Precio_Especial"] = nv_esp
                                
                                guardar_catalogo_db(df_catalogo)
                                st.cache_data.clear()
                                
                                # MENSAJE DE CONFIRMACIÓN DETALLADO
                                st.success(f"✅ ¡Guardado con éxito! Producto: '{row_prod.get('Producto')}' | Menudeo: ${nv_men:,.2f} | Mayoreo 1: ${nv_m1:,.2f}")
                                st.toast("¡Datos del producto actualizados y sincronizados correctamente!", icon="💾")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar el producto: {e}")
                        
                        if dejar_igual:
                            st.info("ℹ️ Se conservaron los precios originales del producto.")
                st.markdown("---")

            # --- TABLA GENERAL DE EDICIÓN ---
            df_editado = st.data_editor(
                df_filtrado, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_catalogo"
            )

            if st.button("💾 Guardar Cambios Generales en Catálogo", use_container_width=True):
                try:
                    df_final = df_catalogo.copy()
                    df_final.update(df_editado)
                    
                    filas_nuevas = df_editado.loc[~df_editado.index.isin(df_catalogo.index)]
                    if not filas_nuevas.empty:
                        df_final = pd.concat([df_final, filas_nuevas], ignore_index=True)

                    registrar_en_historial(df_catalogo)
                    guardar_catalogo_db(df_final)
                    st.cache_data.clear()
                    
                    st.success("✅ ¡Catálogo general actualizado y guardado correctamente en Turso y el sistema!")
                    st.toast("¡Cambios generales guardados con éxito!", icon="💾")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar los cambios: {e}")

        with tab_subir:
            st.markdown("### 📤 Subir tu Catálogo (Excel o CSV)")
            st.info("Sube tu archivo .xlsx o .csv con tus productos, costos y precios.")
            
            archivo_subido = st.file_uploader("Selecciona tu archivo", type=["xlsx", "xls", "csv"], key="uploader_excel")
            if archivo_subido is not None:
                try:
                    registrar_en_historial(df_catalogo)
                    df_crudo = leer_archivo_catalogo(archivo_subido)
                    
                    if df_crudo is not None and not df_crudo.empty:
                        df_limpio = limpiar_y_preparar_catalogo(df_crudo)
                        guardar_catalogo_db(df_limpio)
                        st.cache_data.clear()
                        
                        st.success("✅ ¡Catálogo cargado y guardado correctamente en el sistema!")
                        st.toast("¡Archivo importado con éxito!", icon="📂")
                        st.rerun()
                    else:
                        st.error("El archivo está vacío o no se pudo leer.")
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")

        with tab_restaurar:
            st.markdown("### ⏪ Restaurar Versión de Precios Anterior")
            st.warning("Si cometiste un error editando o cargando datos, selecciona una fecha/hora del historial para revertir el catálogo a ese punto exacto.")

            if os.path.exists(HISTORIAL_COSTOS_FILE):
                try:
                    df_hist_all = pd.read_csv(HISTORIAL_COSTOS_FILE)
                    if "Fecha_Actualizacion" in df_hist_all.columns:
                        fechas_disponibles = df_hist_all["Fecha_Actualizacion"].dropna().unique().tolist()
                        fechas_disponibles.reverse()

                        if fechas_disponibles:
                            fecha_sel = st.selectbox("Selecciona la fecha/hora del respaldo a restaurar:", fechas_disponibles)
                            df_respaldo_sel = df_hist_all[df_hist_all["Fecha_Actualizacion"] == fecha_sel]

                            st.markdown(f"#### 📋 Vista previa de la versión: **{fecha_sel}**")
                            st.dataframe(df_respaldo_sel.drop(columns=["Fecha_Actualizacion"], errors="ignore"), use_container_width=True)

                            if st.button("⏪ Confirmar y Restaurar esta Versión de Precios", use_container_width=True):
                                registrar_en_historial(df_catalogo)
                                cols_base = [c for c in df_respaldo_sel.columns if c != "Fecha_Actualizacion"]
                                df_restaurado = df_respaldo_sel[cols_base].copy()
                                guardar_catalogo_db(df_restaurado)

                                st.success(f"✅ ¡Catálogo restaurado exitosamente a la versión de {fecha_sel}!")
                                st.toast("¡Versión restaurada con éxito!", icon="⏪")
                                st.rerun()
                        else:
                            st.info("Aún no hay puntos de restauración guardados en el historial.")
                    else:
                        st.info("Aún no se ha registrado un historial estructurado de cambios.")
                except Exception as e:
                    st.error(f"Error al consultar el historial: {e}")
            else:
                st.info("No hay historial de respaldos disponible aún.")

    else:
        st.markdown("### 📋 Vista Actual del Catálogo y Consulta Rápida")
        columnas_empleado = [col for col in df_filtrado.columns if col.lower() not in ["costo", "costo_unitario", "unnamed: 0"]]
        
        # --- CONSULTA RÁPIDA DE PRECIOS PARA EMPLEADOS ---
        if busqueda and not df_filtrado.empty:
            st.markdown("---")
            st.info(f"🔍 **Consulta Rápida de Precios para la búsqueda:** `{busqueda}`")
            
            opciones_prod_emp = df_filtrado[sku_col].astype(str) + " - " + df_filtrado[prod_col].astype(str)
            prod_sel_emp = st.selectbox("Selecciona un producto para ver sus niveles de precio detallados:", opciones_prod_emp, key="sel_emp_prod")
            
            if prod_sel_emp:
                sku_emp = prod_sel_emp.split(" - ")[0]
                row_emp = df_filtrado[df_filtrado[sku_col].astype(str) == sku_emp].iloc[0]
                
                st.markdown(f"#### 🏷️ Producto: **{row_emp.get(prod_col)}** (SKU: `{sku_emp}`)")
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                col_e1.metric("💵 Menudeo", f"${float(row_emp.get('Precio_Menudeo', 0.0)):,.2f}")
                col_e2.metric("⭐ Mayoreo 1", f"${float(row_emp.get('Precio_Mayoreo_1', 0.0)):,.2f}")
                col_e3.metric("⭐ Mayoreo 2", f"${float(row_emp.get('Precio_Mayoreo_2', 0.0)):,.2f}")
                col_e4.metric("🌟 Especial", f"${float(row_emp.get('Precio_Especial', 0.0)):,.2f}")
            st.markdown("---")

        st.dataframe(df_filtrado[columnas_empleado], use_container_width=True)
