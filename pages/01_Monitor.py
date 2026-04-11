import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta

_ARG_TZ = timezone(timedelta(hours=-3))
from streamlit_autorefresh import st_autorefresh
from sqlalchemy import text

from config import SECTORES_PRODUCCION, verificar_licencia, get_connection, verificar_estado_sistema
from config import SECTORES_ESCANEO_DIRECTO
from styles import CSS_GLOBAL, render_sb_header

st.set_page_config(
    page_title="Control de Produccion",
    page_icon="🏭",
    layout="wide",
)

verificar_licencia()
verificar_estado_sistema()
conn = get_connection()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

st.markdown("""
<style>
@keyframes blinkOrange {
  0% { background-color: #5c2000 !important; }
  50% { background-color: #f97316 !important; color: white !important; }
  100% { background-color: #5c2000 !important; }
}
@keyframes blinkRed {
  0% { background-color: #5c1010 !important; opacity: 1.0 !important; color: white !important; }
  50% { background-color: #ef4444 !important; opacity: 0.3 !important; color: white !important; text-shadow: 0 0 8px #ffaaaa; }
  100% { background-color: #5c1010 !important; opacity: 1.0 !important; color: white !important; }
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 4px;
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding-bottom: 0;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
    background: rgba(15,23,42,0.6) !important;
    border-radius: 10px 10px 0 0 !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 10px 20px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-bottom: none !important;
    transition: all 0.2s !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
    background: rgba(30,41,59,0.9) !important;
    color: #e2e8f0 !important;
}
[data-testid="stTabs"] button[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg, #1e3a8a, #1e293b) !important;
    color: #60a5fa !important;
    border-color: rgba(59,130,246,0.3) !important;
}
[data-testid="stTabContent"] {
    padding-top: 20px !important;
}
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=15_000, key="monitor_autorefresh")
_ultimo_refresh = datetime.now(_ARG_TZ).strftime("%H:%M:%S")
st.toast(f"Datos actualizados a las {_ultimo_refresh}", icon="🔄")


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def cargar_datos():
    query = "SELECT * FROM registros WHERE fecha_hora >= NOW() - INTERVAL '90 days' ORDER BY fecha_hora DESC"
    df_total = conn.query(query, ttl=0)

    if df_total is None or df_total.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), set(), set(), set(), pd.DataFrame()

    df_total["fecha_hora"] = (
        pd.to_datetime(df_total["fecha_hora"], utc=True)
        .dt.tz_convert("America/Argentina/Buenos_Aires")
        .dt.tz_localize(None)
    )
    df_total["orden"] = df_total["orden"].astype(str).str.strip()

    _pfx = re.compile(r'^\s*\[(URGENTE|INCIDENCIA)\]\s*', re.IGNORECASE)
    df_total["_base"] = df_total["orden"].apply(lambda x: _pfx.sub("", x).strip())
    _bases_urg = set(df_total.loc[df_total["orden"].str.contains(r'\[URGENTE\]', case=False, na=False), "_base"])
    _bases_inc = set(df_total.loc[df_total["orden"].str.contains(r'\[INCIDENCIA\]', case=False, na=False), "_base"]) - _bases_urg

    def _normalizar_orden(row):
        base = row["_base"]
        if base in _bases_urg:  return f"[URGENTE] {base}"
        if base in _bases_inc:  return f"[INCIDENCIA] {base}"
        return base

    df_total["orden"] = df_total.apply(_normalizar_orden, axis=1)
    df_total = df_total.drop(columns=["_base"])

    df_entrega   = df_total[df_total["sector"] == "Entrega"].copy()
    df_terminado = df_total[df_total["sector"] == "Terminado"].copy()
    df_danado    = df_total[df_total["sector"] == "Dañado"].copy()
    df_prod      = df_total[~df_total["sector"].isin(["Entrega", "Terminado", "Dañado"])].copy()

    df_estado_actual = (
        df_total
        .sort_values("fecha_hora", ascending=False)
        .drop_duplicates(subset=["orden"], keep="first")
        .copy()
    )
    df_estado_actual["orden"] = df_estado_actual["orden"].astype(str).str.strip()

    entregadas: set = set(df_estado_actual[df_estado_actual["sector"] == "Entrega"]["orden"])
    terminadas: set = set(df_estado_actual[df_estado_actual["sector"] == "Terminado"]["orden"])
    danadas:    set = set(df_estado_actual[df_estado_actual["sector"] == "Dañado"]["orden"])

    return df_total, df_prod, df_entrega, df_terminado, entregadas, terminadas, danadas, df_estado_actual


def aplicar_estilos(df: pd.DataFrame, entregadas: set, terminadas: set, danadas: set):
    if df.empty:
        return df

    col_estado = "Estado" if "Estado" in df.columns else None
    ahora = datetime.now(_ARG_TZ).replace(tzinfo=None)

    def estilo_fila(row):
        orden        = str(row.get("Orden", "")).strip()
        es_entregado = orden in entregadas
        es_terminado = orden in terminadas
        es_danado    = orden in danadas
        es_urgente   = "[URGENTE]" in orden.upper()
        es_incidente = "[INCIDENCIA]" in orden.upper()
        sector_str   = str(row.get("Sector", ""))
        fecha_val    = row.get("Fecha / Hora", None)
        parpadeo     = False

        if sector_str.startswith("Enviado a") and fecha_val is not pd.NaT:
            try:
                if isinstance(fecha_val, str):
                    fecha_val = pd.to_datetime(fecha_val, format="%d/%m/%Y %H:%M", errors="coerce")
                if fecha_val is not None and not pd.isna(fecha_val):
                    if (ahora - fecha_val).total_seconds() > 30 * 60:
                        parpadeo = True
            except:
                pass

        if es_incidente:
            return ["background-color: #7a1a1a; color: #ffaaaa; border-bottom: 2px solid #ef4444; font-weight: bold;"] * len(row)
        if es_urgente:
            return ['background-color: #900000; color: white; font-weight: bold;'] * len(row)
        if es_danado:
            estilos = ["background-color:#5c1010; color:#ffaaaa;"] * len(row)
            if col_estado:
                estilos[df.columns.get_loc(col_estado)] = "background-color:#7a1a1a; color:#ff8a8a; font-weight:700; text-align:center;"
            return estilos

        estilos = [""] * len(row)
        if parpadeo:
            estilos = ["animation: blinkOrange 1.5s infinite; font-weight:bold;"] * len(row)
        if es_entregado:
            estilos = ["background-color:#0d2818; color:#78d495;"] * len(row)
            if col_estado:
                estilos[df.columns.get_loc(col_estado)] = "background-color:#1a4a2e; color:#4ada75; font-weight:700; text-align:center;"
        elif es_terminado:
            estilos = ["background-color:#261f00; color:#d6b04b;"] * len(row)
            if col_estado:
                estilos[df.columns.get_loc(col_estado)] = "background-color:#3a2e00; color:#f0c040; font-weight:700; text-align:center;"
        return estilos

    return df.style.apply(estilo_fila, axis=1)


# ══════════════════════════════════════════════════════════════════════════════
#  MODAL DE FICHA
# ══════════════════════════════════════════════════════════════════════════════
from config import ADMIN_PASSWORD

@st.dialog("📋 Ficha Interactiva de Orden")
def mostrar_modal_orden(orden_actual):
    from sqlalchemy import text as _text
    df_det = conn.query(
        "SELECT * FROM registros WHERE TRIM(orden) = :ord ORDER BY fecha_hora ASC",
        params={"ord": orden_actual}, ttl=0
    )
    if df_det is None or df_det.empty:
        st.warning("No hay registros históricos.")
        return

    # Convertir siempre de UTC a hora Argentina para mostrar correcto
    df_det["fecha_hora"] = (
        pd.to_datetime(df_det["fecha_hora"], utc=True)
        .dt.tz_convert("America/Argentina/Buenos_Aires")
        .dt.tz_localize(None)
    )
    st.markdown("#### ⏳ Historial de Movimientos")
    df_det_display = df_det[["fecha_hora", "sector", "usuario", "carro", "lado"]].copy()
    df_det_display["fecha_hora"] = df_det_display["fecha_hora"].dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(df_det_display, use_container_width=True, hide_index=True)

    t_ini = df_det.iloc[0]["fecha_hora"]
    t_fin = datetime.now(_ARG_TZ).replace(tzinfo=None)
    if df_det.iloc[-1]["sector"] in ["Entrega", "Terminado"]:
        t_fin = df_det.iloc[-1]["fecha_hora"]
    delta = t_fin - t_ini
    st.info(f"📌 **Tiempo en planta:** {delta.components.days} días y {delta.components.hours} horas.")

    st.divider()
    st.markdown("#### 🚨 Acciones Críticas")
    pass_input = st.text_input("🔑 Contraseña de Seguridad (Admin):", type="password")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔥 Urgente", type="primary", use_container_width=True):
            if pass_input == ADMIN_PASSWORD:
                if "[URGENTE]" not in orden_actual:
                    nuevo = f"[URGENTE] {orden_actual}"
                    with conn.session as s:
                        s.execute(_text("UPDATE registros SET orden = :n WHERE TRIM(orden) = :v"), {"n": nuevo, "v": orden_actual})
                        s.commit()
                    st.success("🚀 Prioridad inyectada.")
                    st.rerun()
                else:
                    st.info("Ya tiene prioridad alta.")
            elif pass_input:
                st.error("Contraseña incorrecta.")
    with c2:
        if st.button("🚨 Incidencia", type="primary", use_container_width=True):
            if pass_input == ADMIN_PASSWORD:
                if "[INCIDENCIA]" not in orden_actual:
                    nuevo = f"[INCIDENCIA] {orden_actual}"
                    with conn.session as s:
                        s.execute(_text("UPDATE registros SET orden = :n WHERE TRIM(orden) = :v"), {"n": nuevo, "v": orden_actual})
                        s.commit()
                    st.success("🚨 Incidencia inyectada.")
                    st.rerun()
                else:
                    st.info("Ya está con incidencia.")
            elif pass_input:
                st.error("Contraseña incorrecta.")
    with c3:
        if st.button("🗑️ Eliminar", type="primary", use_container_width=True):
            if pass_input == ADMIN_PASSWORD:
                with conn.session as s:
                    s.execute(_text("DELETE FROM registros WHERE TRIM(orden) = :v"), {"v": orden_actual})
                    s.commit()
                st.success("✅ Orden borrada.")
                st.rerun()
            elif pass_input:
                st.error("Contraseña incorrecta.")


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

    if st.session_state.get("is_admin", False):
        import csv
        from pathlib import Path
        from sqlalchemy import text as _text

        OFFLINE_FILE = Path(__file__).parent.parent / "offline_records.csv"
        if OFFLINE_FILE.exists():
            try:
                with open(OFFLINE_FILE, "r", encoding="utf-8") as f:
                    filas_offline = list(csv.DictReader(f))
                count = len(filas_offline)
                if count > 0:
                    st.divider()
                    with st.expander("🛠️ Sincronización Local", expanded=False):
                        st.markdown(f"""
                            <div style="background:#4a1c11; border: 1px solid #f97316; padding: 10px; border-radius: 8px; text-align:center;">
                                <span style="font-size:14px; color:#f97316; font-weight:bold;">⚠️ Hay {count} registros locales sin subir</span>
                            </div><br>
                        """, unsafe_allow_html=True)
                        if st.button("🔄 Sincronizar Nube", type="primary", use_container_width=True):
                            idx_exito = 0
                            with conn.session as s:
                                for row in filas_offline:
                                    s.execute(_text("""
                                        INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                        VALUES (:f, :o, :c, :l, :u, :s)
                                    """), {"f": row["fecha_hora"], "o": row["orden"], "c": row["carro"],
                                           "l": row["lado"], "u": row["usuario"], "s": row["sector"]})
                                    idx_exito += 1
                                s.commit()
                            OFFLINE_FILE.unlink()
                            st.success(f"✅ ¡{idx_exito} registros sincronizados!")
                            st.cache_data.clear()
                            st.rerun()
            except Exception as e:
                st.error(f"❌ Error leyendo caché: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  CARGA DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🏭 Control de Produccion")

try:
    df_total, df_prod, df_entrega, df_terminado, entregadas, terminadas, danadas, df_estado_actual = cargar_datos()
except Exception as e:
    st.error(f"❌ Error al conectar con la base de datos: {e}")
    st.stop()

hoy = datetime.now(_ARG_TZ).date()

df_prod_hoy    = df_prod[df_prod["fecha_hora"].dt.date == hoy]       if not df_prod.empty    else pd.DataFrame()
df_entrega_hoy = df_entrega[df_entrega["fecha_hora"].dt.date == hoy] if not df_entrega.empty else pd.DataFrame()

total_hoy      = df_prod_hoy["orden"].nunique()    if not df_prod_hoy.empty    else 0
entregados_hoy = df_entrega_hoy["orden"].nunique() if not df_entrega_hoy.empty else 0
sectores_hoy   = df_prod_hoy["sector"].nunique()   if not df_prod_hoy.empty    else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="glass-metric"><div class="glass-title">📦 Órdenes Hoy</div><div class="glass-value">{total_hoy}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="glass-metric"><div class="glass-title">✅ Entregados Hoy</div><div class="glass-value green">{entregados_hoy}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="glass-metric"><div class="glass-title">🏭 Sectores Activos</div><div class="glass-value">{sectores_hoy}</div></div>', unsafe_allow_html=True)
st.write("")


# ══════════════════════════════════════════════════════════════════════════════
#  TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════
_es_admin = st.session_state.get("is_admin", False)

if _es_admin and not df_prod.empty:
    tab_prod, tab_rend, tab_admin = st.tabs(["📋  Producción", "📊  Rendimiento", "⚙️  Admin"])
else:
    tab_prod, tab_rend = st.tabs(["📋  Producción", "📊  Rendimiento"])
    tab_admin = None


# ── TAB 1: PRODUCCIÓN ────────────────────────────────────────────────────────
with tab_prod:

    # ── Alertas urgentes ─────────────────────────────────────────────────────
    if not df_total.empty:
        _urgentes = [o for o in df_total["orden"].unique() if "[URGENTE]" in str(o).upper() and o not in entregadas]
        for _i, _urg in enumerate(_urgentes):
            _sector_urg = df_total[df_total["orden"] == _urg].sort_values("fecha_hora", ascending=False).iloc[0]["sector"]
            _col_banner, _col_btn = st.columns([6, 1])
            with _col_banner:
                st.markdown(f"""
                <div class="alerta-urgente">
                    <span style="font-size:28px; flex-shrink:0;">🚨</span>
                    <div>
                        <div class="alerta-urgente-titulo">⚡ Prioridad Urgente Activa</div>
                        <div class="alerta-urgente-ordenes">{_urg}</div>
                        <div style="font-size:12px; color:#fca5a5; margin-top:4px;">📍 Sector actual: <b>{_sector_urg}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with _col_btn:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if st.button("👁️ Abrir", key=f"urgbtn_{_i}", use_container_width=True):
                    mostrar_modal_orden(_urg)

    # ── Barra de búsqueda + filtro de estado ─────────────────────────────────
    col_srch, col_filt = st.columns([3, 2])
    with col_srch:
        busqueda = st.text_input(
            "Buscar",
            placeholder="🔍 Número de orden, operario o sector...",
            key="busqueda_orden",
            label_visibility="collapsed",
        )
    with col_filt:
        ESTADOS_OPCIONES = ["🔵 Todos", "⚙️ En Proceso", "📥 Pendiente", "⏳ Terminado", "✅ Entregado", "⚠️ Dañado"]
        filtro_estado = st.selectbox(
            "Filtrar por estado",
            options=ESTADOS_OPCIONES,
            key="filtro_estado",
            label_visibility="collapsed",
        )
    st.write("")

    if df_total.empty:
        st.info("📭 No hay registros de producción todavía.")
    else:
        df_vista = (
            df_estado_actual.copy()
            .assign(_es_hoy=lambda d: d["fecha_hora"].dt.date == hoy)
            .sort_values(["_es_hoy", "fecha_hora"], ascending=[False, False])
            .drop(columns="_es_hoy")
            .reset_index(drop=True)
        )

        def calcular_estado(row):
            o = str(row["orden"]).strip()
            s = str(row["sector"]).strip()
            if o in danadas:    return "⚠️ Dañado"
            if o in entregadas: return "✅ Entregado"
            if o in terminadas: return "⏳ Terminado"
            if s.startswith("En Proceso en"): return "⚙️ En Proceso"
            if s.startswith("Enviado a"):     return "📥 Pendiente"
            return ""

        df_vista["Estado"] = df_vista.apply(calcular_estado, axis=1)
        df_vista["fecha_hora"] = df_vista["fecha_hora"].dt.strftime("%d/%m/%Y %H:%M")
        df_vista = df_vista.rename(columns={
            "orden": "Orden", "sector": "Sector", "usuario": "Operario",
            "carro": "Carro", "lado": "Lado", "fecha_hora": "Fecha / Hora",
        })
        cols_show = ["Orden", "Sector", "Operario", "Carro", "Lado", "Fecha / Hora", "Estado"]
        df_vista  = df_vista[cols_show]

        # ── Filtro por estado ─────────────────────────────────────────────────
        if filtro_estado != "🔵 Todos":
            _estado_key = filtro_estado.split(" ", 1)[1]
            df_vista = df_vista[df_vista["Estado"].str.contains(_estado_key, na=False)]

        # ── Filtro por texto ──────────────────────────────────────────────────
        if busqueda.strip():
            busq = busqueda.strip().lower()
            mask = (
                df_vista["Orden"].astype(str).str.lower().str.contains(busq, regex=False, na=False) |
                df_vista["Sector"].astype(str).str.lower().str.contains(busq, regex=False, na=False) |
                df_vista["Operario"].astype(str).str.lower().str.contains(busq, regex=False, na=False)
            )
            df_vista = df_vista[mask]
            if df_vista.empty:
                st.warning(f"⚠️ Sin resultados para **{busqueda}**")
            else:
                st.success(f"🔍 {len(df_vista)} resultado(s) · estado: {filtro_estado}")
        elif filtro_estado != "🔵 Todos":
            st.success(f"Mostrando: **{filtro_estado}** — {len(df_vista)} orden(es)")

        # ── Leyenda (solo sin filtros activos) ────────────────────────────────
        if filtro_estado == "🔵 Todos" and not busqueda.strip():
            leg1, leg2, leg3 = st.columns(3)
            leg1.markdown('<div style="background:#5c1010;color:#ff8a8a;padding:6px 12px;border-radius:6px;font-size:12px;text-align:center;">⚠️ Dañado</div>', unsafe_allow_html=True)
            leg2.markdown('<div style="background:#3a2e00;color:#f0c040;padding:6px 12px;border-radius:6px;font-size:12px;text-align:center;">⏳ Terminado — esperando entrega</div>', unsafe_allow_html=True)
            leg3.markdown('<div style="background:#1a4a2e;color:#4ada75;padding:6px 12px;border-radius:6px;font-size:12px;text-align:center;">✅ Orden entregada al cliente</div>', unsafe_allow_html=True)
            st.write("")

        st.markdown("<p style='font-size:13px; color:#4a6a9a;'>Presioná sobre una fila para ver el detalle de la orden.</p>", unsafe_allow_html=True)

        seleccion_evento = st.dataframe(
            aplicar_estilos(df_vista.reset_index(drop=True), entregadas, terminadas, danadas),
            use_container_width=True,
            hide_index=True,
            height=580,
            selection_mode="single-row",
            on_select="rerun",
        )

        if hasattr(seleccion_evento, "selection") and seleccion_evento.selection.rows:
            row_idx   = seleccion_evento.selection.rows[0]
            orden_str = str(df_vista.reset_index(drop=True).iloc[row_idx]["Orden"]).strip()
            mostrar_modal_orden(orden_str)

        st.caption(f"Mostrando {len(df_vista)} registros · filtro: {filtro_estado}")


# ── TAB 2: RENDIMIENTO ───────────────────────────────────────────────────────
with tab_rend:
    if df_prod_hoy.empty:
        st.info("📭 Sin movimientos registrados hoy.")
    else:
        fecha_format = hoy.strftime("%d/%m/%Y")
        st.markdown(f"### 🎯 Rendimiento del Turno — {fecha_format}")

        conteo = df_prod_hoy["usuario"].value_counts().reset_index()
        conteo.columns = ["Operario", "Total Vidrios"]
        ultimos_movs = df_prod_hoy.groupby("usuario")["fecha_hora"].max().reset_index()
        ultimos_movs.columns = ["Operario", "Último Mov."]
        ultimos_movs["Último Mov."] = ultimos_movs["Último Mov."].dt.strftime("%H:%M")
        df_rendimiento = pd.merge(conteo, ultimos_movs, on="Operario")
        total_vidrios_turno = df_rendimiento["Total Vidrios"].sum()
        df_rendimiento["% Turno"] = (df_rendimiento["Total Vidrios"] / total_vidrios_turno * 100).round(1)

        df_grafico = df_rendimiento.sort_values("Total Vidrios", ascending=True)
        _RANK_COLORS = ["#f59e0b", "#94a3b8", "#b45309"]
        n_ops = len(df_grafico)
        bar_colors = [_RANK_COLORS[n_ops - 1 - _i] if (n_ops - 1 - _i) < 3 else "#3b82f6" for _i in range(n_ops)]

        fig = go.Figure(go.Bar(
            x=df_grafico["Total Vidrios"], y=df_grafico["Operario"], orientation="h",
            marker=dict(color=bar_colors, opacity=0.92, line=dict(color="rgba(255,255,255,0.12)", width=1)),
            text=df_grafico["Total Vidrios"], textposition="inside", insidetextanchor="middle",
            textfont=dict(size=17, color="white", family="Outfit, sans-serif"),
            customdata=df_grafico[["% Turno", "Último Mov."]].values,
            hovertemplate="<b>%{y}</b><br>Vidrios: <b>%{x}</b><br>% turno: <b>%{customdata[0]}%</b><br>Último mov: <b>%{customdata[1]}</b><extra></extra>",
        ))
        fig.update_layout(
            template="plotly_dark", showlegend=False, margin=dict(t=10, b=10, l=20, r=40),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False, tickfont=dict(size=13, color="#94a3b8")),
            yaxis=dict(showgrid=False, tickfont=dict(size=15, color="#e2e8f0")),
            height=max(180, n_ops * 85), bargap=0.38,
            hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(size=13, family="Outfit, sans-serif", color="white")),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📑 Reporte del Turno")
        df_tabla = df_rendimiento.sort_values("Total Vidrios", ascending=False).reset_index(drop=True)
        df_tabla["% Turno"] = df_tabla["% Turno"].astype(str) + "%"
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)


