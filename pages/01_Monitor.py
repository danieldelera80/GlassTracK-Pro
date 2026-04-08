import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from sqlalchemy import text

from config import SECTORES_PRODUCCION, verificar_licencia, get_connection, verificar_estado_sistema
from config import SECTORES_ESCANEO_DIRECTO
from styles import CSS_GLOBAL, render_sb_header

st.set_page_config(
    page_title="Monitor de Producción",
    page_icon="🚀",
    layout="wide",
)

verificar_licencia()
verificar_estado_sistema()
conn = get_connection()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

# ── Alerta Titilante CSS ──────────────────────────────────────────────────────
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
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh cada 15 segundos ─────────────────────────────────────────────
st_autorefresh(interval=15_000, key="monitor_autorefresh")


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS  (ttl=0 para que auto-refresh traiga datos frescos)
# ══════════════════════════════════════════════════════════════════════════════

def cargar_datos():
    """
    Retorna:
      df_prod   : DataFrame con registros de producción (sin Entrega/Terminado)
      df_entrega: DataFrame con registros de Entrega
      df_terminado: DataFrame con registros de Terminado
      entregadas: set de órdenes que ya pasaron por Entrega
      terminadas: set de órdenes en Terminado
    """
    query = "SELECT * FROM registros ORDER BY fecha_hora DESC"
    df_total = conn.query(query, ttl=0)

    if df_total is None or df_total.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), set(), set()

    df_total["fecha_hora"] = pd.to_datetime(df_total["fecha_hora"])
    df_total["orden"] = df_total["orden"].astype(str).str.strip()

    df_entrega   = df_total[df_total["sector"] == "Entrega"].copy()
    df_terminado = df_total[df_total["sector"] == "Terminado"].copy()
    df_danado    = df_total[df_total["sector"] == "Dañado"].copy()
    df_prod      = df_total[~df_total["sector"].isin(["Entrega", "Terminado", "Dañado"])].copy()

    # MAGIA DE LA TAZABILIDAD: Cortamos el fantasma de los números reciclados viejos. 
    # Solo consideramos que una orden ESTÁ Terminada o Dañada si ese es su ÚLTIMO estado absoluto en el tiempo.
    df_estado_actual = df_total.sort_values("fecha_hora", ascending=False).drop_duplicates(subset=["orden"], keep="first")
    df_estado_actual["orden"] = df_estado_actual["orden"].astype(str).str.strip()

    entregadas: set = set(df_estado_actual[df_estado_actual["sector"] == "Entrega"]["orden"])
    terminadas: set = set(df_estado_actual[df_estado_actual["sector"] == "Terminado"]["orden"])
    danadas:    set = set(df_estado_actual[df_estado_actual["sector"] == "Dañado"]["orden"])

    return df_prod, df_entrega, df_terminado, entregadas, terminadas, danadas


def aplicar_estilos(df: pd.DataFrame, entregadas: set, terminadas: set, danadas: set):
    """
    - Fila roja    : orden dañada
    - Celda dorada : orden en Terminado (esperando entrega)
    - Celda verde  : orden entregada
    - Fila Naranja : más de 30 minutos en En viaje
    """
    if df.empty:
        return df

    col_estado = "Estado" if "Estado" in df.columns else None
    ahora = datetime.now()

    def estilo_fila(row):
        orden        = str(row.get("Orden", "")).strip()
        
        # Volvemos a leer de la memoria limpia en tiempo real
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
                    fecha_val = pd.to_datetime(fecha_val)
                if fecha_val.tzinfo is not None:
                    ahora_tz = ahora.astimezone(fecha_val.tzinfo)
                    delta = (ahora_tz - fecha_val).total_seconds()
                else:
                    delta = (ahora - fecha_val).total_seconds()
                    
                if delta > 30 * 60:  # 30 minutos
                    parpadeo = True
            except:
                pass

        if es_incidente:
            estilos = ["background-color: #7a1a1a; color: #ffaaaa; border-bottom: 2px solid #ef4444; font-weight: bold;"] * len(row)
            return estilos

        if es_urgente:
            return ['background-color: #900000; color: white; font-weight: bold;'] * len(row)

        if es_danado:
            estilos = ["background-color:#5c1010; color:#ffaaaa;"] * len(row)
            if col_estado:
                estilos[df.columns.get_loc(col_estado)] = \
                    "background-color:#7a1a1a; color:#ff8a8a; font-weight:700; text-align:center;"
            return estilos

        estilos = [""] * len(row)
        
        if parpadeo:
             estilos = ["animation: blinkOrange 1.5s infinite; font-weight:bold;"] * len(row)
             
        if col_estado:
            if es_entregado:
                estilos[df.columns.get_loc(col_estado)] = \
                    "background-color:#1a4a2e; color:#4ada75; font-weight:700; text-align:center;"
            elif es_terminado:
                estilos[df.columns.get_loc(col_estado)] = \
                    "background-color:#3a2e00; color:#f0c040; font-weight:700; text-align:center;"
        return estilos

    return df.style.apply(estilo_fila, axis=1)

