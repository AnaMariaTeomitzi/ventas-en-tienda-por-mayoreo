import streamlit as st
import pandas as pd
import os
from .base_datos import CATALOGO_FILE, HISTORIAL_COSTOS_FILE, limpiar_y_preparar_catalogo, registrar_en_historial, guardar_catalogo_db

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
            st.info("Puedes hacer doble clic en cualquier celda para cambiar precios o nombres. Al terminar, haz clic en **'💾 Guardar Cambios en Catálogo'**.")
            
            df_editado = st.data_editor(
                df_filtrado, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_catalogo"
            )

            if st.button("💾 Guardar Cambios en Catálogo", use_container_width=True):
                try:
                    df_final = df_catalogo.copy()
                    df_cambios = st.session_state["editor_catalogo"]
                    
                    if busqueda and sku_col in df_final.columns:
                        for _, row in df_cambios.iterrows():
                            sku_val = row[sku_col]
                            df_final.loc[df_final[sku_col] == sku_val] = row
                    else:
                        df_final = df_cambios.copy()

                    registrar_en_historial(df_catalogo)
                    
                    # Guardamos usando la función universal de base de datos que actualiza DB y CSV
                    guardar_catalogo_db(df_final)
                    
                    st.success("¡Precios y catálogo actualizados con éxito!")
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
                    
                    from .base_datos import leer_archivo_catalogo, conectar_db, CATALOGO_FILE
                    df_crudo = leer_archivo_catalogo(archivo_subido)
                    
                    if df_crudo is not None and not df_crudo.empty:
                        df_limpio = limpiar_y_preparar_catalogo(df_crudo)
                        
                        # Guardado directo asegurando escritura en BD y CSV local
                        tipo, conn = conectar_db()
                        if tipo == "turso":
                            # Limpiamos tabla anterior y reinsertamos todo limpio
                            conn.execute("DELETE FROM catalogo_productos;")
                            for _, row in df_limpio.iterrows():
                                conn.execute(
                                    "INSERT OR REPLACE INTO catalogo_productos (SKU, Producto, Costo, Precio_Menudeo, Precio_Mayoreo_1, Precio_Mayoreo_2, Precio_Especial, Stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                                    (str(row.get("SKU", "")), str(row.get("Producto", "")), float(row.get("Costo", 0)), float(row.get("Precio_Menudeo", 0)), float(row.get("Precio_Mayoreo_1", 0)), float(row.get("Precio_Mayoreo_2", 0)), float(row.get("Precio_Especial", 0)), int(row.get("Stock", 100)))
                                )
                        else:
                            df_limpio.to_sql("catalogo_productos", conn, if_exists="replace", index=False)
                            
                        df_limpio.to_csv(CATALOGO_FILE, index=False)
                        st.cache_data.clear()
                        
                        st.success("¡Catálogo cargado y actualizado correctamente en el sistema!")
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

                                st.success(f"¡Catálogo restaurado exitosamente a la versión de {fecha_sel}!")
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
        st.markdown("### 📋 Vista Actual del Catálogo")
        columnas_empleado = [col for col in df_filtrado.columns if col.lower() not in ["costo", "costo_unitario", "unnamed: 0"]]
        st.dataframe(df_filtrado[columnas_empleado], use_container_width=True)
