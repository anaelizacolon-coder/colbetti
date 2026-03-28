import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# CONFIGURACIÓN DE TABLAS (SIEMPRE ACTIVAS)
c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_creacion TEXT, cliente TEXT, 
              mueble TEXT, suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS historial_pagos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, proyecto_id INTEGER, fecha TEXT, 
              tipo_movimiento TEXT, monto REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Mueblería Pro v19", layout="wide")

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ Panel de Control")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción:", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo", clear_on_submit=True):
        f_p = st.date_input("Fecha de Inicio:", date.today())
        col1, col2 = st.columns(2)
        cli = col1.text_input("Nombre del Cliente").upper()
        sup = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mue = st.text_area("Descripción del Mueble / Proyecto")
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio de Venta ($)", min_value=0.0, step=100.0)
        c_f = c2.number_input("Costo de Fábrica ($)", min_value=0.0, step=100.0)
        
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cli and sup and p_v > 0:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto de {cli} guardado con éxito.")
                st.rerun()

# --- 2. VER / GESTIONAR PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado General de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df.style.format({
            "precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", 
            "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"
        }), use_container_width=True)
    else:
        st.info("No hay proyectos registrados aún.")

# --- 3. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Cobros y Pagos")
    df_act = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    
    if not df_act.empty:
        with st.form("form_pagos", clear_on_submit=True):
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}... (Fábrica: {r['suplidor']})" for _, r in df_act.iterrows()]
            sel = st.selectbox("Seleccione el Proyecto Específico:", opc)
            id_p = int(sel.split(" ")[1])
            
            col_t, col_f = st.columns(2)
            tipo = col_t.radio("Tipo de Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
            fecha_m = col_f.date_input("Fecha de transacción:", date.today())
            monto = st.number_input("Monto ($)", min_value=0.0, step=10.0)
            
            if st.form_submit_button("✅ REGISTRAR MOVIMIENTO"):
                if monto > 0:
                    campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                    c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
                    c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                              (id_p, fecha_m.strftime("%Y-%m-%d"), tipo, monto))
                    conn.commit()
                    st.success("¡Dinero registrado y balance actualizado!")
                    st.rerun()
                else:
                    st.warning("El monto debe ser mayor a cero.")
    else:
        st.warning("No hay proyectos activos para procesar pagos.")

# --- 4. CORREGIR DATOS ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro y Eliminación")
    df_e = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_e.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_e.iterrows()]
        sel = st.selectbox("Seleccione registro para editar:", opc)
        id_p = int(sel.split(" ")[1])
        p = df_e[df_e['id'] == id_p].iloc[0]
        
        with st.form("edit_final"):
            n_f = st.date_input("Fecha:", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
            n_c = st.text_input("Cliente", p['cliente'])
            n_s = st.text_input("Suplidor", p['suplidor'])
            n_m = st.text_area("Mueble", p['mueble'])
            col_a, col_b = st.columns(2)
            n_pv = col_a.number_input("Venta", value=float(p['precio_venta']))
            n_cf = col_b.number_input("Costo", value=float(p['costo_fabrica']))
            n_ac = col_a.number_input("Total Cobrado", value=float(p['adelanto_cliente']))
            n_as = col_b.number_input("Total Pagado Fábrica", value=float(p['adelanto_suplidor']))
            n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
            
            btn_save, btn_del = st.columns(2)
            if btn_save.form_submit_button("💾 GUARDAR CAMBIOS"):
                c.execute('''UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, 
                             precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?''',
                          (n_f.strftime("%Y-%m-%d"), n_c.upper(), n_s.upper(), n_m, n_pv, n_cf, n_ac, n_as, n_est, id_p))
                conn.commit()
                st.success("Cambios aplicados.")
                st.rerun()
            if btn_del.form_submit_button("🗑️ ELIMINAR PROYECTO"):
                c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                conn.commit()
                st.rerun()

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Registro de Gastos Operativos")
    with st.form("g_v", clear_on_submit=True):
        col_con, col_mon = st.columns(2)
        con = col_con.text_input("Concepto del Gasto (Ej: Combustible, Comida)")
        mon = col_mon.number_input("Monto ($)", min_value=0.0)
        fec = st.date_input("Fecha:", date.today())
        if st.form_submit_button("Registrar Gasto"):
            if con and mon > 0:
                c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
                conn.commit()
                st.success("Gasto guardado.")
                st.rerun()

# --- 6. REPORTES Y RESPALDO ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    st.
