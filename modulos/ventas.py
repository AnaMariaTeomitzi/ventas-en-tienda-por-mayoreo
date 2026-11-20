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
    if info_producto is not None and "Stock" in info_producto.index:
        try:
            if float(info_producto["Stock"]) <= 0:
                return True
        except Exception:
            pass
    return False


@st.dialog("⚙️ Panel de Catálogo: Artículos Agotados", width="large")
def _modal_gestionar_agotados(df_catalogo):
    """Ventana emergente para marcar o desmarcar artículos agotados en el catálogo."""
    st.caption(f"Artículos actualmente marcados como agotados: **{len(st.session_state.skus_agotados)}**")

    filtro_modal = st.text_input(
        "🔍 Filtrar por SKU o nombre:",
        placeholder="Ej. Cobertor, Sábana, SKU...",
        key="filtro_modal_agotados"
    )

    if df_catalogo is None or df_catalogo.empty:
        st.info("No hay artículos en el catálogo para mostrar.")
        return

    if filtro_modal.strip() != "":
        mask_m = (
            df_catalogo["Producto"].astype(str).str.contains(filtro_modal, case=False, na=False)
            | df_catalogo["SKU"].astype(str).str.contains(filtro_modal, case=False, na=False)
        )
        df_vista = df_catalogo.loc[mask_m].head(40)
    else:
        df_vista = df_catalogo.head(40)
        if len(df_catalogo) > 40:
            st.caption("Mostrando los primeros 40 artículos. Escribe arriba para filtrar más.")

    with st.form("form_modal_agotados"):
        seleccion_temporal = {}

        for idx_row, fila in df_vista.iterrows():
            sku_item = str(fila["SKU"]).strip()
            prod_item = str(fila["Producto"]).strip()
            esta_agotado_actual = sku_item in st.session_state.skus_agotados

            c1, c2 = st.columns([4, 1.2])
            with c1:
                estado_txt = "🔴 AGOTADO" if esta_agotado_actual else "🟢 Disponible"
                st.write(f"**{sku_item}** — {prod_item} · {estado_txt}")
            with c2:
                seleccion_temporal[sku_item] = st.checkbox(
                    "Agotado",
                    value=esta_agotado_actual,
                    key=f"modal_chk_{sku_item}_{idx_row}"
                )

        guardar_cambios = st.form_submit_button("💾 Guardar cambios de agotados", type="primary", use_container_width=True)

        if guardar_cambios:
            for sku_k, marcado_v in seleccion_temporal.items():
                if marcado_v:
                    st.session_state.skus_agotados.add(sku_k)
                else:
                    st.session_state.skus_agotados.discard(sku_k)
            st.rerun()


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

    # --- BÚSQUEDA Y BOTÓN DE VENTANA EMERGENTE DE AGOTADOS ---
    st.markdown("### 🛍️ Búsqueda y Selección de Producto")
    col_busq, col_btn_modal = st.columns([3.5, 1.5])

    with col_busq:
        busqueda_texto = st.text_input("🔍 Buscar producto (nombre o SKU):", placeholder="Ej. Cobertor, Sábanas...")

    with col_btn_modal:
        st.write("")
        st.write("")
        if st.button(f"⚙️ Agotados ({len(st.session_state.skus_agotados)})", use_container_width=True):
            _modal_gestionar_agotados(df_catalogo)

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

    if len(st.session_state.carrito) > 0:
        st.markdown("---")
        st.markdown("### 📋 Resumen del Ticket Actual")

        monto_bruto_total = sum(item["Cantidad"] * item["Precio_Menudeo"] for item in st.session_state.carrito)
        monto_evaluar_global = max(total_compras_historico_cliente, monto_bruto_total)
        
        if permitir_manual and nivel_manual_elegido:
            nivel_global_alcanzado = nivel_manual_elegido
        else:
            nivel_global_alcanzado = obtener_nivel_por_monto(monto_evaluar_global, es_cliente_recurrente_preferente)

        if nivel_global_alcanzado == "Especial / Distribuidor (Precio 4)":
            st.success(f"⭐ **¡Umbral Especial Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN. **Todos los productos adoptan Precio Especial.**")
        elif nivel_global_alcanzado == "Mayoreo Nivel 2 (Precio 3)":
            st.info(f"⭐ **¡Umbral Mayoreo 2 Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN. **Todos los productos adoptan Mayoreo 2.**")
        elif nivel_global_alcanzado == "Mayoreo Nivel 1 (Precio 2)":
            if es_cliente_recurrente_preferente and monto_evaluar_global < monto_mayoreo_1:
                st.info(f"⭐ **Cliente Recurrente:** Se aplica **Mayoreo Nivel 1** garantizado por lista preferente.")
            else:
                st.info(f"⭐ **¡Umbral Mayoreo 1 Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN. **Todos los productos adoptan Mayoreo 1.**")

        total_general = 0.0
        indices_a_eliminar = []

        for idx, item in enumerate(st.session_state.carrito):
            nivel_aplicado = nivel_global_alcanzado

            if nivel_aplicado == "Especial / Distribuidor (Precio 4)":
                precio_unitario = float(item["Precio_Especial"])
            elif nivel_aplicado == "Mayoreo Nivel 2 (Precio 3)":
                precio_unitario = float(item["Precio_Mayoreo_2"])
            elif nivel_aplicado == "Mayoreo Nivel 1 (Precio 2)":
                precio_unitario = float(item["Precio_Mayoreo_1"])
            else:
                precio_unitario = float(item["Precio_Menudeo"])

            total_linea = precio_unitario * item["Cantidad"]
            total_general += total_linea

            cols_fila = st.columns([1.2, 3, 1.2, 1.2, 1.2])
            cols_fila[0].write(f"**{item['SKU']}**")
            cols_fila[1].write(item['Producto'])
            cols_fila[2].write(f"${precio_unitario:,.2f}")
            cols_fila[3].write(f"{item['Cantidad']} pza(s)")
            cols_fila[4].write(f"**${total_linea:,.2f}**")

            if st.button("🗑️ Quitar", key=f"del_{idx}"):
                indices_a_eliminar.append(idx)

        if indices_a_eliminar:
            for i in sorted(indices_a_eliminar, reverse=True):
                st.session_state.carrito.pop(i)
            st.rerun()

        st.markdown("---")
        st.markdown(f"### 💰 **Total a Pagar / Cotizar:** `${total_general:,.2f} MXN`")

        # --- CAMPO NÚMERO DE TICKET AUTOMÁTICO ---
        st.markdown("### 🔢 Folio de Ticket")
        numero_ticket = st.text_input("Número de Ticket Asignado:", value=st.session_state.numero_ticket_auto)

        # --- SECCIÓN: TIPO DE OPERACIÓN Y PAGO ---
        st.markdown("### 💳 Tipo de Operación y Forma de Pago")
        
        tipo_operacion = st.radio(
            "Selecciona el Tipo de Operación:",
            options=["🛒 Venta Confirmada", "📄 Presupuesto / Cotización"],
            horizontal=True
        )

        metodo_pago = "N/A"
        monto_recibido = total_general
        cambio = 0.0
        referencia_pago = ""

        if tipo_operacion == "🛒 Venta Confirmada":
            col_metodo, col_detalle = st.columns([1, 1.2])
            
            with col_metodo:
                metodo_pago = st.selectbox(
                    "Método de Pago:",
                    ["Efectivo 💵", "Transferencia / Mercado Pago 📱", "Tarjeta (Débito/Crédito) 💳"]
                )
                
            with col_detalle:
                if metodo_pago == "Efectivo 💵":
                    monto_recibido = st.number_input(
                        "Monto Recibido de Cliente ($):", 
                        min_value=0.0, 
                        value=float(total_general), 
                        step=10.0,
                        format="%.2f"
                    )
                    cambio = monto_recibido - total_general
                    
                    if monto_recibido >= total_general:
                        st.metric(label="Cambio a Entregar", value=f"${cambio:,.2f} MXN")
                    else:
                        falta = total_general - monto_recibido
                        st.warning(f"⚠️ Cantidad insuficiente. Faltan: **${falta:,.2f} MXN**")

                elif metodo_pago == "Transferencia / Mercado Pago 📱":
                    referencia_pago = st.text_input("Folio / Clave de Rastreo (Opcional):", placeholder="Ej. 123456789")
                    st.info("ℹ️ Asegúrate de verificar que el dinero se refleje en la cuenta antes de finalizar.")

                elif metodo_pago == "Tarjeta (Débito/Crédito) 💳":
                    referencia_pago = st.text_input("Número de Autorización / Voucher (Opcional):", placeholder="Ej. 004521")
        else:
            st.info("ℹ️ **Modo Presupuesto:** No se registrará inventario ni afectará el corte de caja general. Se generará un ticket con desglose de cotización.")

        st.markdown("---")
        col_acc1, col_acc2 = st.columns(2)
        
        with col_acc1:
            if st.button("🗑️ Vaciar Carrito Completo", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()

        with col_acc2:
            pago_valido = True
            if tipo_operacion == "🛒 Venta Confirmada" and metodo_pago == "Efectivo 💵" and monto_recibido < total_general:
                pago_valido = False

            boton_habilitado = pago_valido and (horario_permitido or tipo_operacion == "📄 Presupuesto / Cotización")

            texto_boton = "✅ Confirmar y Guardar Venta" if tipo_operacion == "🛒 Venta Confirmada" else "📄 Generar Presupuesto"
            
            if st.button(texto_boton, type="primary", use_container_width=True, disabled=not boton_habilitado):
                ahora = datetime.now(zona_mx)
                items_finales = []
                for item in st.session_state.carrito:
                    nivel_aplicado = nivel_global_alcanzado

                    if nivel_aplicado == "Especial / Distribuidor (Precio 4)":
                        p_unit = float(item["Precio_Especial"])
                    elif nivel_aplicado == "Mayoreo Nivel 2 (Precio 3)":
                        p_unit = float(item["Precio_Mayoreo_2"])
                    elif nivel_aplicado == "Mayoreo Nivel 1 (Precio 2)":
                        p_unit = float(item["Precio_Mayoreo_1"])
                    else:
                        p_unit = float(item["Precio_Menudeo"])

                    t_linea = p_unit * item["Cantidad"]
                    c_total = item["Costo_Unitario"] * item["Cantidad"]
                    ganancia = t_linea - c_total

                    items_finales.append({
                        "Fecha": ahora.strftime("%Y-%m-%d"),
                        "Sucursal": sucursal_activa,
                        "Cliente": cliente.strip(),
                        "Numero_Ticket": numero_ticket.strip(),
                        "SKU": str(item["SKU"]),
                        "Producto": str(item["Producto"]),
                        "Nivel_Precio": str(nivel_aplicado),
                        "Precio_Unitario": float(p_unit),
                        "Costo_Unitario": float(item["Costo_Unitario"]),
                        "Cantidad": float(item["Cantidad"]),
                        "Total_Venta": float(t_linea),
                        "Costo_Total": float(c_total),
                        "Ganancia": float(ganancia),
                        "Fecha_Hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                        "Tipo_Operacion": tipo_operacion,
                        "Metodo_Pago": metodo_pago,
                        "Monto_Recibido": float(monto_recibido),
                        "Cambio": float(cambio),
                        "Referencia": referencia_pago,
                        "Atendido_Por": usuario_actual
                    })

                df_final_venta = pd.DataFrame(items_finales)
                
                exito = True
                if tipo_operacion == "🛒 Venta Confirmada":
                    exito = guardar_venta_db(df_final_venta)

                if exito:
                    if tipo_operacion == "🛒 Venta Confirmada":
                        st.success(f"⭐ ¡Venta registrada con éxito (Folio: {numero_ticket.strip()})!")
                    else:
                        st.success(f"📄 ¡Presupuesto generado con éxito (Folio: {numero_ticket.strip()})!")
                        
                    st.session_state.ultimo_ticket = {
                        "tipo_operacion": tipo_operacion,
                        "numero_ticket": numero_ticket.strip(),
                        "cliente": cliente.strip(),
                        "sucursal": sucursal_activa,
                        "atendido_por": usuario_actual,
                        "fecha": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                        "items": items_finales,
                        "total": total_general,
                        "metodo_pago": metodo_pago,
                        "monto_recibido": monto_recibido,
                        "cambio": cambio,
                        "referencia": referencia_pago
                    }
                    
                    partes_t = numero_ticket.strip().split("-")
                    if len(partes_t) >= 3 and partes_t[2].isdigit():
                        siguiente_consecutivo = int(partes_t[2]) + 1
                        st.session_state.numero_ticket_auto = f"TCK-{anio_actual}-{siguiente_consecutivo}"
                else:
                    st.error("Hubo un error al guardar la venta en la base de datos.")

                st.session_state.carrito = []
                st.rerun()
    else:
        st.info("El carrito está vacío. Agrega productos arriba.")

    # --- VISUALIZADOR Y BOTÓN DE IMPRESIÓN BLUETOOTH MTP-2 ---
    if "ultimo_ticket" in st.session_state and st.session_state.ultimo_ticket:
        t = st.session_state.ultimo_ticket
        st.markdown("---")
        st.markdown("### 🖨️ Ticket Generado - Impresión Bluetooth MTP-2")
        
        lineas_js = ""
        for itm in t["items"]:
            prod_clean = str(itm['Producto']).replace('"', '\\"')
            lineas_js += f'escpos += "{prod_clean}\\n";\n'
            lineas_js += f'escpos += "  Cant: {int(itm["Cantidad"])} | Total: ${itm["Total_Venta"]:,.2f}\\n";\n'

        sucursal_str = str(t['sucursal'])
        atendido_str = str(t.get('atendido_por', usuario_actual))
        fecha_str = str(t['fecha'])
        cliente_str = str(t['cliente'])
        num_ticket_str = str(t.get('numero_ticket', ''))
        total_str = f"${t['total']:,.2f}"
        tipo_op_str = str(t.get('tipo_operacion', 'VENTA'))
        metodo_pago_str = str(t.get('metodo_pago', 'N/A'))
        monto_recibido_val = float(t.get('monto_recibido', t['total']))
        cambio_val = float(t.get('cambio', 0.0))

        pago_info_html = ""
        pago_info_escpos = ""
        if "Venta" in tipo_op_str:
            pago_info_html += f"Método: {metodo_pago_str}<br>"
            pago_info_escpos += f"Metodo: {metodo_pago_str}\\n"
            if "Efectivo" in metodo_pago_str:
                pago_info_html += f"Recibido: ${monto_recibido_val:,.2f}<br>Cambio:${cambio_val:,.2f}<br>"
                pago_info_escpos += f"Recibido: ${monto_recibido_val:,.2f}\\nCambio:${cambio_val:,.2f}\\n"

        ticket_linea_html = f"<div style='text-align: center; font-size: 12px; font-weight: bold; margin: 4px 0;'>Folio: {num_ticket_str}</div>" if num_ticket_str else ""
        ticket_linea_escpos = f"Folio: {num_ticket_str}\\n" if num_ticket_str else ""

        items_html = '<br>'.join([f"{itm['Producto']}<br>&nbsp;&nbsp;Cant: {int(itm['Cantidad'])} | Total: ${itm['Total_Venta']:,.2f}" for itm in t['items']])

        bluetooth_vta_html = f"""
        <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; max-width: 320px; font-family: 'Courier New', monospace;">
            <div style="text-align: center; font-weight: bold; font-size: 14px;">TEXTILES CONCEPCION</div>
            <div style="text-align: center; font-size: 11px; font-weight: bold;">*** {tipo_op_str.upper()} ***</div>
            {ticket_linea_html}
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="text-align: center; font-size: 11px;">Sucursal: {sucursal_str}</div>
            <div style="text-align: center; font-size: 11px;">Atendió: {atendido_str}</div>
            <div style="text-align: center; font-size: 11px;">{fecha_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="font-size: 11px;">Cliente: {cliente_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="font-size: 11px;">
                {items_html}
            </div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="font-size: 11px;">
                {pago_info_html}
            </div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="text-align: right; font-weight: bold; font-size: 13px;">TOTAL: {total_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            
            <!-- Datos de contacto y horario -->
            <div style="text-align: center; font-size: 11px; margin: 8px 0;">
                <b>Tel: 246 757 61 27</b><br>
                Horario: 11:00 am a 7:00 pm
            </div>
            
            <!-- Vista previa del código QR con textilanitmari.com -->
            <div style="text-align: center; margin: 10px 0;">
                <p style="font-size: 10px; margin-bottom: 4px;">Escanea para visitar nuestra web:</p>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=https://textilanitmari.com" alt="QR Web" style="width: 100px; height: 100px;" />
                <p style="font-size: 10px; font-weight: bold; margin-top: 4px;">www.textilanitmari.com</p>
            </div>

            <div style="text-align: center; font-size: 10px;">¡Gracias por su preferencia!</div>
            
            <br>
            <div style="text-align: center;">
                <button onclick="imprimirVentaMTP2()" style="padding: 12px 18px; font-weight: bold; background: #2e7d32; color: white; border: none; border-radius: 6px; cursor: pointer; width: 100%;">
                    🦷 Imprimir Ticket en MTP-2
                </button>
                <p id="estado_vta_mtp" style="margin-top: 8px; font-size: 12px; color: #333;"></p>
            </div>
        </div>

        <script>
        async function imprimirVentaMTP2() {{
            const estado = document.getElementById("estado_vta_mtp");
            try {{
                estado.innerText = "Conectando a impresora MTP-2...";
                
                const device = await navigator.bluetooth.requestDevice({{
                    acceptAllDevices: true,
                    optionalServices: [
                        '0000ff00-0000-1000-8000-00805f9b34fb', 
                        '00001101-0000-1000-8000-00805f9b34fb',
                        '49535343-fe7d-4ae5-8fa9-9fafd205e455'
                    ]
                }});

                const server = await device.gatt.connect();
                const services = await server.getPrimaryServices();
                
                let writeCharacteristic = null;
                for (const service of services) {{
                    const characteristics = await service.getCharacteristics();
                    for (const char of characteristics) {{
                        if (char.properties.write || char.properties.writeWithoutResponse) {{
                            writeCharacteristic = char;
                            break;
                        }}
                    }}
                    if (writeCharacteristic) break;
                }}

                if (!writeCharacteristic) {{
                    throw new Error("No se encontró canal de escritura en la MTP-2.");
                }}

                estado.innerText = "Enviando ticket a MTP-2...";

                let escpos = "\\x1B\\x40"; // Reset
                escpos += "\\x1B\\x61\\x01"; // Centrar
                escpos += "TEXTILES CONCEPCION\\n";
                escpos += "*** {tipo_op_str.upper()} ***\\n";
                {f'escpos += "{ticket_linea_escpos}\\n";' if num_ticket_str else ''}
                escpos += "--------------------------------\\n";
                escpos += "Sucursal: {sucursal_str}\\n";
                escpos += "Atendio: {atendido_str}\\n";
                escpos += "{fecha_str}\\n";
                escpos += "--------------------------------\\n";
                escpos += "\\x1B\\x61\\x00"; // Izquierda
                escpos += "Cliente: {cliente_str}\\n";
                escpos += "--------------------------------\\n";
                
                {lineas_js}

                escpos += "--------------------------------\\n";
                escpos += "{pago_info_escpos}";
                escpos += "--------------------------------\\n";
                escpos += "\\x1B\\x61\\x02"; // Derecha
                escpos += "TOTAL: {total_str}\\n\\n";
                
                escpos += "\\x1B\\x61\\x01"; // Centrar
                escpos += "Tel: 246 757 61 27\\n";
                escpos += "Horario: 11:00 am a 7:00 pm\\n";
                escpos += "Visita nuestra web:\\n";
                escpos += "textilanitmari.com\\n";
                escpos += "¡Gracias por su preferencia!\\n\\n\\n";

                const encoder = new TextEncoder();
                const data = encoder.encode(escpos);

                const chunkSize = 100;
                for (let i = 0; i < data.length; i += chunkSize) {{
                    const chunk = data.slice(i, i + chunkSize);
                    if (writeCharacteristic.properties.writeWithoutResponse) {{
                        await writeCharacteristic.writeValueWithoutResponse(chunk);
                    }} else {{
                        await writeCharacteristic.writeValue(chunk);
                    }}
                    await new Promise(resolve => setTimeout(resolve, 30));
                }}

                estado.innerText = "✅ ¡Ticket impreso con éxito en MTP-2!";
            }} catch (error) {{
                estado.innerText = "❌ Error: " + error.message;
            }}
        }}
        </script>
        """
        components.html(bluetooth_vta_html, height=620)
        
        if st.button("✖️ Cerrar Vista y Nuevo Ticket"):
            del st.session_state.ultimo_ticket
            st.rerun()
