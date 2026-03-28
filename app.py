import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io

def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Tablas iniciales
c.execute('CREATE TABLE IF NOT EXISTS proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS historial_pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, tipo_movimiento TEXT, monto REAL)')
c.execute('CREATE TABLE IF NOT EXISTS gastos_varios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v29.1", layout="wide")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    df_ex = pd.read_sql("SELECT DISTINCT cliente, suplidor FROM proyectos", conn)
    op_cli = ["+ Nuevo Cliente"] + sorted(df_ex['cliente'].unique().tolist())
    op_sup = ["+ Nuevo Suplidor"] + sorted(df_ex['suplidor'].unique().tolist())
    with st.form("f_n"):
        f = st.date_input("Fecha", date.today())
        c1, c2 = st.columns(2)
        cl_s = c1.selectbox("Cliente", op_cli)
        cl_f = c1.text_input("Nombre Cliente").upper() if cl_s == "+ Nuevo Cliente" else cl_s
        su_s = c2.selectbox("Suplidor", op_sup)
        su_f = c2.text_input("Nombre Suplidor").upper() if su_s == "+ Nuevo Suplidor" else su_s
        mu = st.text_area("Descripción")
        p_v = st.number_input("Venta $", min_value=0.0)
        c_f = st.number_input("Costo $", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                      (f.strftime("%Y-%m-%d"), cl_f, mu, su_f, p_v, c_f, 0.0, 0.0, "En Proceso"))
            conn.commit()
            st.rerun()

# --- 2. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Cobros y Pagos")
    df_p = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_p.empty:
        with st.form("f_p"):
            sel = st.selectbox("Proyecto", [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:15]} | {r['suplidor']}" for _, r in df_p.iterrows()])
            id_p = int(sel.split(" ")[1])
            t = st.radio("Tipo", ["Cobro a Cliente", "Pago a Fábrica"])
            f = st.date_input("Fecha", date.today())
            m = st.number_input("Monto $", min_value=0.1)
            if st.form_submit_button("Registrar"):
                campo = "adelanto_cliente" if "Cliente" in t else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = IFNULL({campo},0) + ? WHERE id = ?", (m, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)", (id_p, f.strftime("%Y-%m-%d"), t, m))
                conn.commit()
                st.rerun()

# --- 3. CORREGIR DATOS ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    t1, t2 = st.tabs(["📋 Proyectos", "💸 Pagos Individuales"])
    with t1:
        df_pro = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_pro.empty:
            sel_p = st.selectbox("Editar Proyecto:", [f"ID {r['id']} - {r['cliente']}" for _, r in df_pro.iterrows()])
            id_p = int(sel_p.split(" ")[1])
            p = df_pro[df_pro['id'] == id_p].iloc[0]
            with st.form("e_pro"):
                nf = st.date_input("Fecha", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
                nc = st.text_input("Cliente", p['cliente'])
                ns = st.text_input("Suplidor", p['suplidor'])
                nm = st.text_area("Mueble", p['mueble'])
                nv = st.number_input("Venta", value=float(p['precio_venta'] or 0))
                ncost = st.number_input("Costo", value=float(p['costo_fabrica'] or 0))
                nest = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                if st.form_submit_button("💾 ACTUALIZAR"):
                    c.execute("UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, precio_venta=?, costo_fabrica=?, estado=? WHERE id=?", (nf.strftime("%Y-%m-%d"), nc.upper(), ns.upper(), nm, nv, ncost, nest, id_p))
                    conn.commit()
                    st.rerun()
    with t2:
        df_hi = pd.read_sql("SELECT h.id, h.proyecto_id, h.fecha, p.cliente, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id ORDER BY h.id DESC", conn)
        if not df_hi.empty:
            sel_h = st.selectbox("Seleccionar Pago:", [f"ID {r['id']} | {r['cliente']} | ${r['monto']}" for _, r in df_hi.iterrows()])
            id_h = int(sel_h.split(" ")[1])
            h = df_hi[df_hi['id'] == id_h].iloc[0]
            if st.button("🗑️ ELIMINAR ESTE PAGO"):
                campo = "adelanto_cliente" if "Cliente" in h['tipo_movimiento'] else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? WHERE id = ?", (h['monto'], h['proyecto_id']))
                c.execute("DELETE FROM historial_pagos WHERE id=?", (id_h,))
                conn.commit()
                st.rerun()

# --- 4. REPORTES Y RESPALDO ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia de Negocio")
    
    # Botón de Respaldo (Simple)
    if st.button("📥 Generar Respaldo Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.read_sql("SELECT * FROM proyectos", conn).to_excel(writer, sheet_name='Proyectos', index=False)
            pd.read_sql("SELECT * FROM historial_pagos", conn).to_excel(writer, sheet_name='Pagos', index=False)
        st.download_button("Descargar Archivo", output.getvalue(), f"Respaldo_{date.today()}.xlsx")

    st.divider()
    f1, f2 = st.sidebar.date_input("R
