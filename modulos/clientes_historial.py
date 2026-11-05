import streamlit as st
import pandas as pd
from .base_datos import conectar_db

def mostrar(acceso_propietaria):
    st.title("👥 Historial de Compras por Cliente")
    
    # Obtenemos los clientes desde Turso
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
        st.info("No hay clientes registrados en las ventas todavía.")
        return

    cliente_sel = st.selectbox("Selecciona un cliente para ver su historial:", clientes)

    if cliente_sel:
        try:
            if tipo == "turso":
                # Consultamos las ventas del cliente seleccionado
                rs = conn.execute("SELECT * FROM registro_ventas WHERE Cliente = ?;", (cliente_sel,))
                columnas = [desc[0] for desc in rs.description] if hasattr(rs, 'description') else [
                    "id", "Fecha", "Sucursal", "Cliente", "SKU", "Producto", "Nivel_Precio", 
                    "Precio_Unitario", "Cantidad", "Total_Venta", "Costo_Unitario", "Costo_Total", 
                    "Ganancia", "Metodo_Pago", "Referencia", "Usuario", "Ticket_ID", "Notas"
                ] # Ajusta según tus columnas exactas
                # O más fácil usando pandas si prefieres:
            
            # Usando Pandas para hacerlo más directo y limpio con la base de datos:
            if tipo == "turso":
                # Convertimos el resultado de Turso a DataFrame de manera segura
                rs_full = conn.execute("SELECT * FROM registro_ventas WHERE Cliente = ?;", (cliente_sel,))
                # Si tu función base_datos ya tiene una forma de traer un df, puedes usarla, o mapear las columnas:
                filas = [row for row in rs_full.rows]
                # Nota: Si usas una función general para obtener el historial, puedes reutilizarla aquí.
            
            # Supongamos que ya tienes el DataFrame del cliente filtrado:
            query_df = f"SELECT * FROM registro_ventas WHERE Cliente = '{cliente_sel}';"
            if tipo == "turso":
                # Si 'conectar_db' devuelve la conexión de Turso, leemos con pandas pasando la query si soporta sqlite3 o iterando:
                df_cliente = pd.read_sql(query_df, conn) if hasattr(conn, 'cursor') else pd.DataFrame() # Dependiendo de tu conector
            
            # --- CÁLCULOS ---
            if not df_cliente.empty:
                total_compras = pd.to_numeric(df_cliente["Total_Venta"], errors='coerce').sum()
                ganancia_total = pd.to_numeric(df_cliente["Ganancia"], errors='coerce').sum()
                
                # 🎁 CALCULO DEL FONDO NAVIDEÑO (Ejemplo: 10% de la Ganancia Generada)
                porcentaje_navideno = 0.10 # 10% de la ganancia
                fondo_navideno = ganancia_total * porcentaje_navideno

                st.markdown(f"### Resumen para: **{cliente_sel}**")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("💵 Total Compras", f"${total_compras:,.2f} MXN")
                col2.metric("⭐ Ganancia Generada", f"${ganancia_total:,.2f} MXN")
                col3.metric("🎄 Fondo Navideño (10%)", f"${fondo_navideno:,.2f} MXN", help="Porcentaje reservado de la ganancia para regalo o reembolso de fin de año.")

                st.markdown("---")
                st.dataframe(df_cliente, use_container_width=True)
            else:
                st.info("Este cliente no tiene compras registradas.")

        except Exception as e:
            st.error(f"Error al generar el historial del cliente: {e}")
