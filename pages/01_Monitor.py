import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from config import SECTORES_PRODUCCION, DB_PATH, init_db, verificar_licencia
from styles import CSS_GLOBAL, render_sb_header

st.set_page_config(
    page_title="Monitor de Producción",
    page_icon="🚀",
    layout="wide",
)

verificar_licencia()
init_db()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

# ── Auto-refresh cada 15 segundos ─────────────────────────────────────────────
st_autorefresh(interval=15_000, key="monitor_autorefresh")


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS  (TTL corto para que auto-refresh traiga datos frescos)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=5)
def cargar_datos():
    """
    Retorna:
      df_prod   : DataFrame con TODOS los registros de producción (sin Entrega)
      df_entrega: DataFrame con registros de Entrega
      entregadas: set de órdenes que ya pasaron por Entrega
      fallos    : set de órdenes que aparecen más de una vez en producción
                  (escaneadas 2+ veces = producto roto o con fallo)
    """
    conn     = sqlite3.connect(DB_PATH)
    df_total = pd.read_sql_query(
        "SELECT * FROM registros ORDER BY fecha_hora DESC", conn
    )
    conn.close()

    if df_total.empty:
        return pd.DataFrame(), pd.DataFrame(), set(), set()

    df_total["fecha_hora"] = pd.to_datetime(df_total["fecha_hora"])

    df_entrega = df_total[df_total["sector"] == "Entrega"].copy()
    df_prod    = df_total[df_total["sector"] != "Entrega"].copy()

    entregadas: set = set(df_entrega["orden"].str.strip())

    # Órdenes que aparecen más de una vez en producción → fallo
    conteo = df_prod["orden"].str.strip().value_counts()
    fallos: set = set(conteo[conteo > 1].index)

    return df_prod, df_entrega, entregadas, fallos


