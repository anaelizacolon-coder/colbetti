import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# Conexión a la base de datos
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Creación de tablas base
c.execute('CREATE TABLE IF NOT EXISTS proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS historial_pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, tipo_movimiento TEXT, monto REAL)')
c.execute('CREATE TABLE IF NOT EXISTS gastos_varios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)')
conn.commit()

st.set_page_config(page_title="Colbeth v29.0", layout="wide")

# Menú lateral
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo"):
        fecha = st.date_input("Fecha", date.today())
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nombre del Cliente").upper()
        suplidor = col2.text_input("Nombre del Suplidor").upper()
        mueble = st.text_area("Descripción del Trabajo/Mueble")
        
        c_v, c_f = st.columns(2)
        p_venta = c_v.number_input("Precio de Venta ($)", min_value=0.0)
        c_fabrica = c_f.number_input("Costo de Fábrica ($)", min_value=0.0)
        
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cliente and mueble:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (fecha.strftime("%Y-%m-%d"), cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto de {cliente} guardado.")
                st.rerun()
            else:
                st.error("Por favor llena el nombre del cliente y la descripción.")

# --- 2. GESTIONAR PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado General de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay proyectos registrados.")

# --- 3. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Cobros y Pagos")
    df_proy = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    
    if not df_proy.empty:
        with st.form("form_pagos"):
            # Crear lista de selección con ID y Cliente
            opciones = [f"ID {row['id']} | {row['cliente']} | {row['mueble'][:20]}" for _, row in df_proy.iterrows()]
            seleccion = st.selectbox("Selecciona el Proyecto", opciones)
            id_proyecto = int(seleccion.split(" ")[1])
            
            tipo = st.radio("Tipo de Movimiento", ["Cobro a Cliente", "Pago a Fábrica"])
            monto = st.number_input("Monto ($)", min_value=0.0)
            fecha_pago = st.date_input("Fecha", date.today())
            
            if st.form_submit_button("Registrar Movimiento"):
                # Actualizar totales en tabla proyectos
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_proyecto))
                
                # Registrar en historial
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                          (id_proyecto, fecha_pago.strftime("%Y-%m-%d"), tipo, monto))
                conn.commit()
                st.success("✅ Pago registrado correctamente.")
                st.rerun()

# --- 4. CORREGIR DATOS ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Modificar o Eliminar Registros")
    df_edit = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_edit.empty:
        sel_edit = st.selectbox("Selecciona Proyecto para editar", [f"ID {r['id']} - {r['cliente']}" for _, r in df_edit.iterrows()])
        id_edit = int(sel_edit.split(" ")[1])
        # Aquí puedes agregar lógica para borrar o editar campos específicos
        if st.button("🗑️ Eliminar Proyecto (CUIDADO)"):
            c.execute("DELETE FROM proyectos WHERE id = ?", (id_edit,))
            c.execute("DELETE FROM historial_pagos WHERE proyecto_id = ?", (id_edit,))
            conn.commit()
            st.warning("Proyecto eliminado.")
            st.rerun()

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("form_gastos"):
        f_gasto = st.date_input("Fecha", date.today())
        concepto = st.text_input("Concepto (Gasolina, Dieta, Tornillos, etc.)")
        monto_g = st.number_input("Monto ($)", min_value=0.0)
        if st.form_submit_button("Guardar Gasto"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)",
                      (f_gasto.strftime("%Y-%m-%d"), concepto, monto_g))
            conn.commit()
            st.success("Gasto registrado.")

# --- 6. REPORTES ---
elif choice == "Reportes":
    st.header("📊 Resumen de Utilidades")
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_p.empty:
        total_ventas = df_p['precio_venta'].sum()
        total_costos = df_p['costo_fabrica'].sum()
        utilidad_bruta = total_ventas - total_costos
        
        st.metric("Ventas Totales", f"${total_ventas:,.2f}")
        st.metric("Costos de Fábrica", f"${total_costos:,.2f}")
        st.metric("Utilidad Proyectada", f"${utilidad_bruta:,.2f}", delta_color="normal")
