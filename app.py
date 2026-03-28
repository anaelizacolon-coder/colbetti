import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io

def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Inicialización de Tablas
c.execute('CREATE TABLE IF NOT EXISTS proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS historial_pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, tipo_movimiento TEXT, monto REAL)')
c.execute('CREATE TABLE IF NOT EXISTS gastos_varios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v34", layout="wide")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    clientes_lista = sorted(pd.read_sql("SELECT DISTINCT cliente FROM proyectos", conn)['cliente'].tolist())
    suplidores_lista = sorted(pd.read_sql("SELECT DISTINCT suplidor FROM proyectos", conn)['suplidor'].tolist())
    with st.form("f_nuevo", clear_on_submit=True):
        f = st.date_input("Fecha", date.today())
        col1, col2 = st.columns(2)
        cl_sel = col1.selectbox("Cliente", ["+ Nuevo"] + clientes_lista)
        cl_final = col1.text_input("Nombre Cliente").upper() if cl_sel == "+ Nuevo" else cl_sel
        su_sel = col2.selectbox("Suplidor", ["+ Nuevo"] + suplidores_lista)
        su_final = col2.text_input("Nombre Suplidor").upper() if su_sel == "+ Nuevo" else su_sel
        mu = st.text_area("Descripción del Mueble/Trabajo")
        c_v, c_c = st.columns(2)
        p_v = c_v.number_input("Precio Venta ($)", min_value=0.0)
        c_f = c_c.number_input("Costo Fábrica ($)", min_value=0.0)
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cl_final and mu:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f.strftime("%Y-%m-%d"), cl_final, mu, su_final, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado con éxito")
                st.rerun()

# --- 2. GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn).fillna(0)
    if not df.empty:
        st.dataframe(df.style.format({"precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"}), use_container_width=True)
    else:
        st.info("No hay proyectos registrados aún.")

# --- 3. PAGOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Cobro o Pago")
    df_p = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_p.empty:
        with st.form("f_pagos", clear_on_submit=True):
            sel = st.selectbox("Seleccionar Proyecto", [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}" for _, r in df_p.iterrows()])
            id_p = int(sel.split(" ")[1])
            tipo = st.radio("Tipo de Movimiento", ["Cobro a Cliente", "Pago a Fábrica"])
            f_p = st.date_input("Fecha", date.today())
            monto = st.number_input("Monto ($)", min_value=0.1)
            if st.form_submit_button("✅ Registrar"):
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = IFNULL({campo}, 0) + ? WHERE id = ?", (monto, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)", (id_p, f_p.strftime("%Y-%m-%d"), tipo, monto))
                conn.commit()
                st.success("Movimiento registrado")
                st.rerun()

# --- 4. CORREGIR ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor de Registros")
    tab1, tab2 = st.tabs(["Proyectos", "Pagos Individuales"])
    with tab1:
        df_pro = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_pro.empty:
            sel_p = st.selectbox("Proyecto a editar:", [f"ID {r['id']} - {r['cliente']}" for _, r in df_pro.iterrows()])
            id_p = int(sel_p.split(" ")[1])
            p = df_pro[df_pro['id'] == id_p].iloc[0]
            with st.form("edit_pro"):
                nc = st.text_input("Cliente", p['cliente'])
                ns = st.text_input("Suplidor", p['suplidor'])
                nm = st.text_area("Mueble", p['mueble'])
                nv = st.number_input("Venta", value=float(p['precio_venta'] or 0))
                ncf = st.number_input("Costo", value=float(p['costo_fabrica'] or 0))
                nest = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                if st.form_submit
