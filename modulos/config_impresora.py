import streamlit as st
import streamlit.components.v1 as components

def mostrar():
    st.title("⚙️ Configuración de Impresora y Hardware")
    st.info("Configura la conexión Bluetooth y realiza una prueba directa con tu Goojprt PT-210.")

    if "config_impresora" not in st.session_state:
        st.session_state.config_impresora = {
            "nombre_dispositivo": "PT-210",
            "ancho_papel": "58mm",
            "caracteres_por_linea": 32
        }

    cfg = st.session_state.config_impresora

    st.markdown("### 🖨️ Parámetros de la Impresora Térmica")
    nombre_dev = st.text_input("Nombre de la Impresora:", value=cfg["nombre_dispositivo"])
    ancho_papel = st.selectbox("Ancho de Papel:", ["58mm (Portátil / Goojprt)", "80mm (Mostrador)"], index=0)

    st.markdown("---")
    st.markdown("### 🧪 Conexión Directa por Bluetooth (Web Bluetooth API)")
    st.write("Haz clic en el botón de abajo para buscar tu impresora **Goojprt PT-210** por Bluetooth y enviar un ticket de prueba directo sin pasar por los menús del navegador.")

    # Componente interactivo con JavaScript para Web Bluetooth
    bluetooth_html = """
    <div style="text-align: center; padding: 5px;">
        <button onclick="conectarEImprimir()" style="padding: 10px 18px; font-size: 15px; font-weight: bold; background: #2e7d32; color: white; border: none; border-radius: 6px; cursor: pointer;">
            🦷 Conectar e Imprimir Prueba Bluetooth
        </button>
        <p id="estado" style="margin-top: 8px; font-family: monospace; font-size: 12px; color: #333;"></p>
    </div>

    <script>
    async function conectarEImprimir() {
        const estado = document.getElementById("estado");
        try {
            estado.innerText = "Buscando dispositivo Bluetooth (Selecciona tu PT-210)...";
            
            // Solicitar dispositivo Bluetooth permitiendo cualquier dispositivo cercano
            const device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: ['0000ff00-0000-1000-8000-00805f9b34fb', '49535343-fe7d-4ae5-8fa9-9fafd205e455', '00001101-0000-1000-8000-00805f9b34fb']
            });

            estado.innerText = "Conectando a " + (device.name || "Impresora") + "...";
            const server = await device.gatt.connect();
            
            estado.innerText = "Buscando servicio de impresión...";
            let service;
            const servicesUUIDs = ['0000ff00-0000-1000-8000-00805f9b34fb', '49535343-fe7d-4ae5-8fa9-9fafd205e455'];
            
            for (let uuid of servicesUUIDs) {
                try {
                    service = await server.getPrimaryService(uuid);
                    if (service) break;
                } catch(e) {}
            }

            if (!service) {
                const services = await server.getPrimaryServices();
                service = services[0];
            }

            const characteristics = await service.getCharacteristics();
            let characteristic = characteristics.find(c => c.properties.write || c.properties.writeWithoutResponse);

            if (!characteristic) {
                throw new Error("No se encontró una característica de escritura compatible en la impresora.");
            }

            estado.innerText = "Enviando comandos ESC/POS a la PT-210...";

            // Comandos ESC/POS para Goojprt PT-210
            let comandos = "\x1B\x40"; // Reset impresora
            comandos += "\x1B\x61\x01"; // Centrar texto
            comandos += "TEXTIL ANIT MARI\n";
            comandos += "Sucursal: Tienda Chela\n";
            comandos += "--------------------------------\n";
            comandos += "\x1B\x61\x00"; // Alinear a la izquierda
            comandos += "Prueba de impresion Bluetooth\n";
            comandos += "Goojprt PT-210 conectada OK!\n\n\n";

            const encoder = new TextEncoder();
            const data = encoder.encode(comandos);

            await characteristic.writeValue(data);

            estado.innerText = "✅ ¡Impresión de prueba enviada con éxito!";
        } catch (error) {
            estado.innerText = "❌ Error: " + error.message;
            console.error(error);
        }
    }
    </script>
    """
    components.html(bluetooth_html, height=130)

    if st.button("🖨️ Enviar Ticket de Prueba", use_container_width=True):
        st.info(f"Enviando señal de prueba a la impresora Bluetooth: **{nombre_dev}** ({ancho_papel})...")
