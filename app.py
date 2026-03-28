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

st.set_page_config(page_title="Mueblería Pro v23", layout="wide")

# --- MENÚ LATERAL ---
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción:", menu)

# --- 1. NUEVO PROYECTO (Mantiene selectores inteligentes) ---
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
        cli_final = col1.text_input("Nombre Nuevo Cliente").upper() if cli_sel == "+ Agregar Nuevo Cliente" else cli_sel
        sup_sel = col2.selectbox("Seleccionar Suplidor:", opciones_sup)
        sup_final = col2.text_input("Nombre Nuevo Suplidor").upper() if sup_sel == "+ Agregar Nuevo Suplidor" else sup_sel
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
    if not df.empty:
        st.dataframe(df.style.format({
            "precio_venta": "${:,.2f}", "costo_fabrica": "${:,.2f}", 
            "adelanto_cliente": "${:,.2f}", "adelanto_suplidor": "${:,.2f}"
        }), use_container_width=True)
    else:
        st.info("No hay proyectos registrados.")

# --- 3. PAGOS Y ABONOS (Mantiene fecha manual) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registrar Pago o Cobro")
    df_act = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df_act.empty:
        with st.form("f_pagos", clear_on_submit=True):
            opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}" for _, r in df_act.iterrows()]
            sel = st.selectbox("Proyecto:", opc)
            id_p = int(sel.split(" ")[1])
            col_a, col_b = st.columns(2)
            tipo = col_a.radio("Tipo:", ["Cobro a Cliente", "Pago a Fábrica"])
            f_pago = col_b.date_input("Fecha del Pago:", date.today())
            mon = st.number_input("Monto ($)", min_value=0.1)
            if st.form_submit_button("Registrar Movimiento"):
                campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
                c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (mon, id_p))
                c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                          (id_p, f_pago.strftime("%Y-%m-%d"), tipo, mon))
                conn.commit()
                st.success(f"✅ Registrado exitosamente.")
                st.rerun()

# --- 4. CORREGIR DATOS (Mantiene edición de fechas de pagos y proyectos) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Editor Maestro")
    tab_proy, tab_hist = st.tabs(["Editar Proyecto", "Editar/Corregir Fechas de Pagos"])
    
    with tab_proy:
        df_e = pd.read_sql("SELECT * FROM proyectos", conn)
        if not df_e.empty:
            opc = [f"ID {r['id']} - {r['cliente']}" for _, r in df_e.iterrows()]
            sel = st.selectbox("Seleccione proyecto:", opc)
            id_p = int(sel.split(" ")[1])
            p = df_e[df_e['id'] == id_p].iloc[0]
            with st.form("edit_proy"):
                n_f = st.date_input("Fecha Creación:", datetime.strptime(p['fecha_creacion'], "%Y-%m-%d").date())
                n_c = st.text_input("Cliente", p['cliente'])
                n_s = st.text_input("Suplidor", p['suplidor'])
                n_m = st.text_area("Mueble", p['mueble'])
                n_pv = st.number_input("Venta", value=float(p['precio_venta']))
                n_cf = st.number_input("Costo", value=float(p['costo_fabrica']))
                n_ac = st.number_input("Total Cobrado", value=float(p['adelanto_cliente']))
                n_as = st.number_input("Total Pagado Fábrica", value=float(p['adelanto_suplidor']))
                n_est = st.selectbox("Estado", ["En Proceso", "Entregado"], index=0 if p['estado']=="En Proceso" else 1)
                
                col_s, col_d = st.columns(2)
                if col_s.form_submit_button("💾 GUARDAR CAMBIOS"):
                    c.execute("UPDATE proyectos SET fecha_creacion=?, cliente=?, suplidor=?, mueble=?, precio_venta=?, costo_fabrica=?, adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?",
                              (n_f.strftime("%Y-%m-%d"), n_c.upper(), n_s.upper(), n_m, n_pv, n_cf, n_ac, n_as, n_est, id_p))
                    conn.commit()
                    st.success("Cambiado.")
                    st.rerun()
                
                check_del = st.checkbox("Confirmar eliminación permanente")
                if col_d.form_submit_button("🗑️ ELIMINAR"):
                    if check_del:
                        c.execute("DELETE FROM proyectos WHERE id=?", (id_p,))
                        c.execute("DELETE FROM historial_pagos WHERE proyecto_id=?", (id_p,))
                        conn.commit()
                        st.rerun()

    with tab_hist:
        df_h_edit = pd.read_sql("SELECT h.id, h.fecha, p.cliente, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id ORDER BY h.fecha DESC", conn)
        if not df_h_edit.empty:
            opc_h = [f"Pago ID {r['id']} | {r['cliente']} | {r['tipo_movimiento']} | ${r['monto']}" for _, r in df_h_edit.iterrows()]
            sel_h = st.selectbox("Seleccione el pago a corregir:", opc_h)
            id_h = int(sel_h.split(" ")[2])
            p_h = df_h_edit[df_h_edit['id'] == id_h].iloc[0]
            with st.form("edit_pago_fecha"):
                nueva_f_pago = st.date_input("Nueva Fecha del Pago:", datetime.strptime(p_h['fecha'], "%Y-%m-%d").date())
                if st.form_submit_button("Actualizar Fecha de Pago"):
                    c.execute("UPDATE historial_pagos SET fecha=? WHERE id=?", (nueva_f_pago.strftime("%Y-%m-%d"), id_h))
                    conn.commit()
                    st.success("✅ Fecha actualizada.")
                    st.rerun()

