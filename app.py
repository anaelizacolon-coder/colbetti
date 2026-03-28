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

st.set_page_config(page_title="Mueblería Pro v15", layout="wide")

# --- MENÚ ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Nuevo Proyecto")
    with st.form("f_n", clear_on_submit=True):
        f_p = st.date_input("Fecha de Inicio:", date.today())
        col1, col2 = st.columns(2)
        cli = col1.text_input("Cliente").upper()
        sup = col2.text_input("Suplidor").upper()
        mue = st.text_area("Descripción del Mueble")
        p_v = st.number_input("Precio Venta ($)", min_value=0.0)
        c_f = st.number_input("Costo Fábrica ($)", min_value=0.0)
        if st.form_submit_button("Guardar Proyecto"):
            if cli and sup:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto guardado con fecha {f_p}")

# --- 2. VER PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado General de Proyectos")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay proyectos registrados.")

# --- 3. PAGOS Y ABONOS ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Cobro o Pago")
    df_act = pd.read_sql("SELECT id, cliente FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_act.iterrows()]
        sel = st.selectbox("Seleccione Proyecto:", opc)
        id_p = int(sel.split(" ")[1])
        t_m = st.radio("Tipo de Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        f_m = st.date_input("Fecha del Movimiento:", date.today())
        mon = st.number_input("Monto ($)", min_value=0.0)
        if st.button("Registrar en Historial"):
            campo = "adelanto_cliente" if "Cliente" in t_m else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, f_m.strftime("%Y-%m-%d"), t_m, mon))
            conn.commit()
            st.success("✅ Transacción registrada con éxito.")
    else:
        st.info("No hay proyectos activos para pagos.")

# --- 4. CORREGIR DATOS (AHORA CON FECHA EDITABLE) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro de Registros")
    df_e = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_e.empty:
        opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_e.iterrows()]
        sel = st.selectbox("Seleccione el proyecto a modificar:", opc)
        id_p = int(sel.split(" ")[1])
        p = df_e[df_e['id'] == id_p].iloc[0]
        
        # Convertir la fecha de texto a objeto date para el widget
        fecha_actual_proy = datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date()
        
        with st.form("e_m"):
            st.subheader(f"Editando Proyecto ID: {id_p}")
            n_fecha = st.date_input("Fecha de Creación:", value=fecha_actual_proy)
            
            col_1, col_2 = st.columns(2)
            n_c = col_1.text_input("Cliente", p['cliente'])
            n_s = col_2.text_input("Suplidor", p['suplidor'])
            
            n_mue = st.text_area("Descripción", p['mueble'])
            
            col_a, col_b = st.columns(2)
            n_pv = col_a.number_input("Precio Venta ($)", value=float(p['precio_venta']))
            n_cf = col_b.number_input("Costo Fábrica ($)", value=float(p['costo_fabrica']))
            
            col_c, col_d = st.columns(2)
            n_ac = col_c.number_input("Total Cobrado ($)", value=float(p['adelanto_cliente']))
            n_as = col_d.number_input("Total Pagado Fábrica ($)", value=float(p['adelanto_suplidor']))
            
            n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
            
            st.divider()
            btn_save, btn_del = st.columns(2)
            if btn_save.form_submit_button("💾 GUARDAR CAMBIOS"):
                c.execute('''UPDATE proyectos SET 
                             fecha_creacion=?, cliente=?, suplidor=?, mueble=?, 
                             precio_venta=?, costo_fabrica=?, adelanto_cliente=?, 
                             adelanto_suplidor=?, estado=? WHERE id=?''',
                          (n_fecha.strftime("%Y-%m-%d"), n_c.upper(), n_s.upper(), n_mue, 
                           n_pv, n_cf, n_ac, n_as, n_est, id_p))
                conn.commit()
                st.success("✅ Cambios guardados correctamente.")
                st.rerun()
                
            if btn_del.form_submit_button("🗑️ ELIMINAR REGISTRO"):
                c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                conn.commit()
                st.warning(f"⚠️ Proyecto {id_p} eliminado permanentemente.")
                st.rerun()
    else:
        st.info("No hay proyectos para editar.")

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("g_v"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto ($)", min_value=0.0)
        fec = st.date_input("Fecha del Gasto:", date.today())
        if st.form_submit_button("Guardar Gasto"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("✅ Gasto registrado.")

# --- 6. REPORTES ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    st.sidebar.subheader("Filtrar por Fecha")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    
    s_ini, s_fin = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    df_h = pd.read_sql(f"SELECT * FROM historial_pagos WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    tab1, tab2, tab3 = st.tabs(["📈 Estado de Resultados", "👥 Saldos Pendientes", "📦 Respaldo"])

    with tab1:
        ingresos = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        egresos_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gastos_v = df_g['monto'].sum() or 0.0
        beneficio = ingresos - egresos_f - gastos_v

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("INGRESOS (Cobros)", f"${ingresos:,.2f}")
        m2.metric("PAGOS FÁBRICA", f"${egresos_f:,.2f}")
        m3.metric("GASTOS VARIOS", f"${gastos_v:,.2f}")
        m4.metric("BENEFICIO NETO", f"${beneficio:,.2f}")

        if not df_h.empty or not df_g.empty:
            st.divider()
            c_a, c_b = st.columns(2)
            c_a.write("**Movimientos de Caja**")
            c_a.dataframe(df_h.style.format({"monto": "${:,.2f}"}), use_container_width=True)
            c_b.write("**Gastos Varios**")
            c_b.dataframe(df_g.style.format({"monto": "${:,.2f}"}), use_container_width=True)

    with tab2:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            
            st.subheader("Cuentas por Cobrar (Clientes)")
            cc = df_p.groupby('cliente')['Por Cobrar'].sum().reset_index().query('`Por Cobrar` > 0')
            st.table(cc.style.format({"Por Cobrar": "${:,.2f}"}))
            
            st.subheader("Cuentas por Pagar (Fábricas)")
            cp = df_p.groupby('suplidor')['Por Pagar'].sum().reset_index().query('`Por Pagar` > 0')
            st.table(cp.style.format({"Por Pagar": "${:,.2f}"}))

    with tab3:
        st.download_button("Descargar Base de Datos (CSV)", df_p.to_csv(index=False).encode('utf-8'), "respaldo_muebles.csv")
