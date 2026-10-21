import streamlit as st
import pandas as pd
from datetime import datetime
import os
from .base_datos import obtener_clientes_recurrentes_lista, guardar_venta_db, obtener_historial_ventas

def mostrar(df_catalogo, monto_mayoreo_1, monto_mayoreo_2, monto_especial,sucursal_activa="Tienda Chela"):
    st.title("🛒 Control de Ventas")

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
                cliente = st.selectbox("Selecciona el Cliente Recurrente:", lista_recurrentes_nombres)
            else:
                st.info("Aún no hay clientes recurrentes dados de alta. Ingresa el nombre como nuevo cliente.")
                cliente = st.text_input("Nombre del Cliente / Negocio", value="Público General")
        else:
            cliente = st.text_input("Nombre del Cliente / Negocio", value="Público General")

    with col_toggle:
        st.write("") 
        st.write("")
        permitir_manual = st.toggle("🔓 Habilitar Selección Manual de Mayoreo", value=False, help="Activa esta opción si deseas forzar un nivel de mayoreo específico.")

    if permitir_manual:
        st.warning("⚠️ **Modo manual activo:** El nivel de precio seleccionado manualmente se aplicará al producto agregado.")

    es_cliente_recurrente_preferente = (cliente.strip().lower() in [c.lower() for c in lista_recurrentes_nombres]) and (cliente.strip().lower() != "público general")

    if es_cliente_recurrente_preferente:
        st.success(f"⭐ **Cliente Recurrente Confirmado:** '{cliente.strip()}' cuenta con **Precio Mayoreo 1 garantizado** desde 1 pieza.")

