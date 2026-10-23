# --- VISUALIZADOR Y BOTÓN DE IMPRESIÓN BLUETOOTH MTP-2 ---
    if "ultimo_ticket" in st.session_state and st.session_state.ultimo_ticket:
        t = st.session_state.ultimo_ticket
        st.markdown("---")
        st.markdown("### 🖨️ Ticket Generado - Impresión Bluetooth MTP-2")
        
        # Generar líneas de productos formateadas para JavaScript ESC/POS
        lineas_js = ""
        for itm in t["items"]:
            prod_clean = str(itm['Producto']).replace('"', '\\"')
            lineas_js += f'escpos += "{prod_clean}\\n";\n'
            lineas_js += f'escpos += "  Cant: {int(itm["Cantidad"])} | Total: ${itm["Total_Venta"]:,.2f}\\n";\n'

        sucursal_str = str(t['sucursal'])
        fecha_str = str(t['fecha'])
        cliente_str = str(t['cliente'])
        total_str = f"${t['total']:,.2f}"

        items_html = '<br>'.join([f"{itm['Producto']}<br>&nbsp;&nbsp;Cant: {int(itm['Cantidad'])} | Total: ${itm['Total_Venta']:,.2f}" for itm in t['items']])

        bluetooth_vta_html = f"""
        <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; max-width: 320px; font-family: 'Courier New', monospace;">
            <div style="text-align: center; font-weight: bold; font-size: 14px;">TEXTIL ANIT MARI</div>
            <div style="text-align: center; font-size: 11px;">Sucursal: {sucursal_str}</div>
            <div style="text-align: center; font-size: 11px;">{fecha_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="font-size: 11px;">Cliente: {cliente_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="font-size: 11px;">
                {items_html}
            </div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="text-align: right; font-weight: bold; font-size: 13px;">TOTAL: {total_str}</div>
            <div style="border-top: 1px dashed #000; margin: 6px 0;"></div>
            <div style="text-align: center; font-size: 10px;">¡Gracias por su compra!</div>
            
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
                escpos += "TEXTIL ANIT MARI\\n";
                escpos += "Sucursal: {sucursal_str}\\n";
                escpos += "{fecha_str}\\n";
                escpos += "--------------------------------\\n";
                escpos += "\\x1B\\x61\\x00"; // Izquierda
                escpos += "Cliente: {cliente_str}\\n";
                escpos += "--------------------------------\\n";
                
                {lineas_js}

                escpos += "--------------------------------\\n";
                escpos += "\\x1B\\x61\\x02"; // Derecha
                escpos += "TOTAL: {total_str}\\n\\n";
                escpos += "\\x1B\\x61\\x01"; // Centrar
                escpos += "¡Gracias por su compra!\\n\\n\\n";

                const encoder = new TextEncoder();
                await writeCharacteristic.writeValue(encoder.encode(escpos));

                estado.innerText = "✅ ¡Ticket impreso con éxito en MTP-2!";
            }} catch (error) {{
                estado.innerText = "❌ Error: " + error.message;
            }}
        }}
        </script>
        """
        components.html(bluetooth_vta_html, height=420)
        
        if st.button("✖️ Cerrar Vista y Nuevo Ticket"):
            del st.session_state.ultimo_ticket
            st.rerun()
