import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. CONEXIÓN A BASE DE DATOS
def get_connection():
    return sqlite3.connect('muebles_negocio.db', check_same_thread=False)

conn = get_connection()
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS proyectos 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, mueble TEXT, 
              suplidor TEXT, precio_venta REAL, costo_fabrica REAL, 
              adelanto_cliente REAL, adelanto_suplidor REAL, estado TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS gastos_varios 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, monto REAL)''')
conn.commit()

st.set_page_config(page_title="Muebles Pro v5", layout="wide")

# --- MENÚ LATERAL ---
st.sidebar.title("🛠️ Panel de Control")
menu = ["Nuevo Proyecto", "Ver / Gestionar Proyectos", "Pagos y Abonos", "✏️ Corregir Datos", "Gastos Varios", "Reportes y Respaldo"]
choice = st.sidebar.selectbox("Seleccione una opción", menu)

# --- OPCIÓN 1: NUEVO PROYECTO ---
if choice == "Nuevo Proyecto":
    st.header("📝 Registrar Nuevo Proyecto")
    with st.form("form_nuevo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nombre del Cliente").upper()
        suplidor = col2.text_input("Nombre del Suplidor (Fábrica)").upper()
        mueble = st.text_area("Descripción del Mueble / Materiales")
        c1, c2 = st.columns(2)
        p_venta = c1.number_input("Precio de Venta ($)", min_value=0.0)
        c_fabrica = c2.number_input("Costo de Fábrica ($)", min_value=0.0)
        if st.form_submit_button("Guardar Proyecto"):
            if cliente and suplidor:
                c.execute("INSERT INTO proyectos (cliente, mueble, suplidor, precio_venta, costo_fabrica, adelanto_cliente, adelanto_suplidor, estado) VALUES (?,?,?,?,?,?,?,?)",
                          (cliente, mueble, suplidor, p_venta, c_fabrica, 0.0, 0.0, "En Proceso"))
                conn.commit()
                st.success("✅ Proyecto guardado.")

# --- OPCIÓN 2: VER / GESTIONAR ---
elif choice == "Ver / Gestionar Proyectos":
    st.header("📋 Gestión de Proyectos")
    df_proyectos = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df_proyectos.empty:
        st.subheader("⚠️ Acciones Rápidas")
        col_id, col_acc, col_btn = st.columns([1, 2, 1])
        id_target = col_id.number_input("ID del Proyecto:", min_value=1, step=1)
        accion_tipo = col_acc.selectbox("Seleccione Acción:", ["---", "Marcar como ENTREGADO", "ELIMINAR PERMANENTE"])
        if col_btn.button("EJECUTAR"):
            if accion_tipo == "Marcar como ENTREGADO":
                c.execute("UPDATE proyectos SET estado = 'Entregado' WHERE id = ?", (id_target,))
            elif accion_tipo == "ELIMINAR PERMANENTE":
                c.execute("DELETE FROM proyectos WHERE id = ?", (id_target,))
            conn.commit()
            st.success("Cambio realizado. Refresque la pestaña.")
        st.divider()
        st.dataframe(df_proyectos, use_container_width=True)
    else:
        st.info("No hay proyectos.")

# --- OPCIÓN 3: PAGOS Y ABONOS (Suma al acumulado) ---
elif choice == "Pagos y Abonos":
    st.header("💰 Registro de Abonos")
    df = pd.read_sql("SELECT id, cliente, mueble FROM proyectos WHERE estado != 'Entregado'", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']}" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione Proyecto:", opciones)
        id_p = int(selec.split(" ")[1])
        tipo = st.radio("Movimiento:", ["Cobro a Cliente", "Pago a Fábrica"])
        monto = st.number_input("Monto a SUMAR al balance ($)", min_value=0.0)
        if st.button("Guardar Pago"):
            campo = "adelanto_cliente" if "Cliente" in tipo else "adelanto_suplidor"
            c.execute(f"UPDATE proyectos SET {campo} = {campo} + ? WHERE id = ?", (monto, id_p))
            conn.commit()
            st.success("Monto sumado correctamente.")
    else:
        st.warning("No hay proyectos activos.")

# --- NUEVA OPCIÓN 4: CORREGIR DATOS (Sobrescribe valores) ---
elif choice == "✏️ Corregir Datos":
    st.header("✏️ Modificar Montos de Proyecto")
    st.info("Use esta opción si se equivocó al escribir un número y quiere reemplazarlo.")
    df = pd.read_sql("SELECT * FROM proyectos", conn)
    if not df.empty:
        opciones = [f"ID {row['id']} - {row['cliente']} ({row['mueble'][:20]})" for _, row in df.iterrows()]
        selec = st.selectbox("Seleccione el proyecto a corregir:", opciones)
        id_p = int(selec.split(" ")[1])
        
        # Obtener datos actuales del proyecto seleccionado
        p_actual = df[df['id'] == id_p].iloc[0]
        
        with st.form("form_edicion"):
            col_a, col_b = st.columns(2)
            nuevo_pv = col_a.number_input("Corregir Precio Venta ($)", value=float(p_actual['precio_venta']))
            nuevo_cf = col_b.number_input("Corregir Costo Fábrica ($)", value=float(p_actual['costo_fabrica']))
            
            col_c, col_d = st.columns(2)
            nuevo_ac = col_c.number_input("Corregir Adelanto Cliente ($)", value=float(p_actual['adelanto_cliente']))
            nuevo_as = col_d.number_input("Corregir Adelanto Suplidor ($)", value=float(p_actual['adelanto_suplidor']))
            
            nuevo_estado = st.selectbox("Estado:", ["En Proceso", "Entregado"], index=0 if p_actual['estado'] == "En Proceso" else 1)
            
            if st.form_submit_button("✅ GUARDAR CORRECCIONES"):
                c.execute('''UPDATE proyectos SET precio_venta=?, costo_fabrica=?, 
                             adelanto_cliente=?, adelanto_suplidor=?, estado=? WHERE id=?''', 
                          (nuevo_pv, nuevo_cf, nuevo_ac, nuevo_as, nuevo_estado, id_p))
                conn.commit()
