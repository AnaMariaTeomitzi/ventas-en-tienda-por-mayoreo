import streamlit as st
import pandas as pd
from datetime import datetime
import os
from .base_datos import COMPRAS_FILE

def mostrar(df_catalogo, acceso_propietaria):
    if not acceso_propietaria:
        st.error("⛔ Acceso denegado. Esta sección requiere la contraseña de Propietaria.")
    else:
        st.title("📥 Registro de Compras a Proveedores")
        
        busqueda_compra = st.text_input("🔍 Buscar producto para compra:", placeholder="Escribe nombre o SKU...")
        if busqueda_compra.strip() != "":
            mask_c = df_catalogo["Producto"].astype(str).str.contains(busqueda_compra, case=False, na=False) | \
                     df_catalogo["SKU"].astype(str).str.contains(busqueda_compra, case=False, na=False)
            df_filt_c = df_catalogo.loc[mask_c]
        else:
            df_filt_c = df_catalogo

        c1, c2 = st.columns(2)
        with c1:
            proveedor = st.text_input("Nombre del Proveedor", value="Sola Textil")
            if not df_filt_c.empty:
                opciones_prod = df_filt_c["SKU"].astype(str) + " - " + df_filt_c["Producto"].astype(str)
                prod_sel = st.selectbox("Producto Adquirido", opciones_prod)
                sku_compra = prod_sel.split(" - ")[0]
                nom_producto = df_catalogo[df_catalogo["SKU"].astype(str) == sku_compra].iloc[0]["Producto"]
            else:
                st.warning("No hay productos que coincidan.")
                sku_compra = None

        with c2:
            cant_compra = st.number_input("Cantidad de Piezas", min_value=1, value=12, step=1)
            costo_unit = st.number_input("Costo Unitario ($)", min_value=0.0, value=100.0, step=5.0)
            monto_pagado = st.number_input("Monto Pagado ($)", min_value=0.0, value=0.0, step=100.0)

        if sku_compra is not None:
            total_factura = cant_compra * costo_unit
            monto_pendiente = total_factura - monto_pagado

            st.markdown(f"### **Total Compra:** `${total_factura:,.2f} MXN`")
            if monto_pendiente > 0:
                st.warning(f"⚠️ Saldo pendiente: `${monto_pendiente:,.2f} MXN`")

            if st.button("💾 Guardar Registro de Compra", use_container_width=True):
                ahora = datetime.now()
                nueva_compra = pd.DataFrame([{
                    "Fecha_Hora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                    "Fecha": ahora.strftime("%Y-%m-%d"),
                    "Proveedor": proveedor.strip(),
                    "SKU": sku_compra,
                    "Producto": nom_producto,
                    "Cantidad": cant_compra,
                    "Costo_Unitario": costo_unit,
                    "Total_Compra": total_factura,
                    "Monto_Pagado": monto_pagado,
                    "Saldo_Adeudado": monto_pendiente,
                    "Estado": "Pendiente" if monto_pendiente > 0 else "Pagado"
                }])
                if os.path.exists(COMPRAS_FILE):
                    nueva_compra.to_csv(COMPRAS_FILE, mode='a', header=False, index=False)
                else:
                    nueva_compra.to_csv(COMPRAS_FILE, index=False)
                st.success("Compra registrada correctamente.")
                st.rerun()