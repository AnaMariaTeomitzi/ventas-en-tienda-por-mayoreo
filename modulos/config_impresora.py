import streamlit as st
import streamlit.components.v1 as components

def mostrar():
    st.title("⚙️ Configuración de Impresora y Hardware")
    st.info("Configuración optimizada para tu impresora térmica modelo: **MTP-2**")

    if "config_impresora" not in st.session_state:
        st.session_state.config_impresora = {
            "nombre_dispositivo": "MTP-2",
            "ancho_papel": "58mm",
            "caracteres_por_linea": 32
        }

    cfg = st.session_state.config_impresora

    st.markdown("### 🖨️ Parámetros de la Impresora (MTP-2)")
    nombre_dev = st.text_input("Nombre de la Impresora:", value=cfg["nombre_dispositivo"])
    ancho_papel = st.selectbox("Ancho de Papel:", ["58mm (MTP-2 / Portátil)", "80mm (Mostrador)"], index=0)

    st.markdown("---")
    st.markdown("### 🧪 Conexión Directa por Bluetooth para MTP-2")
    st.write("Haz clic en el botón de abajo, busca y selecciona tu **MTP-2** en la lista que aparece en el navegador.")

    bluetooth_html = """
    <div style="text-align: center; padding: 5px;">
        <button onclick="conectarMTP2()" style="padding: 12px 20px; font-size: 15px; font-weight: bold; background: #2e7d32; color: white; border: none; border-radius: 6px; cursor: pointer;">
            🦷 Conectar e Imprimir en MTP-2
        </button>
        <p id="estado_mtp" style="margin-top: 10px; font-family: monospace; font-size: 13px; color: #333;"></p>
    </div>

    <script>
    async function conectarMTP2() {
        const estado = document.getElementById("estado_mtp");
        try {
            estado.innerText = "Abriendo Bluetooth... Selecciona 'MTP-2'.";
            
            // Filtro abierto para aceptar impresoras MTP y genéricas ESC/POS
            const device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [
                    '0000ff00-0000-1000-8000-00805f9b34fb', 
                    '00001101-0000-1000-8000-00805f9b34fb',
                    '49535343-fe7d-4ae5-8fa9-9fafd205e455',
                    'e7810a71-73ae-499d-8c15-faa9aef0c3f2'
                ]
            });

            estado.innerText = "Conectando a MTP-2...";
            const server = await device.gatt.connect();
            
            estado.innerText = "Buscando canales de comunicación...";
            const services = await server.getPrimaryServices();
            
            let writeCharacteristic = null;

            for (const service of services) {
                const characteristics = await service.getCharacteristics();
                for (const char of characteristics) {
                    if (char.properties.write || char.properties.writeWithoutResponse) {
                        writeCharacteristic = char;
                        break;
                    }
                }
                if (writeCharacteristic) break;
            }

            if (!writeCharacteristic) {
                throw new Error("No se encontró canal de escritura en la MTP-2.");
            }

            estado.innerText = "Enviando prueba ESC/POS a MTP-2...";

            // Comandos ESC/POS específicos para MTP-2
            let escpos = "\\x1B\\x40"; // Reset
            escpos += "\\x1B\\x61\\x01"; // Centrar
            escpos += "TEXTIL ANIT MARI\\n";
            escpos += "Sucursal: Activa\\n";
            escpos += "--------------------------------\\n";
            escpos += "\\x1B\\x61\\x00"; // Izquierda
            escpos += "Impresora MTP-2 conectada OK!\\n";
            escpos += "Prueba de impresion directa.\\n\\n\\n";

            const encoder = new TextEncoder();
            await writeCharacteristic.writeValue(encoder.encode(escpos));

            estado.innerText = "✅ ¡Impresión enviada a la MTP-2 con éxito!";
        } catch (error) {
            estado.innerText = "❌ Error: " + error.message;
            console.error(error);
        }
    }
    </script>
    """
    components.html(bluetooth_html, height=150)