# --- 5. GASTOS VARIOS ---
elif choice == "Gastos Varios":
    st.header("⛽ Gastos Operativos")
    with st.form("g_v", clear_on_submit=True):
        con = st.text_input("Concepto (Ej: Comida, Transporte)")
        mon = st.number_input("Monto ($)", min_value=0.0)
        fec = st.date_input("Fecha:", date.today())
        if st.form_submit_button("Registrar Gasto"):
            if con and mon > 0:
                c.execute("INSERT INTO gastos_varios (fecha, concepto, monto) VALUES (?,?,?)", (fec.strftime("%Y-%m-%d"), con, mon))
                conn.commit()
                st.success("Gasto guardado.")
                st.rerun()

# --- 6. REPORTES Y RESPALDO (REFORZADO) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Reporte de Estado de Resultados")
    
    # Filtros de fecha en la barra lateral
    st.sidebar.subheader("Periodo del Reporte")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    
    s_ini, s_fin = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")

    # Obtener datos filtrados
    df_h = pd.read_sql(f"SELECT h.fecha, p.cliente, p.mueble, h.tipo_movimiento, h.monto FROM historial_pagos h JOIN proyectos p ON h.proyecto_id = p.id WHERE h.fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{s_ini}' AND '{s_fin}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    tab_res, tab_sal, tab_resp = st.tabs(["📈 Resultados del Periodo", "👥 Saldos Pendientes", "📦 Respaldo"])

    with tab_res:
        # CÁLCULOS CLAVE
        ingresos_totales = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        pagos_fabrica = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gastos_operativos = df_g['monto'].sum() or 0.0
        utilidad_neta = ingresos_totales - pagos_fabrica - gastos_operativos
        
        # VISUALIZACIÓN DE MÉTRICAS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("INGRESOS (COBROS)", f"${ingresos_totales:,.2f}")
        c2.metric("PAGOS A FÁBRICA", f"${pagos_fabrica:,.2f}")
        c3.metric("GASTOS VARIOS", f"${gastos_operativos:,.2f}")
        c4.metric("UTILIDAD NETA", f"${utilidad_neta:,.2f}", delta_color="normal")
        
        st.write("---")
        st.subheader("Detalle de Movimientos en el Rango Seleccionado")
        if not df_h.empty:
            st.dataframe(df_h.style.format({"monto": "${:,.2f}"}), use_container_width=True)
        else:
            st.info("No hay movimientos de dinero en estas fechas.")

    with tab_sal:
        if not df_p.empty:
            df_p['Por Cobrar'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Por Pagar'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            col_a, col_b = st.columns(2)
            col_a.subheader("Cuentas por Cobrar (Clientes)")
            col_a.table(df_p[df_p['Por Cobrar'] > 0][['cliente', 'mueble', 'Por Cobrar']].style.format({"Por Cobrar": "${:,.2f}"}))
            col_b.subheader("Cuentas por Pagar (Suplidores)")
            col_b.table(df_p[df_p['Por Pagar'] > 0][['suplidor', 'mueble', 'Por Pagar']].style.format({"Por Pagar": "${:,.2f}"}))

    with tab_resp:
        st.write("Descargar base de datos completa para Excel")
        st.download_button("Descargar CSV", df_p.to_csv(index=False).encode('utf-8'), "muebleria_completo.csv")