def aplicar_estilos(df: pd.DataFrame, fallos: set, entregadas: set):
    """
    - Fila roja completa  : orden en fallos (escaneada 2+ veces = fallo)
    - Celda Estado verde  : orden entregada
    """
    if df.empty:
        return df

    col_estado = "Estado" if "Estado" in df.columns else None

    def estilo_fila(row):
        orden        = str(row.get("Orden", "")).strip()
        es_fallo     = orden in fallos
        es_entregado = orden in entregadas

        if es_fallo:
            estilos = ["background-color:#5c1010; color:#ffaaaa;"] * len(row)
            # Aunque la fila sea roja, la celda Estado muestra verde si entregado
            if col_estado and es_entregado:
                estilos[df.columns.get_loc(col_estado)] = \
                    "background-color:#1a4a2e; color:#4ada75; font-weight:700; text-align:center;"
            return estilos

        estilos = [""] * len(row)
        if col_estado and es_entregado:
            estilos[df.columns.get_loc(col_estado)] = \
                "background-color:#1a4a2e; color:#4ada75; font-weight:700; text-align:center;"
        return estilos

    return df.style.apply(estilo_fila, axis=1)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    render_sb_header()

    if st.button("🔄 Refrescar ahora", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    if st.button("🏠 Inicio", use_container_width=True):
        st.switch_page("main.py")
    if st.button("📋 Cargar Orden", use_container_width=True):
        st.switch_page("pages/02_Formulario.py")

    st.divider()
    st.caption("🔁 Auto-refresh cada 15 seg")
    st.markdown(
        f'<div class="sb-footer">DB: {DB_PATH.name}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("## 🚀 Monitor de Producción Industrial")

try:
    df_prod, df_entrega, entregadas, fallos = cargar_datos()
except Exception as e:
    st.error(f"❌ Error al conectar con la base de datos: {e}")
    st.stop()

hoy = datetime.now().date()


# ══════════════════════════════════════════════════════════════════════════════
#  MÉTRICAS GLOBALES
# ══════════════════════════════════════════════════════════════════════════════

df_prod_hoy    = df_prod[df_prod["fecha_hora"].dt.date == hoy]    if not df_prod.empty    else pd.DataFrame()
df_entrega_hoy = df_entrega[df_entrega["fecha_hora"].dt.date == hoy] if not df_entrega.empty else pd.DataFrame()

total_hoy      = len(df_prod_hoy)
entregados_hoy = len(df_entrega_hoy)
fallos_hoy     = int(df_prod_hoy["orden"].str.strip().isin(fallos).sum()) if not df_prod_hoy.empty else 0
sectores_hoy   = df_prod_hoy["sector"].nunique() if not df_prod_hoy.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Registros Hoy",   total_hoy)
c2.metric("✅ Entregados Hoy",  entregados_hoy)
c3.metric("🔴 Con Fallo Hoy",   fallos_hoy)
c4.metric("🏭 Sectores Activos", sectores_hoy)

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
#  BÚSQUEDA + TABLA UNIFICADA
# ══════════════════════════════════════════════════════════════════════════════

col_bus, col_info = st.columns([2, 1])
with col_bus:
    busqueda = st.text_input(
        "🔍 Buscar por número de orden",
        placeholder="Escribí el número de orden...",
        key="busqueda_orden",
    )
with col_info:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:12px; color:#4a6a9a; padding-top:8px;">'
        f'🔁 Actualización automática · últimos datos</div>',
        unsafe_allow_html=True,
    )

st.write("")

if df_prod.empty:
    st.info("📭 No hay registros de producción todavía.")
else:
    # ── Construir tabla unificada ─────────────────────────────────────────────
    df_vista = df_prod.copy()

    # Columna Estado
    df_vista["Estado"] = df_vista["orden"].str.strip().apply(
        lambda o: "✅ Entregado" if o in entregadas else ""
    )

    # Renombrar para mostrar
    df_vista = df_vista.rename(columns={
        "orden":      "Orden",
        "sector":     "Sector",
        "usuario":    "Operario",
        "carro":      "Carro",
        "lado":       "Lado",
        "fecha_hora": "Fecha / Hora",
    })

    # Columnas a mostrar (ocultar id)
    cols_show = ["Orden", "Sector", "Operario", "Carro", "Lado", "Fecha / Hora", "Estado"]
    df_vista  = df_vista[cols_show]

    # ── Filtro de búsqueda ────────────────────────────────────────────────────
    if busqueda.strip():
        mask     = df_vista["Orden"].astype(str).str.contains(busqueda.strip(), case=False, na=False)
        df_vista = df_vista[mask]
        if df_vista.empty:
            st.warning(f"⚠️ No se encontraron registros para la orden **{busqueda}**")
        else:
            st.success(f"🔍 {len(df_vista)} registro(s) encontrado(s) para la orden **{busqueda}**")

    # ── Leyenda ───────────────────────────────────────────────────────────────
    if not busqueda.strip():
        leg1, leg2, leg3 = st.columns(3)
        leg1.markdown(
            '<div style="background:#5c1010;color:#ffaaaa;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '🔴 Fallo / Rotura — escaneada 2+ veces</div>',
            unsafe_allow_html=True,
        )
        leg2.markdown(
            '<div style="background:#1a4a2e;color:#4ada75;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '✅ Orden entregada al cliente</div>',
            unsafe_allow_html=True,
        )
        leg3.markdown(
            '<div style="background:#1a1a2e;color:#aaa;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '⬜ Producción normal</div>',
            unsafe_allow_html=True,
        )
        st.write("")

    # ── Tabla con estilos ─────────────────────────────────────────────────────
    st.dataframe(
        aplicar_estilos(df_vista.reset_index(drop=True), fallos, entregadas),
        use_container_width=True,
        hide_index=True,
        height=520,
    )

    st.caption(f"Mostrando {len(df_vista)} registros · todos los sectores de producción")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN ENTREGAS
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("### 📦 Registro de Entregas")

if df_entrega.empty:
    st.info("📭 No se registró ninguna entrega todavía.")
else:
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Entregas Hoy",       len(df_entrega_hoy))
    col_e2.metric("Entregas Históricas", len(df_entrega))

    st.write("")

    df_ent_show = df_entrega[["orden", "usuario", "fecha_hora"]].rename(columns={
        "orden":      "Orden",
        "usuario":    "Operario",
        "fecha_hora": "Fecha / Hora",
    })

    # Filtrar entregas si hay búsqueda activa
    if busqueda.strip():
        df_ent_show = df_ent_show[
            df_ent_show["Orden"].astype(str).str.contains(busqueda.strip(), case=False, na=False)
        ]

    st.dataframe(df_ent_show, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO RANKING OPERARIOS (HOY)
# ══════════════════════════════════════════════════════════════════════════════

if not df_prod_hoy.empty:
    st.divider()
    st.markdown("### 📊 Ranking Operarios — Hoy")

    conteo = df_prod_hoy["usuario"].value_counts().reset_index()
    conteo.columns = ["Operario", "Registros"]

    fig = px.bar(
        conteo, x="Operario", y="Registros",
        color="Registros", text_auto=True, template="plotly_dark",
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(f"Sistema de Monitoreo — Camara Fabrica Produccion · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
