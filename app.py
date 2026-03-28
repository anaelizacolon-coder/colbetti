import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# 1. CONEXIÓN
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# ESTRUCTURA DE TABLAS
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

st.set_page_config(page_title="Mueblería Pro v17 - Multisuplidor", layout="wide")

menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 1. NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("f_n", clear_on_submit=True):
        f_p = st.date_input("Fecha:", date.today())
        col1, col2 = st.columns(2)
        cli = col1.text_input("Nombre del Cliente").upper()
        sup = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mue = st.text_area("Descripción del Producto (Ej: Closet Habitacion A)")
        c1, c2 = st.columns(2)
        p_v = c1.number_input("Precio Venta ($)", min_value=0.0)
        c_f = c2.number_input("Costo Fábrica ($)", min_value=0.0)
        if st.form_submit_button("Guardar Proyecto"):
            if cli and sup:
                c.execute("INSERT INTO proyectos (fecha_creacion, cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?,?)",
                          (f_p.strftime("%Y-%m-%d"), cli, mue, sup, p_v, c_f, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success(f"✅ Registrado: {mue} para {cli} (Fábrica: {sup})")

# --- 3. PAGOS Y ABONOS (MEJORADO PARA EVITAR CONFUSIÓN) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Pagos por Producto y Suplidor")
    # Traemos más datos para el selector
    df_act = pd.read_sql("SELECT id, cliente, mueble, suplidor FROM proyectos WHERE estado != 'Entregado'", conn)
    
    if not df_act.empty:
        # Ahora la opción muestra: ID - CLIENTE - MUEBLE (SUPLIDOR)
        opc = [f"ID {r['id']} | {r['cliente']} | {r['mueble'][:20]}... (Fábrica: {r['suplidor']})" for _, r in df_act.iterrows()]
        sel = st.selectbox("Seleccione el Proyecto Específico:", opc)
        id_p = int(sel.split(" ")[1])
        
        # Obtener datos del proyecto seleccionado para mostrar información de ayuda
        info_p = df_act[df_act['id'] == id_p].iloc[0]
        st.info(f"**Destino del pago:** Fábrica {info_p['suplidor']} | **Producto:** {info_p['mueble']}")
        
        col_t, col_f = st.columns(2)
        tipo = col_t.radio("Tipo de Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        fecha_m = col_f.date_input("Fecha:", date.today())
        monto = st.number_input("Monto ($)", min_value=0.0)
        
        if st.button("Registrar Movimiento"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            c.execute("INSERT INTO historial_pagos (proyecto_id, fecha, tipo_movimiento, monto) VALUES (?,?,?,?)",
                      (id_p, fecha_m.strftime("%Y-%m-%d"), tipo, monto))
            conn.commit()
            st.success(f"✅ Registrado: {tipo} de ${monto:,.2f} para {info_p['mueble']}")
    else:
        st.warning("No hay proyectos activos.")

# --- 6. REPORTES (CON DETALLE DE SUPLIDOR) ---
elif choice == "Reportes y Respaldo":
    st.header("📊 Inteligencia Financiera")
    st.sidebar.subheader("Filtro de Fecha")
    f_ini = st.sidebar.date_input("Desde", date(date.today().year, date.today().month, 1))
    f_fin = st.sidebar.date_input("Hasta", date.today())
    
    # Consulta avanzada para unir historial con nombres de suplidores y muebles
    query_h = f'''
        SELECT h.fecha, p.cliente, p.mueble, p.suplidor, h.tipo_movimiento, h.monto 
        FROM historial_pagos h
        JOIN proyectos p ON h.proyecto_id = p.id
        WHERE h.fecha BETWEEN '{f_ini.strftime("%Y-%m-%d")}' AND '{f_fin.strftime("%Y-%m-%d")}'
    '''
    df_h = pd.read_sql(query_h, conn)
    df_g = pd.read_sql(f"SELECT * FROM gastos_varios WHERE fecha BETWEEN '{f_ini.strftime('%Y-%m-%d')}' AND '{f_fin.strftime('%Y-%m-%d')}'", conn)
    df_p = pd.read_sql("SELECT * FROM proyectos", conn)

    t1, t2, t3 = st.tabs(["📈 Flujo de Caja Detallado", "👥 Deudas y Saldos", "📦 Respaldo"])

    with t1:
        ing = df_h[df_h['tipo_movimiento'] == 'Cobro a Cliente']['monto'].sum() or 0.0
        p_f = df_h[df_h['tipo_movimiento'] == 'Pago a Fábrica']['monto'].sum() or 0.0
        gas = df_g['monto'].sum() or 0.0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("COBROS CLIENTES", f"${ing:,.2f}")
        c2.metric("PAGOS A FÁBRICAS", f"${p_f:,.2f}")
        c3.metric("GASTOS VARIOS", f"${gas:,.2f}")
        c4.metric("UTILIDAD NETA", f"${(ing - p_f - gas):,.2f}")
        
        st.subheader("Historial de Movimientos Detallado")
        if not df_h.empty:
            st.dataframe(df_h.style.format({"monto": "${:,.2f}"}), use_container_width=True)
        else:
            st.info("No hay movimientos en este periodo.")

    with t2:
        if not df_p.empty:
            df_p['Saldo Cliente'] = df_p['precio_venta'] - df_p['adelanto_cliente']
            df_p['Saldo Fábrica'] = df_p['costo_fabrica'] - df_p['adelanto_suplidor']
            
            st.subheader("¿Quién me debe? (Por Cliente y Mueble)")
            st.table(df_p[df_p['Saldo Cliente'] > 0][['cliente', 'mueble', 'Saldo Cliente']].style.format({"Saldo Cliente": "${:,.2f}"}))
            
            st.subheader("¿A qué fábrica le debo? (Por Suplidor)")
            st.table(df_p[df_p['Saldo Fábrica'] > 0][['suplidor', 'mueble', 'Saldo Fábrica']].style.format({"Saldo Fábrica": "${:,.2f}"}))

    with t3:
        st.download_button("Exportar Todo a CSV", df_p.to_csv(index=False).encode('utf-8'), "muebleria_completo.csv")

# (Las opciones Ver / Gestionar, Corregir y Gastos se mantienen con la lógica de v15/v16)
