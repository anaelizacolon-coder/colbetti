import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import io

def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# 1. MANTENIMIENTO ESTRUCTURA (Asegura que las columnas existan)
c.execute('CREATE TABLE IF NOT EXISTS proyectos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS historial_pagos (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, tipo_movimiento TEXT, monto REAL)')
c.execute('CREATE TABLE IF NOT EXISTS gastos_varios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v31", layout="wide")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú", menu)

# --- MÓDULO 1: NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    df_ex = pd.read_sql("SELECT * FROM proyectos LIMIT 1", conn)
    # Listas para autocompletado
    clientes_lista = sorted(pd.read_sql("SELECT DISTINCT cliente FROM proyectos", conn)['cliente'].tolist())
    suplidores_lista = sorted(pd.read_sql("SELECT DISTINCT suplidor FROM proyectos", conn)['suplidor'].tolist())
    
    with st.form("f_n"):
        f = st.date_input("Fecha", date.today())
        c1, c2 = st.columns(2)
        cl_s = c1.selectbox("Cliente", ["+ Nuevo"] + clientes_lista)
        cl_f = c1.text_input("Nombre Cliente").upper() if cl_s == "+ Nuevo" else cl_s
        su_s = c2.selectbox("Suplidor", ["+ Nuevo"] + suplidores_lista)
        su_f = c2.text_input("Nombre Suplidor").upper() if su_s == "+ Nuevo" else su_s
        mu = st.text_area("Descripción")
        p_v = st.number_input("Precio Venta ($)", min_value=0.0)
        c_f = st.number_input("Costo Fábrica ($)", min_value=0.0)
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                      (f.strftime("%Y-%m-%d"), cl_f, mu, su_f, p_v, c_f, 0.0, 0.0, "En Proceso"))
            conn.commit()
            st.rerun()

# --- MÓDULO 2: GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df.style.format({"precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"}), use_container_width=True)

# --- MÓDULO 3: PAGOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Movimiento")
    df_p = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_p.empty:
        with st.form("f_p"):
            sel = st.selectbox("Proyecto", [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:15]}" for _, r in df_p.iterrows()])
            id_p = int(sel.split(" ")[1])
            t = st.radio("Tipo", ["Cobro a Cliente", "Pago a Fábrica"])
            f = st.date_input("Fecha", date.today())
            m = st.number_input("Monto $", min_value=0.1)
            if st.form_submit_button("Registrar"):
                campo = "adelanto_cliente" if "Cliente" in t else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (m, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)", (id_p, f.strftime("%Y-%m-%d"), t, m))
                conn.commit()
                st.rerun()

# --- MÓDULO 4: CORREGIR ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor de Datos")
    t1, t2 = st.tabs(["Proyectos", "Pagos Individuales"])
    with t1:
        df_pro = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_pro.empty:
            sel_p = st.selectbox("Seleccionar:", [f"ID {r['id']} - {r['cliente']}" for _, r in df_pro.iterrows()])
            id_p = int(sel_p.split(" ")[1])
            p = df_pro[df_pro['id'] == id_p].iloc[0]
            with st.form("e_pro"):
                nc = st.text_input("Cliente", p['cliente'])
                ns = st.text_input("Suplidor", p['suplidor'])
                nm = st.text_area("Mueble", p['mueble'])
                nv = st.number_input("Venta", value=float(p['precio_venta']))
                ncost = st.number_input("Costo", value=float(p['costo_fabrica']))
                nest = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                if st.form_submit_button("Actualizar"):
                    c.execute("UPDATE proyectos SET cliente=?, suplidor=?, mueble=?, precio_venta=?, costo_fabrica=?, estado=? WHERE id=?", (nc.upper(), ns.upper(), nm, nv, ncost, nest, id_p))
                    conn.commit(); st.rerun()
    with t2:
        df_hi = pd.read_sql("SELECT h.*, p.cliente FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id ORDER BY h.id DESC", conn)
        if not df_hi.empty:
            sel_h = st.selectbox("Pago:", [f"ID {r['id']} | {r['cliente']} | ${r['monto']}" for _, r in df_hi.iterrows()])
            id_h = int(sel_h.split(" ")[1])
            h = df_hi[df_hi['id'] == id_h].iloc[0]
            if st.button("🚫 Eliminar/Anular este pago"):
                campo = "adelanto_cliente" if "Cliente" in h['tipo_movimiento'] else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? WHERE id = ?", (h['monto'], h['proyecto_id']))
                c.execute("DELETE FROM historial_pagos WHERE id=?", (id_h,))
                conn.commit(); st.rerun()

# --- MÓDULO 5: REPORTES (Protegido contra KeyError) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Reportes y Respaldo")
    
    # 1. Respaldo Excel
    if st.button("📥 Descargar Respaldo Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.read_sql("SELECT * FROM proyectos", conn).to_excel(writer, sheet_name='Proyectos', index=False)
            pd.read_sql("SELECT * FROM historial_pagos", conn).to_excel(writer, sheet_name='Pagos', index=False)
            pd.read_sql("SELECT * FROM gastos_varios", conn).to_excel(writer, sheet_name='Gastos', index=False)
        st.download_button("Click para descargar", output.getvalue(), f"Respaldo_{date.today()}.xlsx")

    # 2. Resultados
    st.divider()
    f1 = st.sidebar.date_input("Inicio", date(date.today().year, date.today().month, 1))
    f2 = st.sidebar.date_input("Fin", date.today())
    df_h = pd.read_sql(f"SELECT h.*, p.cliente FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{f1}' AND '{f2}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{f1}' AND '{f2}'", conn)
    
    c1, c2, c3 = st.columns(3)
    ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
    paf = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
    gas = df_g['monto'].sum() or 0.0
    c1.metric("INGRESOS", f"${ing:,.2f}"); c2.metric("PAGOS FAB", f"${paf:,.2f}"); c3.metric("UTILIDAD", f"${(ing-paf-gas):,.2f}")

    # 3. Cuentas Pendientes (Con verificación de columnas)
    st.divider()
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_p.empty:
        # Validación de columnas para evitar el error KeyError
        columnas_necesarias = ['precio_venta', 'costo_fabrica', 'adelanto_cliente', 'adelanto_suplidor']
        for col in columnas_necesarias:
            if col not in df_p.columns:
                df_p[col] = 0.0
        
        df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
        df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
        
        col_cli, col_sup = st.columns(2)
        col_cli.subheader("💰 Pendiente Clientes")
        col_cli.table(df_p[df_p['Por Cobrar'] > 0][['cliente', 'mueble', 'Por Cobrar']].style.format("${:,.2f}"))
        col_sup.subheader("🏭 Pendiente Suplidores")
        col_sup.table(df_p[df_p['Por Pagar'] > 0][['suplidor', 'mueble', 'Por Pagar']].style.format("${:,.2f}"))

elif choice == "Gastos Varios":
    with st.form("g"):
        con = st.text_input("Concepto"); mon = st.number_input("Monto"); f = st.date_input("Fecha")
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (f.strftime("%Y-%m-%d"), con, mon))
            conn.commit(); st.rerun()
