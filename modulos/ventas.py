import streamlit as st
import pandas as pd
from datetime import datetime
import zoneinfo
import os
import streamlit.components.v1 as components
from .base_datos import obtener_clientes_recurrentes_lista, guardar_venta_db, obtener_historial_ventas, VENTAS_FILE, conectar_db


def obtener_siguiente_folio(anio_actual):
    """
    Consulta el historial de ventas para determinar el próximo número consecutivo 
    del año actual (ej. TCK-2026-1, TCK-2026-2...).
    """
    try:
        df_hist = obtener_historial_ventas()
        if not df_hist.empty and "Numero_Ticket" in df_hist.columns:
            prefijo_anio = f"TCK-{anio_actual}-"
            tickets_anio = df_hist[df_hist["Numero_Ticket"].astype(str).str.startswith(prefijo_anio)]
            
            if not tickets_anio.empty:
                consecutivos = []
                for t in tickets_anio["Numero_Ticket"].astype(str):
                    partes = t.split("-")
                    if len(partes) >= 3 and partes[2].isdigit():
                        consecutivos.append(int(partes[2]))
                
                if consecutivos:
                    return max(consecutivos) + 1
        return 1
    except Exception:
        return 1


def _inicializar_agotados(df_catalogo):
    """Inicializa el conjunto de SKUs agotados en session_state (y respeta columna 'Agotado' si existe)."""
    if "skus_agotados" not in st.session_state:
        agotados_iniciales = set()
        if df_catalogo is not None and not df_catalogo.empty and "SKU" in df_catalogo.columns:
            if "Agotado" in df_catalogo.columns:
                mask_agot = df_catalogo["Agotado"].astype(str).str.lower().isin(["true", "1", "si", "sí", "agotado"])
                agotados_iniciales = set(df_catalogo.loc[mask_agot, "SKU"].astype(str).str.strip())
        st.session_state.skus_agotados = agotados_iniciales


def _es_articulo_agotado(sku, info_producto=None):
    """Devuelve True si el SKU está marcado como agotado en sesión o en su stock/columna."""
    sku_limpio = str(sku).strip()
    if sku_limpio in st.session_state.get("skus_agotados", set()):
        return True
    if info_producto is not None:
        if "Stock" in info_producto.index:
            try:
                if float(info_producto["Stock"]) <= 0:
                    return True
            except Exception:
                pass
    return False