total_compras_historico_cliente = 0.0
    if cliente.strip().lower() != "público general":
        try:
            df_ventas_hist = obtener_historial_ventas()
            if not df_ventas_hist.empty and "Cliente" in df_ventas_hist.columns:
                df_cte_prev = df_ventas_hist[df_ventas_hist["Cliente"].astype(str).str.strip().str.lower() == cliente.strip().lower()]
                total_compras_historico_cliente = df_cte_prev["Total_Venta"].sum()
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

    st.markdown("### 🛍️ Búsqueda y Selección de Producto")
    busqueda_texto = st.text_input("🔍 Buscar producto (nombre o SKU):", placeholder="Ej. Cobertor, Sábanas...")

    if busqueda_texto.strip() != "":
        mask = df_catalogo["Producto"].astype(str).str.contains(busqueda_texto, case=False, na=False) | \
               df_catalogo["SKU"].astype(str).str.contains(busqueda_texto, case=False, na=False)
        df_filtrado = df_catalogo.loc[mask]
    else:
        df_filtrado = df_catalogo

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if not df_filtrado.empty:
            opciones_productos = df_filtrado["SKU"].astype(str) + " - " + df_filtrado["Producto"].astype(str)
            producto_seleccionado = st.selectbox("Resultados de Búsqueda", opciones_productos)
            sku = producto_seleccionado.split(" - ")[0]
            info_producto = df_catalogo[df_catalogo["SKU"].astype(str) == sku].iloc[0]
        else:
            st.warning("No se encontraron productos.")
            sku = None

    with col2:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)

    with col3:
        if sku is not None and not df_filtrado.empty:
            estimacion_bruta = max(monto_evaluacion, monto_bruto_carrito + (cantidad * float(info_producto.get("Precio_Menudeo", 0.0))))
            nivel_sugerido_linea = obtener_nivel_por_monto(estimacion_bruta, es_cliente_recurrente_preferente)

            dict_precios = {
                "Menudeo (Precio 1)": info_producto.get("Precio_Menudeo", 0.0),
                "Mayoreo Nivel 1 (Precio 2)": info_producto.get("Precio_Mayoreo_1", info_producto.get("Precio_Menudeo", 0.0)),
                "Mayoreo Nivel 2 (Precio 3)": info_producto.get("Precio_Mayoreo_2", info_producto.get("Precio_Mayoreo_1", info_producto.get("Precio_Menudeo", 0.0))),
                "Especial / Distribuidor (Precio 4)": info_producto.get("Precio_Especial", info_producto.get("Precio_Mayoreo_1", info_producto.get("Precio_Menudeo", 0.0)))
            }
            
            keys_precios = list(dict_precios.keys())
            idx_default = keys_precios.index(nivel_sugerido_linea) if nivel_sugerido_linea in keys_precios else 0

            nivel_elegido = st.selectbox(
                "Nivel de Precio Aplicado", 
                keys_precios, 
                index=idx_default, 
                disabled=not permitir_manual
            )
        else:
            nivel_elegido = None

    if sku is not None and not df_filtrado.empty:
        if st.button("➕ Agregar al Carrito", use_container_width=True):
            st.session_state.carrito.append({
                "SKU": sku,
                "Producto": info_producto["Producto"],
                "Precio_Menudeo": float(info_producto.get("Precio_Menudeo", 0.0)),
                "Precio_Mayoreo_1": float(info_producto.get("Precio_Mayoreo_1", 0.0)),
                "Precio_Mayoreo_2": float(info_producto.get("Precio_Mayoreo_2", 0.0)),
                "Precio_Especial": float(info_producto.get("Precio_Especial", 0.0)),
                "Costo_Unitario": float(info_producto.get("Costo", 0.0)),
                "Cantidad": cantidad,
                "Override_Nivel": nivel_elegido if permitir_manual else None
            })
            st.success(f"Agregado: {info_producto['Producto']}")
            st.rerun()

    if len(st.session_state.carrito) > 0:
        st.markdown("---")
        st.markdown("### 📋 Resumen del Ticket Actual")

        monto_bruto_total = sum(item["Cantidad"] * item["Precio_Menudeo"] for item in st.session_state.carrito)
        monto_evaluar_global = max(total_compras_historico_cliente, monto_bruto_total)
        nivel_global_alcanzado = obtener_nivel_por_monto(monto_evaluar_global, es_cliente_recurrente_preferente)

        if nivel_global_alcanzado == "Especial / Distribuidor (Precio 4)":
            st.success(f"⭐ **¡Umbral Especial Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN (≥${monto_especial:,.2f}). **Todos los productos adoptan Precio Especial.**")
        elif nivel_global_alcanzado == "Mayoreo Nivel 2 (Precio 3)":
            st.info(f"⭐ **¡Umbral Mayoreo 2 Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN (≥${monto_mayoreo_2:,.2f}). **Todos los productos adoptan Mayoreo 2.**")
        elif nivel_global_alcanzado == "Mayoreo Nivel 1 (Precio 2)":
            if es_cliente_recurrente_preferente and monto_evaluar_global < monto_mayoreo_1:
                st.info(f"⭐ **Cliente Recurrente:** Se aplica **Mayoreo Nivel 1** garantizado por lista preferente.")
            else:
                st.info(f"⭐ **¡Umbral Mayoreo 1 Alcanzado!** Subtotal regular: ${monto_bruto_total:,.2f} MXN (≥${monto_mayoreo_1:,.2f}). **Todos los productos adoptan Mayoreo 1.**")

        total_general = 0.0
        indices_a_eliminar = []

        for idx, item in enumerate(st.session_state.carrito):
            if item.get("Override_Nivel"):
                nivel_aplicado = item["Override_Nivel"]
            else:
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

            cols_fila = st.columns([1.2, 3, 2.2, 1.2, 1.2, 1.2])
            cols_fila[0].write(f"**{item['SKU']}**")
            cols_fila[1].write(item['Producto'])
            cols_fila[2].write(f"*{nivel_aplicado}*")
            cols_fila[3].write(f"${precio_unitario:,.2f}")
            cols_fila[4].write(f"{item['Cantidad']} pza(s)")
            cols_fila[5].write(f"**${total_linea:,.2f}**")

            if st.button("🗑️ Quitar", key=f"del_{idx}"):
                indices_a_eliminar.append(idx)

        if indices_a_eliminar:
            for i in sorted(indices_a_eliminar, reverse=True):
                st.session_state.carrito.pop(i)
            st.rerun()

        st.markdown("---")
        st.markdown(f"### 💰 **Total a Pagar:** `${total_general:,.2f} MXN`")

        col_acc1, col_acc2 = st.columns(2)
        with col_acc1:
            if st.button("🗑️ Vaciar Carrito Completo", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()

        with col_acc2:
            if st.button("✅ Confirmar y Guardar Venta Completa", use_container_width=True):
                ahora = datetime.now()
                items_finales = []
                for item in st.session_state.carrito:
                    if item.get("Override_Nivel"):
                        nivel_aplicado = item["Override_Nivel"]
                    else:
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
                        "SKU": item["SKU"],
                        "Producto": item["Producto"],
                        "Nivel_Precio": nivel_aplicado,
                        "Precio_Unitario": p_unit,
                        "Costo_Unitario": item["Costo_Unitario"],
                        "Cantidad": item["Cantidad"],
                        "Total_Venta": t_linea,
                        "Costo_Total": c_total,
                        "Ganancia": ganancia,
                        "Fecha_Hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                        "Fecha": ahora.strftime("%Y-%m-%d"),
                        "Cliente": cliente.strip()
                    })

                df_final_venta = pd.DataFrame(items_finales)
                if os.path.exists(VENTAS_FILE):
                    df_final_venta.to_csv(VENTAS_FILE, mode='a', header=False, index=False)
                else:
                    df_final_venta.to_csv(VENTAS_FILE, index=False)

                st.success(f"¡Venta registrada con éxito para '{cliente.strip()}'!")
                st.session_state.carrito = []
                st.rerun()
    else:
        st.info("El carrito está vacío. Agrega productos arriba.")
