import streamlit as st
from .base_datos import obtener_clientes_recurrentes_lista, guardar_cliente_recurrente, eliminar_cliente_recurrente

def mostrar(acceso_propietaria):
    if not acceso_propietaria:
        st.error("⛔ Acceso denegado. Esta sección requiere la contraseña de Propietaria.")
    else:
        st.title("⭐ Gestión de Clientes Recurrentes Preferentes")
        st.info("Los clientes registrados aquí obtienen automáticamente **Precio Mayoreo Nivel 1** desde la primera pieza al registrar sus ventas.")

        col_reg1, col_reg2 = st.columns(2)

        with col_reg1:
            st.markdown("### ➕ Dar de Alta Nuevo Cliente Recurrente")
            nuevo_nombre_cte = st.text_input("Nombre o Negocio del Cliente:")
            if st.button("💾 Guardar en Lista Preferente", use_container_width=True):
                if guardar_cliente_recurrente(nuevo_nombre_cte):
                    st.success(f"¡Cliente '{nuevo_nombre_cte.strip()}' agregado exitosamente a la lista preferente!")
                    st.rerun()
                else:
                    st.warning("El nombre está vacío o ya se encuentra registrado.")

        with col_reg2:
            st.markdown("### 📋 Listado Actual y Eliminación")
            recurrentes_actuales = obtener_clientes_recurrentes_lista()
            if recurrentes_actuales:
                cte_a_borrar = st.selectbox("Selecciona cliente a eliminar de recurrentes:", recurrentes_actuales)
                if st.button("🗑️ Eliminar de la Lista Preferente", use_container_width=True):
                    if eliminar_cliente_recurrente(cte_a_borrar):
                        st.success(f"Cliente '{cte_a_borrar}' eliminado de la lista preferente.")
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar el cliente.")
                
                st.markdown("**Clientes Preferentes Actuales:**")
                for c in recurrentes_actuales:
                    st.write(f"- ⭐ {c}")
            else:
                st.info("No hay clientes recurrentes guardados actualmente.")