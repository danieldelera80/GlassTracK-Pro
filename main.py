import streamlit as st
from config import init_db, verificar_licencia
from styles import CSS_GLOBAL, render_sb_header

st.set_page_config(
    page_title="Contacto S.A. — Producción",
    page_icon="🏭",
    layout="centered",
)

verificar_licencia()
init_db()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

with st.sidebar:
    render_sb_header()
    st.caption("Seleccioná una sección para comenzar.")
    st.markdown('<div style="margin-top:8px;color:#2a3a4a;font-size:11px;text-align:center;">v1.0 · Fabrica Produccion</div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; padding: 20px 0 10px;">
    <div style="font-size:52px;">🏭</div>
    <div style="font-size:24px; font-weight:800; color:#e0e8f5; margin-top:8px;">
        Control de Producción
    </div>
    <div style="font-size:14px; color:#4a6a9a; margin-top:4px; letter-spacing:2px; text-transform:uppercase;">
        Contacto S.A. — Fabrica Produccion
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()
st.markdown("#### Seleccioná una opción:")
st.write("")

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Monitor\nde Producción", use_container_width=True):
        st.switch_page("pages/01_Monitor.py")

with col2:
    if st.button("📋 Cargar\nOrden", use_container_width=True):
        st.switch_page("pages/02_Formulario.py")