# ── TAB 3: ADMIN ─────────────────────────────────────────────────────────────
if tab_admin is not None:
    with tab_admin:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1e293b, #0f172a); border-left: 5px solid #3b82f6; border-radius:12px;
                    padding:20px; margin-bottom:16px;">
            <div style="font-size:18px; color:#60a5fa; font-weight:800; letter-spacing:1px;">
                ⚡ MODO ADMINISTRADOR — Edición Rápida
            </div>
            <div style="font-size:12px; color:#94a3b8; margin-top:4px;">
                Encuentre la orden, modifique estado o número, y guarde los cambios al instante.
            </div>
        </div>
        """, unsafe_allow_html=True)

        df_calc = df_prod.copy()
        df_calc["orden_trim"] = df_calc["orden"].astype(str).str.strip()
        df_calc = df_calc.sort_values("fecha_hora", ascending=True)
        df_origen = df_calc.groupby("orden_trim")["sector"].first().rename("sector_origen")
        df_actual = df_calc.groupby("orden_trim")["sector"].last().rename("sector_actual")
        df_usr    = df_calc.groupby("orden_trim")["usuario"].last().rename("usuario_actual")
        df_unicas = pd.concat([df_origen, df_actual, df_usr], axis=1).reset_index()

        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        with col_f1:
            ops_origen    = ["Todos"] + sorted(df_unicas["sector_origen"].dropna().unique().tolist())
            filtro_origen = st.selectbox("🏭 Sector Origen:", options=ops_origen, key="_mon_admin_filtro_ori")
        with col_f2:
            ops_actual    = ["Todos"] + sorted(df_unicas["sector_actual"].dropna().unique().tolist())
            filtro_actual = st.selectbox("📍 Estado Actual:", options=ops_actual, key="_mon_admin_filtro_act")

        if filtro_origen != "Todos": df_unicas = df_unicas[df_unicas["sector_origen"] == filtro_origen]
        if filtro_actual != "Todos": df_unicas = df_unicas[df_unicas["sector_actual"] == filtro_actual]

        map_opciones = {f"{r['orden_trim']}  —  🧑‍💻 {r['usuario_actual']}": r['orden_trim'] for _, r in df_unicas.iterrows()}
        opciones_orden = sorted(list(map_opciones.keys()))

        with col_f3:
            if not opciones_orden:
                st.info("No hay registros que coincidan.")
                orden_seleccionada_str = None
            else:
                orden_seleccionada_str = st.selectbox("🔎 Buscar Orden o Operario:", options=opciones_orden, key="_mon_orden_sel", index=0)

        if orden_seleccionada_str:
            orden_editar = map_opciones[orden_seleccionada_str]
            df_fila = df_prod[df_prod["orden"].astype(str).str.strip() == orden_editar].sort_values("fecha_hora", ascending=False)
            row = df_fila.iloc[0]

            fecha_ingreso = pd.to_datetime(row['fecha_hora'])
            ahora_admin   = pd.Timestamp.now()
            if fecha_ingreso.tzinfo is not None:
                ahora_admin = ahora_admin.tz_localize(fecha_ingreso.tzinfo)
            tiempo_delta    = ahora_admin - fecha_ingreso
            horas_en_sector = tiempo_delta.total_seconds() / 3600.0
            dias  = tiempo_delta.days
            horas = int(tiempo_delta.components.hours)
            mins  = int(tiempo_delta.components.minutes)
            tiempo_str = f"{dias}d {horas}h" if dias > 0 else (f"{horas}h {mins}m" if horas > 0 else f"{mins}m")

            es_demora    = row['sector'].strip().lower() == 'perforación' and horas_en_sector >= 4
            color_tiempo = "#facc15" if es_demora else "#f8fafc"
            bg_tiempo    = "#422006" if es_demora else "#0f172a"
            borde_tiempo = "border-left: 3px solid #facc15;" if es_demora else "border-left: 3px solid #ef4444;"
            aviso_demora = "<br><span style='color:#facc15; font-size:10px;'>⚠️ DEMORA DETECTADA</span>" if es_demora else ""

            st.markdown(f"""
            <div style="background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
                <h3 style="color: white; margin-top: 0; margin-bottom: 15px; font-size: 20px;">
                    Ficha: <span style="color: #60a5fa; font-weight: 800; background: #0f172a; padding: 4px 10px; border-radius: 6px;">{row['orden']}</span>
                </h3>
                <div style="display: flex; flex-wrap: wrap; gap: 12px;">
                    <div style="flex:1;min-width:120px;background:#0f172a;padding:12px;border-radius:8px;border-left:3px solid #6366f1;">
                        <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;text-transform:uppercase;font-weight:600;">Operario</p>
                        <p style="color:#f8fafc;font-size:15px;font-weight:700;margin:0;">👷 {row['usuario']}</p>
                    </div>
                    <div style="flex:1;min-width:120px;background:#0f172a;padding:12px;border-radius:8px;border-left:3px solid #14b8a6;">
                        <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;text-transform:uppercase;font-weight:600;">Sector Actual</p>
                        <p style="color:#f8fafc;font-size:15px;font-weight:700;margin:0;">📍 {row['sector']}</p>
                    </div>
                    <div style="flex:1;min-width:120px;background:{bg_tiempo};padding:12px;border-radius:8px;{borde_tiempo}">
                        <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;text-transform:uppercase;font-weight:600;">Tiempo en Sector</p>
                        <p style="color:{color_tiempo};font-size:15px;font-weight:700;margin:0;">⏳ {tiempo_str}{aviso_demora}</p>
                    </div>
                    <div style="flex:1;min-width:120px;background:#0f172a;padding:12px;border-radius:8px;border-left:3px solid #f59e0b;">
                        <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;text-transform:uppercase;font-weight:600;">Carro / Lado</p>
                        <p style="color:#f8fafc;font-size:15px;font-weight:700;margin:0;">🛒 {row['carro']} — {row['lado']}</p>
                    </div>
                    <div style="flex:1;min-width:120px;background:#0f172a;padding:12px;border-radius:8px;border-left:3px solid #8b5cf6;">
                        <p style="color:#94a3b8;font-size:11px;margin:0 0 4px;text-transform:uppercase;font-weight:600;">Fecha / Hora</p>
                        <p style="color:#f8fafc;font-size:15px;font-weight:700;margin:0;">🕒 {row['fecha_hora']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_n1, col_n2 = st.columns([1, 2])
            with col_n1:
                nuevo_num = st.text_input("🔢 Corregir Número de Orden", value=orden_editar, key="_mon_nuevo_num")
            with col_n2:
                st.markdown("<div style='font-size:14px;margin-bottom:-15px;'>📌 Cambiar Estado de Orden</div>", unsafe_allow_html=True)
                nuevo_estado = st.radio("Estado", options=["(mismo estado)", "🔴 Dañado/Roto", "🟡 Terminado", "🟢 Entregado"],
                                        horizontal=True, label_visibility="hidden", key="_mon_estado")
            st.write("")

            if st.button("💾 GUARDAR CAMBIOS", use_container_width=True, key="_mon_guardar_nuevo"):
                try:
                    from sqlalchemy import text as _text
                    orden_final = nuevo_num.strip() if nuevo_num.strip() else orden_editar
                    map_estado  = {"🔴 Dañado/Roto": "Dañado", "🟡 Terminado": "Terminado", "🟢 Entregado": "Entrega"}
                    sets   = ["orden = :nueva"]
                    params = {"nueva": orden_final, "vieja": orden_editar.strip()}
                    if nuevo_estado != "(mismo estado)":
                        sets.append("sector = :estado")
                        params["estado"] = map_estado[nuevo_estado]
                    query = f"UPDATE registros SET {', '.join(sets)} WHERE TRIM(orden) = :vieja"
                    with conn.session as s:
                        s.execute(_text(query), params)
                        s.commit()
                    st.success(f"✅ Cambios guardados en {orden_editar}.", icon="🚀")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as _e:
                    st.error(f"❌ Error al guardar: {_e}")

            st.write("")
            with st.expander(f"🗑️ Eliminar todos los registros de la orden **{orden_editar}**"):
                st.warning(f"⚠️ Borrará permanentemente todas las filas de `{orden_editar}`.")
                if st.checkbox(f"Confirmo eliminar la orden {orden_editar}", key="_mon_confirm_del"):
                    if st.button("🗑️ Eliminar orden", type="primary", key="_mon_eliminar"):
                        try:
                            from sqlalchemy import text as _text
                            with conn.session as s:
                                s.execute(_text("DELETE FROM registros WHERE TRIM(orden) = :o"), {"o": orden_editar.strip()})
                                s.commit()
                            st.success(f"✅ Orden {orden_editar} eliminada.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as _e:
                            st.error(f"❌ Error al eliminar: {_e}")


st.divider()
st.caption(f"Control de Produccion — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
