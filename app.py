import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# CONFIGURACIÓN DE TABLAS
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

st.set_page_config(page_title="Mueblería Pro v21", layout="wide")

# --- MENÚ LATERAL ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción:", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    df_p_existentes = pd.read_sql("SELECT DISTINCT cliente, suplidor FROM proyectos", conn)
    lista_clientes = sorted(df_p_existentes['cliente'].unique().tolist())
    lista_suplidores = sorted(df_p_existentes['suplidor'].unique().tolist())
    opciones_cli = ["+ Agregar Nuevo Cliente"] + lista_clientes
    opciones_sup = ["+ Agregar Nuevo Suplidor"] + lista_suplidores

    with st.form("form_nuevo", clear_on_submit=True):
        f_p = st.date_input("Fecha de Inicio:", date.today())
        col1, col2 = st.columns(2)
        cli_sel = col1.selectbox("Seleccionar Cliente:", opciones_cli)
        cli_final = col1.text_input("Nombre Nuevo Cliente (si aplica)").upper() if cli_sel == "+ Agregar Nuevo Cliente" else cli_sel
        sup_sel = col2.selectbox("Seleccionar Suplidor:", opciones_sup)
        sup_final = col2.text_input("Nombre Nuevo Suplidor (si aplica)").upper() if sup_sel == "+ Agregar Nuevo Suplidor" else sup_sel
        mue = st.text_area("Descripción del Mueble")
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio Venta ($)", min_value=0.0)
        c_f = c2.number_input("Costo Fábrica ($)", min_value=0.0)
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cli_final and sup_final:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli_final, mue, sup_final, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado.")
                st.rerun()

# --- 2. VER PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    st.dataframe(df, use_container_width=True)

# --- 3. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Pago")
    df_act = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        with st.form("f_pagos", clear_on_submit=True):
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}" for _, r in df_act.iterrows()]
            sel = st.selectbox("Proyecto:", opc)
            id_p = int(sel.split(" ")[1])
            tipo = st.radio("Tipo:", ["Cobro a Cliente", "Pago a Fábrica"])
            mon = st.number_input("Monto ($)", min_value=0.1)
            if st.form_submit_button("Registrar"):
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                          (id_p, date.today().strftime("%Y-%m-%d"), tipo, mon))
                conn.commit()
                st.success("Registrado.")
                st.rerun()

# --- 4. CORREGIR DATOS (RESTAURADO ELIMINAR) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    df_e = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_e.empty:
        opc = [f"ID {r['id']} - {r['cliente']} ({r['mueble'][:15]})" for _, r in df_e.iterrows()]
        sel = st.selectbox("Seleccione registro:", opc)
        id_p = int(sel.split(" ")[1])
        p = df_e[df_e['id'] == id_p].iloc[0]

        with st.form("edit_form"):
            st.subheader(f"Modificando ID: {id_p}")
            n_f = st.date_input("Fecha:", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
            col1, col2 = st.columns(2)
            n_c = col1.text_input("Cliente", p['cliente'])
            n_s = col2.text_input("Suplidor", p['suplidor'])
            n_m = st.text_area("Mueble", p['mueble'])
            n_pv = col1.number_input("Precio Venta", value=float(p['precio_venta']))
            n_cf = col2.number_input("Costo Fábrica", value=float(p['costo_fabrica']))
            n_ac = col1.number_input("Total Cobrado", value=float(p['adelanto_cliente']))
            n_as = col2.number_input("Total Pagado Fábrica", value=float(p['adelanto_suplidor']))
            n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
            
            st.write("---")
            col_save, col_del = st.columns(2)
            
            # Botón Guardar
            if col_save.form_submit_button("💾 GUARDAR CAMBIOS"):
                c.execute('''UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, 
                             precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?''',
                          (n_f.strftime("%Y-%m-%d"), n_c.upper(), n_s.upper(), n_m, n_pv, n_cf, n_ac, n_as, n_est, id_p))
                conn.commit()
                st.success("✅ Cambios guardados.")
                st.rerun()

            # Botón Eliminar (Dentro del formulario para que sea procesado)
            eliminar_check = st.checkbox("Confirmar que deseo ELIMINAR permanentemente este proyecto")
            if col_del.form_submit_button("🗑️ ELIMINAR AHORA"):
                if eliminar_check:
                    c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                    c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                    conn.commit()
                    st.warning(f"⚠️ Proyecto {id_p} eliminado.")
                    st.rerun()
                else:
                    st.error("Debes marcar la casilla de confirmación para eliminar.")

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos")
    with st.form("g_v"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto", min_value=0.0)
        fec = st.date_input("Fecha", date.today())
        if st.form_submit_button("Guardar"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto anotado.")

# --- 6. REPORTES ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    st.sidebar.subheader("Filtros")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    df_h = pd.read_sql(f"SELECT h.fecha, p.cliente, p.mueble, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{f_ini}' AND '{f_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{f_ini}' AND '{f_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)
    
    t1, t2 = st.tabs(["Resultados", "Saldos"])
    with t1:
        ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        p_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gas = df_g['monto'].sum() or 0.0
        st.metric("Utilidad Neta", f"${(ing - p_f - gas):,.2f}")
        st.dataframe(df_h)
    with t2:
        if not df_p.empty:
            df_p['Deuda'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            st.table(df_p[df_p['Deuda'] > 0][['cliente', 'mueble', 'Deuda']])