# ══════════════════════════════════════════════════════════════════════════════
#  MODAL DE FICHA (Requiere Streamlit >= 1.35)
# ══════════════════════════════════════════════════════════════════════════════
from config import ADMIN_PASSWORD

@st.dialog("📋 Ficha Interactiva de Orden")
def mostrar_modal_orden(orden_actual):
    from sqlalchemy import text as _text
    query = "SELECT * FROM registros WHERE TRIM(orden) = :ord ORDER BY fecha_hora ASC"
    df_det = conn.query(query, params={"ord": orden_actual}, ttl=0)
    
    if df_det is None or df_det.empty:
        st.warning("No hay registros históricos.")
        return
        
    df_det["fecha_hora"] = pd.to_datetime(df_det["fecha_hora"])
    
    # ── Historial
    st.markdown("#### ⏳ Historial de Movimientos")
    st.dataframe(df_det[["fecha_hora", "sector", "usuario", "carro", "lado"]], use_container_width=True, hide_index=True)
    
    # ── Tiempos Estimados Simples
    t_ini = df_det.iloc[0]["fecha_hora"]
    t_fin = datetime.now()
    if df_det.iloc[-1]["sector"] in ["Entrega", "Terminado"]:
        t_fin = df_det.iloc[-1]["fecha_hora"]
        
    delta = t_fin - t_ini
    dias = delta.components.days
    horas = delta.components.hours
    st.info(f"📌 **Tiempo estimado/total en planta de esta orden:** {dias} días y {horas} horas.")
    
    st.divider()
    
    # ── Contingencia Autorizada
    st.markdown("#### 🚨 Acciones Críticas")
    st.caption("Estas acciones afectarán a la prioridad de la orden en toda la fábrica.")
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
                    st.success("🚀 Prioridad inyectada exitosamente. Se recargará monitor.")
                    st.rerun()
                else:
                    st.info("La orden ya tiene prioridad alta.")
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
                    st.success("🚨 Incidencia inyectada. Se recargará monitor.")
                    st.rerun()
                else:
                    st.info("La orden ya está reportada con incidencia.")
            elif pass_input:
                st.error("Contraseña incorrecta.")

    with c3:
        if st.button("🗑️ Eliminar", type="primary", use_container_width=True):
            if pass_input == ADMIN_PASSWORD:
                with conn.session as s:
                    s.execute(_text("DELETE FROM registros WHERE TRIM(orden) = :v"), {"v": orden_actual})
                    s.commit()
                st.success("✅ Orden borrada permanentemente. Recargando...")
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
        import os
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
                            </div>
                            <br>
                        """, unsafe_allow_html=True)
                        if st.button("🔄 Sincronizar Nube", type="primary", use_container_width=True):
                            idx_exito = 0
                            with conn.session as s:
                                for row in filas_offline:
                                    s.execute(_text("""
                                        INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                        VALUES (:f, :o, :c, :l, :u, :s)
                                    """), {
                                        "f": row["fecha_hora"], "o": row["orden"], "c": row["carro"],
                                        "l": row["lado"], "u": row["usuario"], "s": row["sector"]
                                    })
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

st.markdown("## 🚀 Monitor de Producción Industrial")

try:
    df_prod, df_entrega, df_terminado, entregadas, terminadas, danadas = cargar_datos()
except Exception as e:
    st.error(f"❌ Error al conectar con la base de datos: {e}")
    st.stop()

hoy = datetime.now().date()


# ══════════════════════════════════════════════════════════════════════════════
#  MÉTRICAS GLOBALES
# ══════════════════════════════════════════════════════════════════════════════

df_prod_hoy    = df_prod[df_prod["fecha_hora"].dt.date == hoy]       if not df_prod.empty    else pd.DataFrame()
df_entrega_hoy = df_entrega[df_entrega["fecha_hora"].dt.date == hoy] if not df_entrega.empty else pd.DataFrame()

total_hoy      = len(df_prod_hoy)
st.write(f"Órdenes encontradas: {df_prod.shape[0]}")
entregados_hoy = len(df_entrega_hoy)
sectores_hoy   = df_prod_hoy["sector"].nunique() if not df_prod_hoy.empty else 0

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'''
    <div class="glass-metric">
        <div class="glass-title">📦 Registros Hoy</div>
        <div class="glass-value">{total_hoy}</div>
    </div>
    ''', unsafe_allow_html=True)

with c2:
    st.markdown(f'''
    <div class="glass-metric">
        <div class="glass-title">✅ Entregados Hoy</div>
        <div class="glass-value green">{entregados_hoy}</div>
    </div>
    ''', unsafe_allow_html=True)

with c3:
    st.markdown(f'''
    <div class="glass-metric">
        <div class="glass-title">🏭 Sectores Activos</div>
        <div class="glass-value">{sectores_hoy}</div>
    </div>
    ''', unsafe_allow_html=True)

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
        '<div style="font-size:12px; color:#4a6a9a; padding-top:8px;">'
        '🔁 Actualización automática · últimos datos</div>',
        unsafe_allow_html=True,
    )

st.write("")

if df_prod.empty:
    st.info("📭 No hay registros de producción todavía.")
else:
    # ── Construir tabla unificada ─────────────────────────────────────────────
    df_vista = df_prod.copy()
    
    # Agrupar: Un renglón por orden mostrando el más reciente y dejando los últimos arriba
    df_vista = df_vista.sort_values("fecha_hora", ascending=False).drop_duplicates(subset=["orden"], keep="first")

    def calcular_estado(row):
        o = str(row["orden"]).strip()
        s = str(row["sector"]).strip()
        if o in danadas: return "💔 Dañado"
        if o in entregadas: return "✅ Entregado"
        if o in terminadas: return "⏳ Terminado"
        if s.startswith("En Proceso en"): return "⚙️ En Proceso"
        if s.startswith("Enviado a"): return "📥 Pendiente"
        return ""

    df_vista["Estado"] = df_vista.apply(calcular_estado, axis=1)

    df_vista = df_vista.rename(columns={
        "orden":      "Orden",
        "sector":     "Sector",
        "usuario":    "Operario",
        "carro":      "Carro",
        "lado":       "Lado",
        "fecha_hora": "Fecha / Hora",
    })

    cols_show = ["Orden", "Sector", "Operario", "Carro", "Lado", "Fecha / Hora", "Estado"]
    df_vista  = df_vista[cols_show]

    # ── Filtro de búsqueda ────────────────────────────────────────────────────
    if busqueda.strip():
        busq = busqueda.strip().lower()
        mask_orden  = df_vista["Orden"].astype(str).str.lower().str.contains(busq, regex=False, na=False)
        mask_sector = df_vista["Sector"].astype(str).str.lower().str.contains(busq, regex=False, na=False)
        mask_usr    = df_vista["Operario"].astype(str).str.lower().str.contains(busq, regex=False, na=False)
        
        df_vista = df_vista[mask_orden | mask_sector | mask_usr]
        
        if df_vista.empty:
            st.warning(f"⚠️ No se encontraron registros para la búsqueda **{busqueda}**")
        else:
            st.success(f"🔍 {len(df_vista)} registro(s) encontrado(s) para **{busqueda}**")

    # ── Leyenda ───────────────────────────────────────────────────────────────
    if not busqueda.strip():
        leg1, leg2, leg3 = st.columns(3)
        leg1.markdown(
            '<div style="background:#5c1010;color:#ff8a8a;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '💔 Dañado</div>',
            unsafe_allow_html=True,
        )
        leg2.markdown(
            '<div style="background:#3a2e00;color:#f0c040;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '⏳ Terminado — esperando entrega</div>',
            unsafe_allow_html=True,
        )
        leg3.markdown(
            '<div style="background:#1a4a2e;color:#4ada75;padding:6px 12px;'
            'border-radius:6px;font-size:12px;text-align:center;">'
            '✅ Orden entregada al cliente</div>',
            unsafe_allow_html=True,
        )
        st.write("")

    # ── Tabla con estilos + Interacción ───────────────────────────────────────
    st.markdown("<p style='font-size:14px; color:#4a6a9a;'>Puedes presionar sobre una fila para ver el botón de Detalles abajo.</p>", unsafe_allow_html=True)
    
    seleccion_evento = st.dataframe(
        aplicar_estilos(df_vista.reset_index(drop=True), entregadas, terminadas, danadas),
        use_container_width=True,
        hide_index=True,
        height=520,
        selection_mode="single-row",
        on_select="rerun"
    )

    if hasattr(seleccion_evento, "selection") and seleccion_evento.selection.rows:
        row_idx = seleccion_evento.selection.rows[0]
        orden_str = str(df_vista.reset_index(drop=True).iloc[row_idx]["Orden"]).strip()
        mostrar_modal_orden(orden_str)
            
    st.write("")

    st.caption(f"Mostrando {len(df_vista)} registros · todos los sectores de producción")


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL DE EDICIÓN ADMIN (visible solo cuando está logueado)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.get("is_admin", False) and not df_prod.empty:
    st.divider()
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); border-left: 5px solid #3b82f6; border-radius:12px;
                padding:20px; margin-bottom:16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);">
        <div style="font-size:18px; color:#60a5fa; font-weight:800; letter-spacing:1px; display:flex; align-items:center; gap:8px;">
            <span style="font-size:24px;">⚡</span> MODO ADMINISTRADOR — Edición Rápida
        </div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">
            Encuentre la orden, modifique estado o número, y guarde los cambios al instante.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Buscador Inteligente Avanzado
    st.markdown("<h4 style='color:#e2e8f0; margin-bottom: 12px; font-size: 16px;'>🔍 Filtro Avanzado de Órdenes</h4>", unsafe_allow_html=True)
    
    # Preparar el dataframe de registros unicos
    df_calc = df_prod.copy()
    df_calc["orden_trim"] = df_calc["orden"].astype(str).str.strip()
    df_calc = df_calc.sort_values("fecha_hora", ascending=True)
    
    df_origen = df_calc.groupby("orden_trim")["sector"].first().rename("sector_origen")
    df_actual = df_calc.groupby("orden_trim")["sector"].last().rename("sector_actual")
    df_usr = df_calc.groupby("orden_trim")["usuario"].last().rename("usuario_actual")
    
    df_unicas = pd.concat([df_origen, df_actual, df_usr], axis=1).reset_index()

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        ops_origen = ["Todos"] + sorted(df_unicas["sector_origen"].dropna().unique().tolist())
        filtro_origen = st.selectbox("🏭 Sector Origen:", options=ops_origen, key="_mon_admin_filtro_ori")
    with col_f2:
        ops_actual = ["Todos"] + sorted(df_unicas["sector_actual"].dropna().unique().tolist())
        filtro_actual = st.selectbox("📍 Estado Actual:", options=ops_actual, key="_mon_admin_filtro_act")

    if filtro_origen != "Todos":
        df_unicas = df_unicas[df_unicas["sector_origen"] == filtro_origen]
    if filtro_actual != "Todos":
        df_unicas = df_unicas[df_unicas["sector_actual"] == filtro_actual]

    map_opciones = {
        f"{r['orden_trim']}  —  🧑‍💻 {r['usuario_actual']}": r['orden_trim']
        for _, r in df_unicas.iterrows()
    }
    opciones_orden = sorted(list(map_opciones.keys()))

    with col_f3:
        if not opciones_orden:
            st.info("No hay registros que coincidan.")
            orden_seleccionada_str = None
        else:
            orden_seleccionada_str = st.selectbox(
                "🔎 Buscar Orden o Operario:",
                options=opciones_orden,
                key="_mon_orden_sel",
                index=0
            )

    if orden_seleccionada_str:
        orden_editar = map_opciones[orden_seleccionada_str]
        df_fila = df_prod[df_prod["orden"].astype(str).str.strip() == orden_editar].sort_values("fecha_hora", ascending=False)
        row = df_fila.iloc[0]

        # Calcular tiempo en sector actual
        import datetime as dt
        fecha_ingreso = pd.to_datetime(row['fecha_hora'])
        ahora = pd.Timestamp.now()
        if fecha_ingreso.tzinfo is not None:
            ahora = ahora.tz_localize(fecha_ingreso.tzinfo)
        
        tiempo_delta = ahora - fecha_ingreso
        horas_en_sector = tiempo_delta.total_seconds() / 3600.0
        
        dias = tiempo_delta.days
        horas = int(tiempo_delta.components.hours)
        mins = int(tiempo_delta.components.minutes)
        
        if dias > 0:
            tiempo_str = f"{dias}d {horas}h"
        elif horas > 0:
            tiempo_str = f"{horas}h {mins}m"
        else:
            tiempo_str = f"{mins}m"
            
        horas_limite = 4
        es_demora = row['sector'].strip().lower() == 'perforación' and horas_en_sector >= horas_limite
        
        color_tiempo = "#facc15" if es_demora else "#f8fafc"
        bg_tiempo = "#422006" if es_demora else "#0f172a" 
        borde_tiempo = "border-left: 3px solid #facc15;" if es_demora else "border-left: 3px solid #ef4444;"
        aviso_demora = "<br><span style='color:#facc15; font-size:10px;'>⚠️ DEMORA DETECTADA</span>" if es_demora else ""

        # 2. Ficha de Orden Exclusiva (Card)
        st.markdown(f"""
        <div style="background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h3 style="color: white; margin-top: 0; margin-bottom: 15px; font-size: 20px;">
                Ficha de Orden: <span style="color: #60a5fa; font-weight: 800; background: #0f172a; padding: 4px 10px; border-radius: 6px;">{row['orden']}</span>
            </h3>
            <div style="display: flex; flex-wrap: wrap; gap: 15px;">
                <div style="flex: 1; min-width: 120px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #6366f1;">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 600;">Operario</p>
                    <p style="color: #f8fafc; font-size: 16px; font-weight: 700; margin: 0;">👷 {row['usuario']}</p>
                </div>
                <div style="flex: 1; min-width: 120px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #14b8a6;">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 600;">Sector Actual</p>
                    <p style="color: #f8fafc; font-size: 16px; font-weight: 700; margin: 0;">📍 {row['sector']}</p>
                </div>
                <div style="flex: 1; min-width: 120px; background: {bg_tiempo}; padding: 12px; border-radius: 8px; {borde_tiempo}">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 600;">Tiempo en Sector</p>
                    <p style="color: {color_tiempo}; font-size: 16px; font-weight: 700; margin: 0;">⏳ {tiempo_str} {aviso_demora}</p>
                </div>
                <div style="flex: 1; min-width: 120px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #f59e0b;">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 600;">Carro / Lado</p>
                    <p style="color: #f8fafc; font-size: 16px; font-weight: 700; margin: 0;">🛒 {row['carro']} - {row['lado']}</p>
                </div>
                <div style="flex: 1; min-width: 120px; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid #8b5cf6;">
                    <p style="color: #94a3b8; font-size: 11px; margin: 0 0 5px 0; text-transform: uppercase; font-weight: 600;">Fecha / Hora</p>
                    <p style="color: #f8fafc; font-size: 16px; font-weight: 700; margin: 0;">🕒 {row['fecha_hora']}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3. Acciones y Modificaciones (Botones coloridos usando radio de Streamlit como selector)
        st.markdown("<h4 style='color:#e2e8f0; margin-bottom: 10px; font-size: 16px;'>🛠️ Realizar Cambios Rápidos</h4>", unsafe_allow_html=True)
        
        col_n1, col_n2 = st.columns([1, 2])
        with col_n1:
            nuevo_num = st.text_input(
                "🔢 Corregir Número de Orden",
                value=orden_editar,
                key="_mon_nuevo_num",
            )
        with col_n2:
            st.markdown("<div style='font-size: 14px; margin-bottom: -15px;'>📌 Cambiar Estado de Orden</div>", unsafe_allow_html=True)
            # Se aprovecha horizontal radio que se comporta similar a toggle buttons rápidos
            nuevo_estado = st.radio(
                "Estado",
                options=["(mismo estado)", "🔴 Dañado/Roto", "🟡 Terminado", "🟢 Entregado"],
                horizontal=True,
                label_visibility="hidden",
                key="_mon_estado",
            )

        st.write("")
        
        # 4. Confirmación - BOTÓN GIGANTE
        # Agregamos estilos CSS para hacer el botón gigante y llamativo sin afectar el resto.
        # Al insertar este estilo, afectará a este botón en particular asumiendo uso de st.button("💾 GUARDAR CAMBIOS")
        st.markdown("""
            <style>
                div[data-testid="stButton"] button:has(div p:contains("💾 GUARDAR CAMBIOS")) {
                    background: linear-gradient(90deg, #1d4ed8, #2563eb) !important;
                    color: #ffffff !important;
                    border: none !important;
                    padding: 1rem !important;
                    font-size: 24px !important;
                    border-radius: 12px !important;
                    height: auto !important;
                }
                div[data-testid="stButton"] button:has(div p:contains("💾 GUARDAR CAMBIOS")):hover {
                    transform: scale(1.02);
                    box-shadow: 0 0 15px rgba(37,99,235,0.6) !important;
                }
            </style>
        """, unsafe_allow_html=True)

        guardar = st.button("💾 GUARDAR CAMBIOS", use_container_width=True, key="_mon_guardar_nuevo")

        if guardar:
            try:
                from sqlalchemy import text as _text
                orden_final = nuevo_num.strip() if nuevo_num.strip() else orden_editar
                
                map_estado = {
                    "🔴 Dañado/Roto": "Dañado",
                    "🟡 Terminado": "Terminado",
                    "🟢 Entregado": "Entrega"
                }

                sets = ["orden = :nueva"]
                params = {"nueva": orden_final, "vieja": orden_editar.strip()}
                
                if nuevo_estado != "(mismo estado)":
                    sets.append("sector = :estado")
                    params["estado"] = map_estado[nuevo_estado]

                query = f"UPDATE registros SET {', '.join(sets)} WHERE TRIM(orden) = :vieja"

                with conn.session as s:
                    s.execute(_text(query), params)
                    s.commit()

                msg_exito = f"<div style='font-size:24px; text-align:center; padding: 20px;'>✅ ¡CAMBIOS GUARDADOS CON ÉXITO!<br><b>{orden_editar}</b> se actualizó correctamente.</div>"
                st.success(msg_exito, icon="🚀")
                st.cache_data.clear()
                st.rerun()
            except Exception as _e:
                st.error(f"❌ Error al guardar: {_e}")

        # ── Eliminar orden ──────────────────────────────────────────────────
        st.write("")
        with st.expander(f"🗑️ Eliminar todos los registros de la orden **{orden_editar}**"):
            st.warning(f"⚠️ Esto borrará **permanentemente** todas las filas de la orden `{orden_editar}` en todos los sectores. No se puede deshacer.")
            confirmar_eliminar = st.checkbox(
                f"Confirmo que quiero eliminar la orden {orden_editar}",
                key="_mon_confirm_del",
            )
            if st.button("🗑️ Eliminar orden", type="primary",
                         disabled=not confirmar_eliminar, key="_mon_eliminar"):
                try:
                    from sqlalchemy import text as _text
                    with conn.session as s:
                        s.execute(
                            _text("DELETE FROM registros WHERE TRIM(orden) = :o"),
                            {"o": orden_editar.strip()},
                        )
                        s.commit()
                    st.success(f"✅ Orden **{orden_editar}** eliminada correctamente.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as _e:
                    st.error(f"❌ Error al eliminar: {_e}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN ENTREGAS
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("### 📦 Registro de Entregas")

if df_entrega.empty:
    st.info("📭 No se registró ninguna entrega todavía.")
else:
    col_e1, col_e2 = st.columns(2)
    col_e1.metric("Entregas Hoy",        len(df_entrega_hoy))
    col_e2.metric("Entregas Históricas",  len(df_entrega))

    st.write("")

    df_ent_show = df_entrega[["orden", "usuario", "fecha_hora"]].rename(columns={
        "orden":      "Orden",
        "usuario":    "Operario",
        "fecha_hora": "Fecha / Hora",
    })

    if busqueda.strip():
        df_ent_show = df_ent_show[
            df_ent_show["Orden"].astype(str).str.contains(busqueda.strip(), case=False, na=False)
        ]

    st.dataframe(df_ent_show, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO DE DIRECCIÓN: RENDIMIENTO OPERATIVO
# ══════════════════════════════════════════════════════════════════════════════

if not df_prod_hoy.empty:
    st.divider()
    fecha_format = hoy.strftime("%d/%m/%Y")
    st.markdown(f"### 🎯 Rendimiento Operativo — {fecha_format}")

    # 1. Preparar métricas administrativas
    conteo = df_prod_hoy["usuario"].value_counts().reset_index()
    conteo.columns = ["Operario", "Total Vidrios"]
    
    ultimos_movs = df_prod_hoy.groupby("usuario")["fecha_hora"].max().reset_index()
    ultimos_movs.columns = ["Operario", "Último Movimiento"]
    ultimos_movs["Último Movimiento"] = ultimos_movs["Último Movimiento"].dt.strftime("%H:%M:%S")

    df_rendimiento = pd.merge(conteo, ultimos_movs, on="Operario")
    
    # Orden ascendente en Plotly para que el mayor quede arriba en barra horizontal
    df_grafico = df_rendimiento.sort_values(by="Total Vidrios", ascending=True)

    # 2. Gráfico Ejecutivo (Barra Horizontal, Color Corporativo, Flotante)
    fig = px.bar(
        df_grafico, 
        x="Total Vidrios", 
        y="Operario",
        orientation='h',
        text_auto=True, 
        template="plotly_dark",
        color_discrete_sequence=["#3b82f6"] # Azul tecnológico corporativo
    )
    fig.update_layout(
        showlegend=False, 
        margin=dict(t=20, b=20, l=10, r=20),
        xaxis_title=None,
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. Tabla Analítica de Apoyo
    st.markdown("#### 📑 Reporte de Actividad del Turno")
    df_tabla = df_rendimiento.sort_values(by="Total Vidrios", ascending=False).reset_index(drop=True)
    df_tabla.index = df_tabla.index + 1  # Enumerar desde 1
    st.table(df_tabla)

st.divider()
st.caption(f"Sistema de Monitoreo — Camara Fabrica Produccion · {datetime.now().strftime('%d/%m/%Y %H:%M')}")