def mostrar(df_catalogo, monto_mayoreo_1, monto_mayoreo_2, monto_especial, sucursal_activa="Tienda Chela"):
    st.title("🛒 Control de Ventas")

    _inicializar_agotados(df_catalogo)

    # --- OBTENER USUARIO LOGUEADO EN SESIÓN ---
    usuario_actual = st.session_state.get("username", st.session_state.get("usuario", "Mostrador"))

    # --- VALIDACIÓN DE HORARIO EN ZONA HORARIA DE MÉXICO ---
    zona_mx = zoneinfo.ZoneInfo("America/Mexico_City")
    ahora_actual = datetime.now(zona_mx)
    hora_actual = ahora_actual.hour  # 0 a 23 hrs
    anio_actual = ahora_actual.year

    horario_permitido = 8 <= hora_actual < 19

    if not horario_permitido:
        st.warning(f"⏰ **Horario de ventas cerrado.** El registro de ventas solo está disponible de **8:00 AM a 7:00 PM**. (Hora local actual: {ahora_actual.strftime('%I:%M %p')})")

    # --- AUTOMATIZACIÓN DEL FOLIO DE TICKET ---
    if "numero_ticket_auto" not in st.session_state:
        siguiente_num = obtener_siguiente_folio(anio_actual)
        st.session_state.numero_ticket_auto = f"TCK-{anio_actual}-{siguiente_num}"

    lista_recurrentes_nombres = obtener_clientes_recurrentes_lista()

    col_tipo_cte, col_toggle = st.columns([2, 1])
    with col_tipo_cte:
        tipo_cliente = st.radio(
            "Selecciona el Tipo de Cliente:",
            ["⭐ Cliente Recurrente (Lista)", "🆕 Nuevo Cliente / General"],
            horizontal=True
        )

        if tipo_cliente == "⭐ Cliente Recurrente (Lista)":
            if lista_recurrentes_nombres:
                cliente = st.selectbox(
                    "Selecciona el Cliente Recurrente:", 
                    options=lista_recurrentes_nombres,
                    index=0,
                    help="Escribe para autocompletar o despliega la lista."
                )
            else:
                st.info("Aún no hay clientes recurrentes dados de alta. Ingresa el nombre como nuevo cliente.")
                cliente = st.text_input("Nombre del Cliente / Negocio", value="Público General")
        else:
            cliente = st.text_input("Nombre del Cliente / Negocio", value="Público General")

    with col_toggle:
        st.write("") 
        st.write("")
        permitir_manual = st.toggle("🔓 Habilitar Selección Manual de Mayoreo", value=False, help="Activa esta opción si deseas forzar un nivel de mayoreo específico general.")

    if permitir_manual:
        st.warning("⚠️ **Modo manual activo:** El nivel de precio seleccionado manualmente se aplicará al carrito.")

    es_cliente_recurrente_preferente = (cliente.strip().lower() in [c.lower() for c in lista_recurrentes_nombres]) and (cliente.strip().lower() != "público general")

    if es_cliente_recurrente_preferente:
        st.success(f"⭐ **Cliente Recurrente Confirmado:** '{cliente.strip()}' cuenta con **Precio Mayoreo 1 garantizado** desde 1 pieza.")

    total_compras_historico_cliente = 0.0
    if cliente.strip().lower() != "público general":
        try:
            df_ventas_hist = obtener_historial_ventas()
            if not df_ventas_hist.empty and "Cliente" in df_ventas_hist.columns:
                df_cte_prev = df_ventas_hist[df_ventas_hist["Cliente"].astype(str).str.strip().str.lower() == cliente.strip().lower()]
                if "Total_Venta" in df_cte_prev.columns:
                    total_compras_historico_cliente = pd.to_numeric(df_cte_prev["Total_Venta"], errors='coerce').sum()
        except:
            total_compras_historico_cliente = 0.0

    if "carrito" not in st.session_state:
        st.session_state.carrito = []

    monto_bruto_carrito = sum(item["Cantidad"] * item["Precio_Menudeo"] for item in st.session_state.carrito)
    monto_evaluacion = max(total_compras_historico_cliente, monto_bruto_carrito)

    def obtener_nivel_por_monto(monto, es_recurrente):
        if monto >= monto_especial:
            return "Especial / Distribuidor (Precio 4)"
        elif monto >= monto_mayoreo_2:
            return "Mayoreo Nivel 2 (Precio 3)"
        elif monto >= monto_mayoreo_1 or es_recurrente:
            return "Mayoreo Nivel 1 (Precio 2)"
        else:
            return "Menudeo (Precio 1)"

    # --- PANEL PARA MARCAR ARTÍCULOS AGOTADOS EN CATÁLOGO ---
    with st.expander("⚙️ Panel de Catálogo: Marcar Artículos Agotados", expanded=False):
        st.caption(f"Total marcados como agotados en esta sesión: **{len(st.session_state.skus_agotados)}**")
        filtro_panel_agotados = st.text_input(
            "Filtrar artículos en el panel de agotados:",
            placeholder="Escribe SKU o nombre para marcar/desmarcar...",
            key="filtro_panel_agotados"
        )

        if df_catalogo is not None and not df_catalogo.empty:
            if filtro_panel_agotados.strip() != "":
                mask_p = (
                    df_catalogo["Producto"].astype(str).str.contains(filtro_panel_agotados, case=False, na=False)
                    | df_catalogo["SKU"].astype(str).str.contains(filtro_panel_agotados, case=False, na=False)
                )
                df_panel = df_catalogo.loc[mask_p].head(30)
            else:
                df_panel = df_catalogo.head(30)
                if len(df_catalogo) > 30:
                    st.info("Mostrando los primeros 30 artículos. Usa el buscador de arriba para filtrar cualquier otro.")

            for idx_row, fila in df_panel.iterrows():
                sku_item = str(fila["SKU"]).strip()
                prod_item = str(fila["Producto"]).strip()
                esta_agotado_actual = sku_item in st.session_state.skus_agotados

                col_p1, col_p2 = st.columns([3.5, 1.5])
                with col_p1:
                    etiqueta_estado = "🔴 AGOTADO" if esta_agotado_actual else "🟢 Disponible"
                    st.write(f"**{sku_item}** - {prod_item} · {etiqueta_estado}")
                with col_p2:
                    marcado = st.checkbox(
                        "Agotado",
                        value=esta_agotado_actual,
                        key=f"chk_agotado_{sku_item}_{idx_row}"
                    )
                    if marcado != esta_agotado_actual:
                        if marcado:
                            st.session_state.skus_agotados.add(sku_item)
                        else:
                            st.session_state.skus_agotados.discard(sku_item)
                        st.rerun()

    st.markdown("### 🛍️ Búsqueda y Selección de Producto")
    busqueda_texto = st.text_input("🔍 Buscar producto (nombre o SKU):", placeholder="Ej. Cobertor, Sábanas...")

    if busqueda_texto.strip() != "":
        mask = df_catalogo["Producto"].astype(str).str.contains(busqueda_texto, case=False, na=False) | \
               df_catalogo["SKU"].astype(str).str.contains(busqueda_texto, case=False, na=False)
        df_filtrado = df_catalogo.loc[mask]
    else:
        df_filtrado = df_catalogo

    # Advertencia general si al buscar aparece al menos un artículo agotado
    if busqueda_texto.strip() != "" and not df_filtrado.empty:
        skus_filtrados_agotados = [
            f"{str(r['SKU'])} - {str(r['Producto'])}"
            for _, r in df_filtrado.iterrows()
            if _es_articulo_agotado(r["SKU"], r)
        ]
        if skus_filtrados_agotados:
            st.warning(
                f"⚠️ **Advertencia de inventario:** Se encontraron **{len(skus_filtrados_agotados)}** artículo(s) **AGOTADO(S)** en tu búsqueda: "
                + ", ".join(skus_filtrados_agotados[:5])
                + ("..." if len(skus_filtrados_agotados) > 5 else "")
            )

    col1, col2 = st.columns([3, 1])

    sku = None
    info_producto = None
    articulo_seleccionado_agotado = False

    with col1:
        if not df_filtrado.empty:
            def _formatear_opcion(row):
                s_val = str(row["SKU"]).strip()
                p_val = str(row["Producto"]).strip()
                prefijo = "⛔ [AGOTADO] " if _es_articulo_agotado(s_val, row) else ""
                return f"{prefijo}{s_val} - {p_val}"

            opciones_productos = [_formatear_opcion(r) for _, r in df_filtrado.iterrows()]
            producto_seleccionado = st.selectbox("Resultados de Búsqueda", opciones_productos)

            # Extraer SKU limpio quitando el prefijo si existe
            texto_sin_prefijo = producto_seleccionado.replace("⛔ [AGOTADO] ", "", 1)
            sku = texto_sin_prefijo.split(" - ")[0].strip()
            info_producto = df_catalogo[df_catalogo["SKU"].astype(str).str.strip() == sku].iloc[0]
            articulo_seleccionado_agotado = _es_articulo_agotado(sku, info_producto)
        else:
            st.warning("No se encontraron productos.")
            sku = None

    with col2:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)

    permitir_agregar_agotado = True
    if sku is not None and not df_filtrado.empty and articulo_seleccionado_agotado:
        st.error(f"⛔ **ARTÍCULO AGOTADO:** **{info_producto['Producto']}** (SKU: `{sku}`) está marcado actualmente como **AGOTADO**.")
        permitir_agregar_agotado = st.checkbox(
            "Confirmar que deseo agregar este artículo agotado de todas formas (ej. cotización o encargo)",
            value=False,
            key=f"confirmar_agotado_{sku}"
        )

    if permitir_manual:
        dict_precios_keys = [
            "Menudeo (Precio 1)", 
            "Mayoreo Nivel 1 (Precio 2)", 
            "Mayoreo Nivel 2 (Precio 3)", 
            "Especial / Distribuidor (Precio 4)"
        ]
        nivel_manual_elegido = st.selectbox("Nivel de Precio Manual Global", dict_precios_keys)
    else:
        nivel_manual_elegido = None

    if sku is not None and not df_filtrado.empty:
        if st.button("➕ Agregar al Carrito", use_container_width=True, disabled=not permitir_agregar_agotado):
            st.session_state.carrito.append({
                "SKU": sku,
                "Producto": info_producto["Producto"],
                "Precio_Menudeo": float(info_producto.get("Precio_Menudeo", 0.0)),
                "Precio_Mayoreo_1": float(info_producto.get("Precio_Mayoreo_1", 0.0)),
                "Precio_Mayoreo_2": float(info_producto.get("Precio_Mayoreo_2", 0.0)),
                "Precio_Especial": float(info_producto.get("Precio_Especial", 0.0)),
                "Costo_Unitario": float(info_producto.get("Costo", 0.0)),
                "Cantidad": cantidad
            })
            st.success(f"Agregado: {info_producto['Producto']}")
            st.rerun()

    # ... el resto de tu código continúa igual ...
