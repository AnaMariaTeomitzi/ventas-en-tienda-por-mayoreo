import streamlit as st
import sqlite3
from modulos.usuarios_db import conectar_usuarios, hash_password

def mostrar():
    st.title("👥 Gestión de Usuarios y Sucursales")
    st.write("Administra el personal, sus contraseñas, roles y la sucursal a la que pertenecen.")

    conn = conectar_usuarios()
    cursor = conn.cursor()

    tab1, tab2, tab3 = st.tabs(["📋 Listado de Usuarios", "➕ Dar de Alta", "⚙️ Modificar / Eliminar / Estado"])

    SUCURSALES = ["Tienda Chela", "Tienda Santa Ana", "Tienda Ixcotla"]

    # --- TAB 1: LISTADO ---
    with tab1:
        st.subheader("Personal Registrado")
        cursor.execute("SELECT id, username, rol, sucursal, activo FROM usuarios")
        usuarios = cursor.fetchall()
        
        datos = []
        for u in usuarios:
            datos.append({
                "ID": u[0],
                "Usuario": u[1],
                "Rol": u[2],
                "Sucursal": u[3],
                "Estado": "🟢 Activo" if u[4] == 1 else "🔴 Inactivo"
            })
        st.dataframe(datos, use_container_width=True)

    # --- TAB 2: DAR DE ALTA ---
    with tab2:
        st.subheader("Registrar Nuevo Usuario")
        with st.form("form_alta"):
            nuevo_user = st.text_input("Nombre de Usuario").strip()
            nuevo_pass = st.text_input("Contraseña", type="password")
            nuevo_rol = st.selectbox("Rol en el Sistema", ["Empleado", "Propietaria (Dueña)"])
            nueva_sucursal = st.selectbox("Sucursal Asignada", SUCURSALES)
            submit = st.form_submit_button("Guardar Usuario")

            if submit:
                if nuevo_user and nuevo_pass:
                    try:
                        pass_enc = hash_password(nuevo_pass)
                        cursor.execute("INSERT INTO usuarios (username, password, rol, sucursal, activo) VALUES (?, ?, ?, ?, 1)",
                                       (nuevo_user, pass_enc, nuevo_rol, nueva_sucursal))
                        conn.commit()
                        st.success(f"¡Usuario '{nuevo_user}' registrado con éxito en {nueva_sucursal}!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya existe. Elige uno diferente.")
                else:
                    st.warning("Completa todos los campos obligatorios.")

    # --- TAB 3: MODIFICAR, CAMBIAR ESTADO, CONTRASEÑA O SUCURSAL ---
    with tab3:
        st.subheader("Gestión Avanzada de Usuario")
        cursor.execute("SELECT id, username, rol, sucursal, activo FROM usuarios")
        lista_users = cursor.fetchall()

        if lista_users:
            dict_users = {u[1]: (u[0], u[2], u[3], u[4]) for u in lista_users}
            user_sel = st.selectbox("Selecciona un usuario para administrar", list(dict_users.keys()))
            
            uid, rol_actual, sucursal_actual, estado_actual = dict_users[user_sel]

            st.markdown("---")
            
            # 1. Modificar Rol y Sucursal
            col_rol, col_suc = st.columns(2)
            with col_rol:
                roles_disponibles = ["Empleado", "Propietaria (Dueña)"]
                idx_rol = roles_disponibles.index(rol_actual) if rol_actual in roles_disponibles else 0
                nuevo_rol_sel = st.selectbox("Modificar Rol", roles_disponibles, index=idx_rol, key=f"rol_{uid}")
                
                if nuevo_rol_sel != rol_actual:
                    if st.button("💾 Guardar Nuevo Rol"):
                        cursor.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (nuevo_rol_sel, uid))
                        conn.commit()
                        st.success(f"Rol de '{user_sel}' actualizado.")
                        st.rerun()

            with col_suc:
                idx_suc = SUCURSALES.index(sucursal_actual) if sucursal_actual in SUCURSALES else 0
                nueva_suc_sel = st.selectbox("Modificar Sucursal", SUCURSALES, index=idx_suc, key=f"suc_{uid}")
                
                if nueva_suc_sel != sucursal_actual:
                    if st.button("💾 Guardar Nueva Sucursal"):
                        cursor.execute("UPDATE usuarios SET sucursal = ? WHERE id = ?", (nueva_suc_sel, uid))
                        conn.commit()
                        st.success(f"Sucursal de '{user_sel}' actualizada a {nueva_suc_sel}.")
                        st.rerun()

            st.markdown("---")

            # 2. Estado (Activo / Inactivo) y Contraseña
            col_est, col_pass = st.columns(2)
            with col_est:
                st.write(f"**Estado actual:** {'🟢 Activo' if estado_actual == 1 else '🔴 Inactivo'}")
                if estado_actual == 1:
                    if st.button(f"🔴 Dar de baja", type="secondary"):
                        cursor.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (uid,))
                        conn.commit()
                        st.warning(f"Usuario '{user_sel}' desactivado.")
                        st.rerun()
                else:
                    if st.button(f"🟢 Reactivar"):
                        cursor.execute("UPDATE usuarios SET activo = 1 WHERE id = ?", (uid,))
                        conn.commit()
                        st.success(f"Usuario '{user_sel}' reactivado.")
                        st.rerun()

            with col_pass:
                nueva_pass = st.text_input(f"Nueva contraseña para {user_sel}", type="password", key=f"pass_{uid}")
                if st.button("Actualizar Contraseña"):
                    if nueva_pass:
                        pass_enc = hash_password(nueva_pass)
                        cursor.execute("UPDATE usuarios SET password = ? WHERE id = ?", (pass_enc, uid))
                        conn.commit()
                        st.success(f"Contraseña de '{user_sel}' actualizada.")
                    else:
                        st.warning("Escribe una contraseña válida.")

            st.markdown("---")

            # 3. Eliminar Definitivamente
            st.write("⚠️ **Zona de Peligro**")
            if user_sel == "admin":
                st.info("El usuario administrador principal ('admin') no se puede eliminar.")
            else:
                confirmar_borrado = st.checkbox(f"Confirmo que deseo eliminar permanentemente a {user_sel}", key=f"chk_del_{uid}")
                if confirmar_borrado:
                    if st.button(f"🗑️ Eliminar Definitivamente a {user_sel}", type="primary"):
                        cursor.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
                        conn.commit()
                        st.error(f"Usuario '{user_sel}' eliminado.")
                        st.rerun()
        else:
            st.info("No hay usuarios registrados.")

    conn.close()