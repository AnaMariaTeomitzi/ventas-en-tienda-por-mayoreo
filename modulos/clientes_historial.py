import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from .base_datos import conectar_db

def mostrar(acceso_propietaria):
    st.title("👥 Historial de Compras por Cliente y Tickets")
    
    tipo, conn = conectar_db()
    try:
        if tipo == "turso":
            rs = conn.execute("SELECT DISTINCT Cliente FROM registro_ventas WHERE Cliente IS NOT NULL AND Cliente != '';")
            clientes = [row[0] for row in rs.rows]
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Cliente FROM registro_ventas WHERE Cliente IS NOT NULL AND Cliente != '';")
            clientes = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        st.error(f"Error al cargar clientes: {e}")
        clientes = []

    if not clientes:
        st.info("No hay clientes con ventas registradas todavía.")
        return

    cliente_sel = st.selectbox("Selecciona un cliente para ver sus tickets e historial:", clientes)

    if cliente_sel:
        try:
            if tipo == "turso":
                rs = conn.execute("SELECT * FROM registro_ventas WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));", (cliente_sel,))
                filas = rs.rows
                columnas = rs.columns if hasattr(rs, 'columns') else []
                df_cliente = pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame()
            else:
                query = "SELECT * FROM registro_ventas WHERE TRIM(LOWER(Cliente)) = TRIM(LOWER(?));"
                df_cliente = pd.read_sql(query, conn, params=(cliente_sel,))

            if not df_cliente.empty:
                # Normalizar columnas numéricas para el resumen general
                if "Total_Venta" in df_cliente.columns:
                    df_cliente["Total_Venta"] = pd.to_numeric(df_cliente["Total_Venta"], errors='coerce').fillna(0)
                    total_compras = df_cliente["Total_Venta"].sum()
                else:
                    total_compras = 0.0

                if "Ganancia" in df_cliente.columns:
                    df_cliente["Ganancia"] = pd.to_numeric(df_cliente["Ganancia"], errors='coerce').fillna(0)
                    ganancia_total = df_cliente["Ganancia"].sum()
                else:
                    ganancia_total = 0.0
                
                # Fondo Navideño (10%)
                porcentaje_navideno = 0.10 
                fondo_navideno = ganancia_total * porcentaje_navideno

                st.markdown(f"### Resumen General para: **{cliente_sel}**")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("💵 Total Compras", f"${total_compras:,.2f} MXN")
                col2.metric("⭐ Ganancia Generada", f"${ganancia_total:,.2f} MXN", help="Utilidad neta generada por este cliente.")
                col3.metric("🎄 Fondo Navideño (10%)", f"${fondo_navideno:,.2f} MXN", help="Porcentaje reservado exclusivamente de la ganancia para regalo o reembolso de fin de año.")

                st.markdown("---")
                st.markdown("### 🎫 Tickets Registrados del Cliente")

                if "Numero_Ticket" in df_cliente.columns:
                    df_cliente["Numero_Ticket"] = df_cliente["Numero_Ticket"].fillna("S/N").astype(str)
                    tickets_unicos = df_cliente["Numero_Ticket"].unique()
                else:
                    tickets_unicos = ["S/N"]

                for t_idx, num_tk in enumerate(tickets_unicos):
                    df_tk = df_cliente[df_cliente["Numero_Ticket"] == num_tk] if "Numero_Ticket" in df_cliente.columns else df_cliente
                    
                    fecha_tk = df_tk["Fecha_Hora"].iloc[0] if "Fecha_Hora" in df_tk.columns and not df_tk["Fecha_Hora"].empty else "Fecha no registrada"
                    sucursal_tk = df_tk["Sucursal"].iloc[0] if "Sucursal" in df_tk.columns and not df_tk["Sucursal"].empty else "Tienda Chela"
                    tipo_op_tk = df_tk["Tipo_Operacion"].iloc[0] if "Tipo_Operacion" in df_tk.columns and not df_tk["Tipo_Operacion"].empty else "Venta"
                    metodo_pago_tk = df_tk["Metodo_Pago"].iloc[0] if "Metodo_Pago" in df_tk.columns and not df_tk["Metodo_Pago"].empty else "N/A"
                    monto_recibido_tk = float(df_tk["Monto_Recibido"].iloc[0]) if "Monto_Recibido" in df_tk.columns and not df_tk["Monto_Recibido"].empty else 0.0
                    cambio_tk = float(df_tk["Cambio"].iloc[0]) if "Cambio" in df_tk.columns and not df_tk["Cambio"].empty else 0.0
                    atendido_tk = df_tk["Atendido_Por"].iloc[0] if "Atendido_Por" in df_tk.columns and not df_tk["Atendido_Por"].empty else "Mostrador"
                    
                    total_tk = df_tk["Total_Venta"].sum() if "Total_Venta" in df_tk.columns else 0.0

                    with st.expander(f"🎫 Folio: {num_tk} | 📅 {fecha_tk} | 💰 Total: ${total_tk:,.2f} MXN"):
                        st.write(f"**Sucursal:** {sucursal_tk} | **Tipo:** {tipo_op_tk} | **Atendió:** {atendido_tk}")
                        st.write(f"**Método de Pago:** {metodo_pago_tk}")
                        
                        cols_det = ["SKU", "Producto", "Nivel_Precio", "Precio_Unitario", "Cantidad", "Total_Venta"]
                        cols_existentes = [c for c in cols_det if c in df_tk.columns]
                        st.dataframe(df_tk[cols_existentes], use_container_width=True)

                        if st.button(f"🖨️ Reimprimir Ticket {num_tk}", key=f"reimp_{num_tk}_{t_idx}"):
                            items_lista_reimp = []
                            for _, row_i in df_tk.iterrows():
                                items_lista_reimp.append({
                                    "Producto": row_i.get("Producto", "Artículo"),
                                    "Cantidad": row_i.get("Cantidad", 1),
                                    "Total_Venta": row_i.get("Total_Venta", 0.0)
                                })

                            st.session_state.ultimo_ticket = {
                                "tipo_operacion": tipo_op_tk,
                                "numero_ticket": num_tk,
                                "cliente": cliente_sel,
                                "sucursal": sucursal_tk,
                                "atendido_por": atendido_tk,
                                "fecha": fecha_tk,
                                "items": items_lista_reimp,
                                "total": total_tk,
                                "metodo_pago": metodo_pago_tk,
                                "monto_recibido": monto_recibido_tk if monto_recibido_tk > 0 else total_tk,
                                "cambio": cambio_tk,
                                "referencia": ""
                            }
                            st.success(f"¡Ticket {num_tk} cargado para reimpresión!")
                            st.rerun()

                # --- VISUALIZADOR Y BOTÓN DE IMPRESIÓN FUERA DEL CICLO ---
                if "ultimo_ticket" in st.session_state and st.session_state.ultimo_ticket:
                    t = st.session_state.ultimo_ticket
                    st.markdown("---")
                    st.markdown(f"### 🖨️ Vista Previa de Reimpresión - Ticket: {t.get('numero_ticket', '')}")
                    
                    lineas_js = ""
                    for itm in t["items"]:
                        prod_clean = str(itm['Producto']).replace('"', '\\"')
                        lineas_js += f'escpos += "{prod_clean}\\n";\n'
                        lineas_js += f'escpos += "  Cant: {int(itm["Cantidad"])} | Total: ${itm["Total_Venta"]:,.2f}\\n";\n'

                    sucursal_str = str(t['sucursal'])
                    atendido_str = str(t.get('atendido_por', 'Mostrador'))
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
                        
                        <div style="text-align: center; font-size: 11px; margin: 8px 0;">
                            <b>Tel: 246 757 61 27</b><br>
                            Horario: 11:00 am a 7:00 pm
                        </div>
                        
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

                            let escpos = "\\x1B\\x40"; 
                            escpos += "\\x1B\\x61\\x01"; 
                            escpos += "TEXTILES CONCEPCION\\n";
                            escpos += "*** {tipo_op_str.upper()} ***\\n";
                            {f'escpos += "{ticket_linea_escpos}\\n";' if num_ticket_str else ''}
                            escpos += "--------------------------------\\n";
                            escpos += "Sucursal: {sucursal_str}\\n";
                            escpos += "Atendio: {atendido_str}\\n";
                            escpos += "{fecha_str}\\n";
                            escpos += "--------------------------------\\n";
                            escpos += "\\x1B\\x61\\x00"; 
                            escpos += "Cliente: {cliente_str}\\n";
                            escpos += "--------------------------------\\n";
                            
                            {lineas_js}

                            escpos += "--------------------------------\\n";
                            escpos += "{pago_info_escpos}";
                            escpos += "--------------------------------\\n";
                            escpos += "\\x1B\\x61\\x02"; 
                            escpos += "TOTAL: {total_str}\\n\\n";
                            
                            escpos += "\\x1B\\x61\\x01"; 
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
                        } catch (error) {{
                            estado.innerText = "❌ Error: " + error.message;
                        }}
                    }}
                    </script>
                    """
                    components.html(bluetooth_vta_html, height=620)
                    
                    if st.button("✖️ Cerrar Vista de Reimpresión"):
                        del st.session_state.ultimo_ticket
                        st.rerun()

            else:
                st.info("Este cliente no tiene compras registradas en el sistema.")

        except Exception as e:
            st.error(f"Error al generar el historial del cliente: {e}")
