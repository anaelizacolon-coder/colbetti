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

st.set_page_config(page_title="Mueblería Pro v27", layout="wide")

# --- MENÚ LATERAL ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Navegación Principal:", menu)

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
        
        cli_sel = col1.selectbox("Cliente:", opciones_cli)
        cli_final = col1.text_input("Nombre Nuevo Cliente").upper() if cli_sel == "+ Agregar Nuevo Cliente" else cli_sel
        
        sup_sel = col2.selectbox("Suplidor (Fábrica/Marmolería):", opciones_sup)
        sup_final = col2.text_input("Nombre Nuevo Suplidor").upper() if sup_sel == "+ Agregar Nuevo Suplidor" else sup_sel
        
        mue = st.text_area("Descripción del Producto (Ej: Cocina Madera, Tope Granito, etc.)")
        
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio Venta ($)", min_value=0.0)
        c_f = c2.number_input("Costo Fábrica ($)", min_value=0.0)
        
        if st.form_submit_button("💾 Guardar Proyecto"):
            if cli_final and sup_final and p_v > 0:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli_final, mue, sup_final, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Proyecto registrado para {cli_final}")
                st.rerun()

# --- 2. VER PROYECTOS ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Listado General")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        st.dataframe(df.style.format({"precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"}), use_container_width=True)
    else:
        st.info("No hay proyectos.")

# --- 3. PAGOS Y ABONOS (Con identificación clara de suplidor) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Pago o Cobro")
    df_act = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        with st.form("f_pagos", clear_on_submit=True):
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:15]} | Fab: {r['suplidor']}" for _, r in df_act.iterrows()]
            sel = st.selectbox("Proyecto Destino:", opc)
            id_p = int(sel.split(" ")[1])
            
            col_a, col_b = st.columns(2)
            tipo = col_a.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
            f_pago = col_b.date_input("Fecha:", date.today())
            mon = st.number_input("Monto ($)", min_value=0.1)
            
            if st.form_submit_button("✅ Guardar"):
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                          (id_p, f_pago.strftime("%Y-%m-%d"), tipo, mon))
                conn.commit()
                st.success("Registrado correctamente.")
                st.rerun()

# --- 4. CORREGIR DATOS (Módulo Completo de Edición y Anulación) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    tab1, tab2 = st.tabs(["📋 Editar Proyectos", "💸 Editar/Anular Pagos"])
    
    with tab1:
        df_e = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_e.empty:
            opc = [f"ID {r['id']} - {r['cliente']} ({r['mueble'][:15]})" for _, r in df_e.iterrows()]
            sel = st.selectbox("Proyecto a editar:", opc)
            id_p = int(sel.split(" ")[1])
            p = df_e[df_e['id'] == id_p].iloc[0]
            with st.form("edit_proy"):
                nf = st.date_input("Fecha Creación:", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
                nc = st.text_input("Cliente", p['cliente'])
                ns = st.text_input("Suplidor", p['suplidor'])
                nm = st.text_area("Mueble", p['mueble'])
                col_v, col_c = st.columns(2)
                npv = col_v.number_input("Venta", value=float(p['precio_venta']))
                ncf = col_c.number_input("Costo", value=float(p['costo_fabrica']))
                nest = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                
                cs, cd = st.columns(2)
                if cs.form_submit_button("💾 ACTUALIZAR"):
                    c.execute("UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, precio_venta=?, costo_fabrica=?, estado=? WHERE id=?",
                              (nf.strftime("%Y-%m-%d"), nc.upper(), ns.upper(), nm, npv, ncf, nest, id_p))
                    conn.commit()
                    st.rerun()
                
                if cd.form_submit_button("🗑️ ELIMINAR TODO"):
                    if st.checkbox("Confirmar borrado total"):
                        c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                        c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                        conn.commit()
                        st.rerun()

    with tab2:
        df_h_edit = pd.read_sql("SELECT h.id as p_id, h.proyecto_id, h.fecha, p.cliente, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id ORDER BY h.id DESC", conn)
        if not df_h_edit.empty:
            opc_h = [f"ID {r['p_id']} | {r['cliente']} | {r['tipo_movimiento']} | ${r['monto']}" for _, r in df_h_edit.iterrows()]
            sel_h = st.selectbox("Seleccione pago:", opc_h)
            id_h = int(sel_h.split(" ")[1])
            p_h = df_h_edit[df_h_edit['p_id'] == id_h].iloc[0]
            with st.form("edit_pago_ind"):
                fn = st.date_input("Fecha Pago:", datetime.strptime(p_h['fecha'], "%Y-%m-%d").date())
                mn = st.number_input("Monto Pago:", value=float(p_h['monto']))
                c_s, c_a = st.columns(2)
                if c_s.form_submit_button("💾 GUARDAR"):
                    campo = "adelanto_cliente" if "Cliente" in p_h['tipo_movimiento'] else "adelanto_suplidor"
                    c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? + ? WHERE id = ?", (p_h['monto'], mn, p_h['proyecto_id']))
                    c.execute("UPDATE historial_pagos SET fecha=?, monto=? WHERE id=?", (fn.strftime("%Y-%m-%d"), mn, id_h))
                    conn.commit()
                    st.rerun()
                if c_a.form_submit_button("🚫 ANULAR"):
                    if st.checkbox("Confirmar anulación de este pago"):
                        campo = "adelanto_cliente" if "Cliente" in p_h['tipo_movimiento'] else "adelanto_suplidor"
                        c.execute(f"UPDATE proyectos SET {campo} = {campo} - ? WHERE id = ?", (p_h['monto'], p_h['proyecto_id']))
                        c.execute("DELETE FROM historial_pagos WHERE id=?", (id_h,))
                        conn.commit()
                        st.rerun()

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("g_v"):
        con = st.text_input("Concepto")
        mon = st.number_input("Monto ($)")
        fec = st.date_input("Fecha", date.today())
        if st.form_submit_button("Guardar Gasto"):
            c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
            conn.commit()
            st.success("Gasto anotado.")

# --- 6. REPORTES (ESTADO DE RESULTADOS) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Reportes Financieros")
    f_ini = st.sidebar.date_input("Inicio Periodo", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Fin Periodo", date.today())
    
    df_h = pd.read_sql(f"SELECT h.fecha, p.cliente, p.suplidor, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{f_ini}' AND '{f_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{f_ini}' AND '{f_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    t1, t2 = st.tabs(["📉 Resultados", "👥 Deudas y Pendientes"])
    
    with t1:
        ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        paf = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gas = df_g['monto'].sum() or 0.0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("COBROS", f"${ing:,.2f}")
        m2.metric("PAGOS FÁB.", f"${paf:,.2f}")
        m3.metric("GASTOS", f"${gas:,.2f}")
        m4.metric("UTILIDAD", f"${(ing-paf-gas):,.2f}")
        st.dataframe(df_h, use_container_width=True)
        
    with t2:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            
            c_c, c_s = st.columns(2)
            c_c.subheader("Saldos Clientes")
            c_c.table(df_p[df_p['Por Cobrar'] > 0][['cliente', 'mueble', 'Por Cobrar']].style.format("${:,.2f}"))
            
            c_s.subheader("Pendientes Suplidores")
            c_s.table(df_p[df_p['Por Pagar'] > 0][['suplidor', 'mueble', 'Por Pagar']].style.format("${:,.2f}"))
