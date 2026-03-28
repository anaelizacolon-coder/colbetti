import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN SEGURA
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# ASEGURAR ESTRUCTURA
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

st.set_page_config(page_title="Mueblería Pro v14", layout="wide")

# --- MENÚ ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    with st.form("f_n", clear_on_submit=True):
        f_p = st.date_input("Fecha:", date.today())
        col1, col2 = st.columns(2)
        cli = col1.text_input("Cliente").upper()
        sup = col2.text_input("Suplidor").upper()
        mue = st.text_area("Descripción")
        p_v = st.number_input("Precio Venta", min_value=0.0)
        c_f = st.number_input("Costo Fábrica", min_value=0.0)
        if st.form_submit_button("Guardar"):
            if cli and sup:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("Proyecto Guardado")

# --- 2. VER PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado General")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    st.dataframe(df, use_container_width=True)

# --- 3. PAGOS Y ABONOS (ESTO ALIMENTA EL REPORTE) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Cobro o Pago")
    df_act = pd.read_sql("SELECT id, cliente FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_act.iterrows()]
        sel = st.selectbox("Proyecto:", opc)
        id_p = int(sel.split(" ")[1])
        t_m = st.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        f_m = st.date_input("Fecha Movimiento:", date.today())
        mon = st.number_input("Monto", min_value=0.0)
        if st.button("Registrar Pago"):
            campo = "adelanto_cliente" if "Cliente" in t_m else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, f_m.strftime("%Y-%m-%d"), t_m, mon))
            conn.commit()
            st.success("Transacción registrada con éxito")
    else:
        st.info("No hay proyectos activos.")

# --- 4. CORREGIR ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    df_e = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_e.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_e.iterrows()]
        sel = st.selectbox("Seleccione:", opc)
        id_p = int(sel.split(" ")[1])
        p = df_e[df_e['id'] == id_p].iloc[0]
        with st.form("e_m"):
            n_c = st.text_input("Cliente", p['cliente'])
            n_s = st.text_input("Suplidor", p['suplidor'])
            n_pv = st.number_input("Venta", value=float(p['precio_venta']))
            n_cf = st.number_input("Costo", value=float(p['costo_fabrica']))
            n_ac = st.number_input("Cobrado", value=float(p['adelanto_cliente']))
            n_as = st.number_input("Pagado Fábrica", value=float(p['adelanto_suplidor']))
            col_a, col_b = st.columns(2)
            if col_a.form_submit_button("Guardar"):
                c.execute("UPDATE proyectos SET cliente=?, suplidor=?, precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=? WHERE id=?",
                          (n_c.upper(), n_s.upper(), n_pv, n_cf, n_ac, n_as, id_p))
                conn.commit()
                st.rerun()
            if col_b.form_submit_button("ELIMINAR"):
                c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                conn.commit()
                st.rerun()

# --- 5. GASTOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos")
    with st.form("g_v"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto", min_value=0.0)
        fec = st.date_input("Fecha", date.today())
        if st.form_submit_button("Guardar Gasto"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto anotado")

# --- 6. REPORTES (REVISIÓN DE FILTROS) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    
    # Rango de fechas dinámico
    st.sidebar.subheader("Periodo del Reporte")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    
    s_ini, s_fin = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    # CARGA DE DATOS SIN FILTROS PARA VALIDAR
    df_h = pd.read_sql(f"SELECT * FROM historial_pagos WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    t1, t2, t3 = st.tabs(["📈 Estado de Resultados", "👥 Saldos", "📦 Respaldo"])

    with t1:
        # Cálculos Manuales para asegurar que no haya nulos
        ingresos = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        egresos_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gastos_v = df_g['monto'].sum() or 0.0
        beneficio = ingresos - egresos_f - gastos_v

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("INGRESOS (Cobros)", f"${ingresos:,.2f}")
        m2.metric("PAGOS FÁBRICA", f"${egresos_f:,.2f}")
        m3.metric("GASTOS VARIOS", f"${gastos_v:,.2f}")
        m4.metric("BENEFICIO NETO", f"${beneficio:,.2f}")

        st.divider()
        if df_h.empty and df_g.empty:
            st.warning(f"No hay movimientos registrados entre {s_ini} y {s_fin}. Prueba ampliando el rango de fechas en la izquierda.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Desglose de Movimientos**")
                st.dataframe(df_h.style.format({"monto": "${:,.2f}"}), use_container_width=True)
            with col_b:
                st.write("**Desglose de Gastos**")
                st.dataframe(df_g.style.format({"monto": "${:,.2f}"}), use_container_width=True)

    with t2:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            
            st.subheader("Cuentas por Cobrar")
            cc = df_p.groupby('cliente')['Por Cobrar'].sum().reset_index().query('`Por Cobrar` > 0')
            st.table(cc.style.format({"Por Cobrar": "${:,.2f}"}))
            
            st.subheader("Cuentas por Pagar")
            cp = df_p.groupby('suplidor')['Por Pagar'].sum().reset_index().query('`Por Pagar` > 0')
            st.table(cp.style.format({"Por Pagar": "${:,.2f}"}))

    with t3:
        st.download_button("Descargar Excel (CSV)", df_p.to_csv(index=False).encode('utf-8'), "muebles.csv")
