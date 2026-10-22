import streamlit as st
import pandas as pd
import os
from .base_datos import CATALOGO_FILE, HISTORIAL_COSTOS_FILE, limpiar_y_preparar_catalogo, registrar_en_historial

def mostrar(df_catalogo, acceso_propietaria):
    st.title("📦 Gestión de Productos, Edición de Precios e Historial")

    # Limpiar cualquier columna "Unnamed" o vacía que venga del Excel o CSV
    if df_catalogo is not None and not df_catalogo.empty:
        df_catalogo = df_catalogo.loc[:, ~df_catalogo.columns.str.contains('^Unnamed', na=False)]

    # --- BUSCADOR DINÁMICO ---
    st.markdown("---")
    busqueda = st.text_input("🔍 Buscar producto por nombre o SKU:", "").strip().lower()
    
    df_filtrado = df_catalogo.copy()
    if busqueda:
        condicion = False
        if "SKU" in df_filtrado.columns:
            condicion = condicion | df_filtrado["SKU"].astype(str).str.lower().str.contains(busqueda, na=False)
        if "Producto" in df_filtrado.columns:
            condicion = condicion | df_filtrado["Producto"].astype(str).str.lower().str.contains(busqueda, na=False)
        
        df_filtrado = df_filtrado[condicion]
    # -------------------------

    if acceso_propietaria:
        tab_editar, tab_subir, tab_restaurar = st.tabs([
            "✏️ Editar Precios Directamente", 
            "📤 Cargar Catálogo en Excel", 
            "⏪ Restaurar Versión Anterior"
        ])

     with tab_editar:
            st.markdown("### ✏️ Edición Rápida de Precios y Productos")
            st.info("Puedes hacer doble clic en cualquier celda para cambiar precios o nombres. Al terminar, haz clic en **'💾 Guardar Cambios en Catálogo'**.")
            
            # Mostramos el editor usando el DataFrame filtrado para la vista
            df_editado = st.data_editor(
                df_filtrado, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_catalogo"
            )

            if st.button("💾 Guardar Cambios en Catálogo", use_container_width=True):
                try:
                    # Obtenemos la tabla completa directamente desde el estado del editor en la sesión
                    # Si hubo búsqueda, actualizamos los registros modificados en el catálogo general.
                    df_final = df_catalogo.copy()
                    df_cambios = st.session_state["editor_catalogo"]
                    
                    if busqueda and "SKU" in df_final.columns:
                        # Actualizamos fila por fila basándonos en el SKU editado
                        for _, row in df_cambios.iterrows():
                            sku_val = row["SKU"]
                            df_final.loc[df_final["SKU"] == sku_val] = row
                    else:
                        # Si no hay búsqueda activa, el editor contiene todo el catálogo
                        df_final = df_cambios.copy()

                    # Limpiamos, respaldamos y guardamos de forma persistente
                    df_final = limpiar_y_preparar_catalogo(df_final)
                    registrar_en_historial(df_catalogo)
                    df_final.to_csv(CATALOGO_FILE, index=False)
                    
                    st.success("¡Precios y catálogo actualizados con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar los cambios: {e}")

        with tab_subir:
            st.markdown("### 📤 Subir tu Catálogo en Excel")
            st.info("Sube tu archivo .xlsx con tus productos, costos y precios.")
            
            archivo_subido = st.file_uploader("Selecciona tu archivo Excel", type=["xlsx", "xls"])
            if archivo_subido is not None:
                try:
                    df_subido = pd.read_excel(archivo_subido)
                    df_subido = limpiar_y_preparar_catalogo(df_subido)
                    registrar_en_historial(df_catalogo)
                    df_subido.to_csv(CATALOGO_FILE, index=False)
                    st.success("¡Catálogo cargado y actualizado correctamente!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo Excel: {e}")

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
                                df_restaurado = limpiar_y_preparar_catalogo(df_restaurado)
                                df_restaurado.to_csv(CATALOGO_FILE, index=False)

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
