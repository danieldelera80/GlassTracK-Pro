import re
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import csv
from pathlib import Path

from config import SECTORES, SECTORES_ESCANEO_DIRECTO, verificar_licencia, get_connection, verificar_estado_sistema
from styles import CSS_GLOBAL, render_sb_header, render_sb_operario, render_steps

st.set_page_config(page_title="Carga de Producción", page_icon="📋", layout="centered")

verificar_licencia()
verificar_estado_sistema()
conn = get_connection()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

# CSS extra para grilla de sectores y botones de kanban
st.markdown("""
<style>
/* Grilla de sector — botones grandes para tablet */
div[data-testid="stHorizontalBlock"] .stButton > button {
    min-height: 62px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}
/* Badge contador kanban */
.kanban-header {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 10px;
}
.kanban-count {
    background: #1e3a8a; color: #bfdbfe;
    font-size: 13px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px;
    min-width: 28px; text-align: center;
}
.kanban-count.orange { background: #7c2d12; color: #fed7aa; }
/* Historial mini */
.hist-row {
    display: flex; gap: 10px; align-items: center;
    font-size: 12px; color: #64748b;
    padding: 4px 0; border-bottom: 0.5px solid rgba(148,163,184,0.1);
}
.hist-orden { font-weight: 600; color: #94a3b8; }
.hist-check { color: #34d399; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_DISPONIBLE = True
except ImportError:
    PYZBAR_DISPONIBLE = False

CAMARA_DISPONIBLE = True
SECTOR_ENTREGA   = "Entrega"
SECTOR_TERMINADO = "Terminado"
_ARG_TZ = timezone(timedelta(hours=-3))
_PFX_RE = re.compile(r'^\s*\[(URGENTE|INCIDENCIA)\]\s*', re.IGNORECASE)


def _now_utc():
    return datetime.now(timezone.utc)

def _hora_arg():
    return datetime.now(_ARG_TZ).strftime("%H:%M:%S")


# ══════════════════════════════════════════════════════════════════════════════
#  NORMALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def _normalizar_df_ordenes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["orden"] = df["orden"].astype(str).str.strip()
    df["_base"] = df["orden"].apply(lambda x: _PFX_RE.sub("", x).strip())
    bases_urg = set(df.loc[df["orden"].str.contains(r'\[URGENTE\]',    case=False, na=False), "_base"])
    bases_inc = set(df.loc[df["orden"].str.contains(r'\[INCIDENCIA\]', case=False, na=False), "_base"]) - bases_urg

    def _norm(row):
        b = row["_base"]
        if b in bases_urg: return f"[URGENTE] {b}"
        if b in bases_inc: return f"[INCIDENCIA] {b}"
        return b

    df["orden"] = df.apply(_norm, axis=1)
    df = (df.sort_values("fecha_hora", ascending=False)
            .drop_duplicates(subset=["orden"], keep="first"))
    return df.drop(columns=["_base"])


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

OFFLINE_FILE = Path(__file__).parent.parent / "offline_records.csv"


def guardar_registro_offline(orden, carro, lado, usuario, sector):
    file_exists = OFFLINE_FILE.exists()
    try:
        with open(OFFLINE_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["fecha_hora", "orden", "carro", "lado", "usuario", "sector"])
            writer.writerow([_now_utc().isoformat(), orden.strip(), carro, lado, usuario.strip(), sector])
        return True
    except Exception as e:
        print(f"Error offline: {e}")
        return False


def guardar_registro(orden, carro, lado, usuario, sector):
    import time
    for intento in range(3):
        try:
            with conn.session as s:
                s.execute(text("""
                    INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                    VALUES (:f, :o, :c, :l, :u, :s)
                """), {"f": _now_utc(), "o": orden.strip(), "c": carro,
                       "l": lado, "u": usuario.strip(), "s": sector})
                s.commit()
            return True, None
        except Exception as e:
            if intento < 2:
                time.sleep(2)
            else:
                if guardar_registro_offline(orden, carro, lado, usuario, sector):
                    return True, "OFFLINE"
                return False, str(e)


def obtener_activos(sector_actual):
    try:
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros ORDER BY fecha_hora DESC"
        with conn.session as s:
            df = pd.read_sql(text(query), s.connection())
        if df.empty:
            return [], []
        df = _normalizar_df_ordenes(df)
        def fmt(d):
            d = d.copy()
            d["fecha_hora"] = pd.to_datetime(d["fecha_hora"], utc=True)\
                .dt.tz_convert("America/Argentina/Buenos_Aires").dt.strftime("%H:%M")
            return d.to_dict("records")
        return (
            fmt(df[df["sector"].str.strip() == f"Enviado a {sector_actual}"]),
            fmt(df[df["sector"].str.strip() == f"En Proceso en {sector_actual}"])
        )
    except Exception as e:
        print(f"Error obtener_activos: {e}")
        return [], []


def obtener_pendientes_entrega():
    try:
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros ORDER BY fecha_hora DESC"
        with conn.session as s:
            df = pd.read_sql(text(query), s.connection())
        if df.empty:
            return []
        df = _normalizar_df_ordenes(df)
        mask = (df["sector"].str.strip() == SECTOR_TERMINADO) | \
               (df["sector"].str.strip() == f"Enviado a {SECTOR_ENTREGA}")
        res = df[mask].copy()
        res["fecha_hora"] = pd.to_datetime(res["fecha_hora"], utc=True)\
            .dt.tz_convert("America/Argentina/Buenos_Aires").dt.strftime("%H:%M")
        return res.to_dict("records")
    except Exception as e:
        print(f"Error pendientes_entrega: {e}")
        return []


def resolver_nombre_orden(orden_base):
    try:
        base = _PFX_RE.sub("", orden_base).strip()
        df = conn.query(
            "SELECT DISTINCT orden FROM registros "
            "WHERE TRIM(orden) = :base OR TRIM(orden) ILIKE :urg OR TRIM(orden) ILIKE :inc "
            "   OR TRIM(orden) LIKE :base_sub OR TRIM(orden) ILIKE :urg_sub OR TRIM(orden) ILIKE :inc_sub",
            params={"base": base, "urg": f"[URGENTE] {base}", "inc": f"[INCIDENCIA] {base}",
                    "base_sub": f"{base} - %", "urg_sub": f"[URGENTE] {base} - %", "inc_sub": f"[INCIDENCIA] {base} - %"},
            ttl=0
        )
        if df.empty:
            return orden_base
        ordenes = [str(o).strip() for o in df["orden"].values]
        for o in ordenes:
            if "[URGENTE]" in o.upper() and " - " not in o:   return o
        for o in ordenes:
            if "[INCIDENCIA]" in o.upper() and " - " not in o: return o
        return f"{base} - {len(df) + 1}"
    except Exception as e:
        print(f"Error resolver_nombre_orden: {e}")
        return orden_base


def obtener_carro_lado(orden):
    try:
        base = _PFX_RE.sub("", orden).strip()
        df = conn.query(
            "SELECT carro, lado FROM registros "
            "WHERE TRIM(orden) = :base OR TRIM(orden) ILIKE :urg OR TRIM(orden) ILIKE :inc "
            "ORDER BY fecha_hora DESC LIMIT 1",
            params={"base": base, "urg": f"[URGENTE] {base}", "inc": f"[INCIDENCIA] {base}"},
            ttl=0
        )
        if not df.empty:
            return int(df.iloc[0]["carro"] or 0), str(df.iloc[0]["lado"] or "A")
    except:
        pass
    return 0, "A"


def decodificar_imagen(img_bytes):
    if not PYZBAR_DISPONIBLE:
        return None
    try:
        from PIL import Image as PILImage
        img     = PILImage.open(img_bytes)
        codigos = zbar_decode(img)
        return codigos[0].data.decode("utf-8").strip() if codigos else None
    except:
        return None


def pieza_en_proceso(orden, sector):
    """Verifica si la orden ya fue tomada (En Proceso en) en este sector."""
    try:
        res = conn.query(
            "SELECT sector FROM registros WHERE TRIM(orden) = :ord ORDER BY fecha_hora DESC LIMIT 1",
            params={"ord": orden.strip()}, ttl=0
        )
        if not res.empty:
            return res.iloc[0]["sector"].strip() == f"En Proceso en {sector}"
    except:
        pass
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE — con persistencia via query_params
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULTS = {
    "paso":              0,
    "op_confirmado":     "",
    "sector_confirmado": SECTORES[0],
    "orden_val":         "",
    "ord_n":             0,
    "reg_error":         None,
    "ultimo":            None,
    "modo_camara":       False,
    "entrega_lista":     False,
    "carro_previo":      0,
    "lado_previo":       "A",
    "paso3_fresh":       False,
    "historial":         [],   # últimos 3 escaneos de la sesión
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Persistencia: recuperar operario y sector del URL ────────────────────────
if not st.session_state.op_confirmado:
    _op_url     = st.query_params.get("op", "")
    _sector_url = st.query_params.get("sector", "")
    if _op_url:
        st.session_state.op_confirmado     = _op_url
        st.session_state.sector_confirmado = _sector_url if _sector_url in SECTORES else SECTORES[0]
        st.session_state.paso              = 2  # saltar directo al escaneo


def confirmar_operario():
    val = st.session_state.get("_inp_op", "").strip()
    if val:
        st.session_state.op_confirmado = val
        st.session_state.paso          = 1
        st.query_params["op"]     = val
        st.query_params["sector"] = st.session_state.sector_confirmado


def confirmar_sector(sector):
    st.session_state.sector_confirmado = sector
    st.session_state.paso              = 2
    st.query_params["sector"]     = sector


def procesar_orden(valor):
    if not valor.strip():
        return
    orden_resuelta                    = resolver_nombre_orden(valor.strip())
    st.session_state.orden_val        = orden_resuelta
    carro_p, lado_p                   = obtener_carro_lado(orden_resuelta)
    st.session_state.carro_previo     = carro_p
    st.session_state.lado_previo      = lado_p
    st.session_state.paso3_fresh      = True
    if st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO:
        st.session_state.entrega_lista = True
    else:
        st.session_state.paso = 3


def cb_orden():
    val = st.session_state.get(f"_inp_ord_{st.session_state.ord_n}", "").strip()
    procesar_orden(val)


def agregar_historial(orden, sector, enviado_a=None):
    entry = {
        "orden":     orden,
        "sector":    sector,
        "enviado_a": enviado_a,
        "hora":      _hora_arg(),
    }
    st.session_state.historial.insert(0, entry)
    st.session_state.historial = st.session_state.historial[:5]


def get_step_labels():
    if st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO:
        return ["Operario", "Sector", "Escanear"]
    return ["Operario", "Sector", "Escanear", "Confirmar"]


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    render_sb_header()
    if st.session_state.op_confirmado:
        render_sb_operario(st.session_state.op_confirmado, st.session_state.sector_confirmado)
        if st.button("🔄 Cambiar operario", use_container_width=True):
            for k in ["op_confirmado", "orden_val", "historial"]:
                st.session_state[k] = _DEFAULTS[k]
            st.session_state.paso = 0
            st.session_state.entrega_lista = False
            st.query_params.clear()
            st.rerun()
    else:
        st.caption("Iniciá sesión para comenzar.")
    st.divider()
    if st.button("🏠 Inicio", use_container_width=True):
        st.switch_page("main.py")


# ══════════════════════════════════════════════════════════════════════════════
#  WIZARD
# ══════════════════════════════════════════════════════════════════════════════

es_escaneo_directo = st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO
es_entrega         = st.session_state.sector_confirmado == SECTOR_ENTREGA
es_terminado       = st.session_state.sector_confirmado == SECTOR_TERMINADO

render_steps(st.session_state.paso, get_step_labels())

# ── Alerta urgente por sector ─────────────────────────────────────────────────
if st.session_state.paso >= 2:
    try:
        _sector_op = st.session_state.sector_confirmado
        _vis = {_sector_op, f"En Proceso en {_sector_op}", f"Enviado a {_sector_op}"}
        _df_urg = conn.query(
            "SELECT DISTINCT ON (orden) orden, sector FROM registros "
            "WHERE orden ILIKE '%[URGENTE]%' ORDER BY orden, fecha_hora DESC", ttl=30
        )
        if _df_urg is not None and not _df_urg.empty:
            for _, _r in _df_urg[_df_urg["sector"].str.strip().isin(_vis)].iterrows():
                st.markdown(f"""
                <div class="alerta-urgente">
                    <span style="font-size:26px;">🚨</span>
                    <div>
                        <div class="alerta-urgente-titulo">⚡ Urgente activa</div>
                        <div class="alerta-urgente-ordenes">{_r['orden']}</div>
                        <div style="font-size:12px;color:#fca5a5;margin-top:3px;">📍 {_r['sector'].strip()}</div>
                    </div>
                </div>""", unsafe_allow_html=True)
    except:
        pass

paso = st.session_state.paso

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 0 — Operario
# ─────────────────────────────────────────────────────────────────────────────
if paso == 0:
    st.markdown("### 👷 ¿Quién sos?")
    st.text_input(
        "Nombre o ID", key="_inp_op", on_change=confirmar_operario,
        placeholder="Escribí tu nombre o escaneá tu ID...",
    )
    st.caption("Presioná Enter o usá el escáner.")
    st.write("")
    if st.button("Confirmar →", use_container_width=True, type="primary"):
        confirmar_operario()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 1 — Sector (GRILLA DE BOTONES GRANDES)
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 1:
    st.markdown("### 📍 ¿En qué sector estás?")
    st.markdown(f"<p style='font-size:13px;color:#4a6a9a;margin-bottom:16px;'>Operario: <b>{st.session_state.op_confirmado}</b></p>", unsafe_allow_html=True)

    # Grilla 2 columnas de botones grandes — mucho mejor para tablet
    for i in range(0, len(SECTORES), 2):
        col_a, col_b = st.columns(2)
        with col_a:
            sec_a = SECTORES[i]
            es_sel_a = (sec_a == st.session_state.sector_confirmado)
            if st.button(
                f"{'✓ ' if es_sel_a else ''}{sec_a}",
                use_container_width=True,
                type="primary" if es_sel_a else "secondary",
                key=f"sec_{i}"
            ):
                confirmar_sector(sec_a)
                st.rerun()
        if i + 1 < len(SECTORES):
            with col_b:
                sec_b = SECTORES[i + 1]
                es_sel_b = (sec_b == st.session_state.sector_confirmado)
                if st.button(
                    f"{'✓ ' if es_sel_b else ''}{sec_b}",
                    use_container_width=True,
                    type="primary" if es_sel_b else "secondary",
                    key=f"sec_{i+1}"
                ):
                    confirmar_sector(sec_b)
                    st.rerun()

    st.write("")
    if st.button("← Volver", use_container_width=True):
        st.session_state.paso = 0
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 2 — Escanear orden
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 2:
    # Barra de contexto compacta
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;background:#0d1f3c;
                border-radius:10px;padding:10px 14px;margin-bottom:16px;">
        <div style="font-size:22px;">👷</div>
        <div>
            <div style="font-size:14px;font-weight:700;color:#e0e8f5;">{st.session_state.op_confirmado}</div>
            <div style="font-size:12px;color:#4a6a9a;">📍 {st.session_state.sector_confirmado}</div>
        </div>
        <div style="margin-left:auto;font-size:11px;color:#2a4a6a;cursor:pointer;"
             onclick="window.location.href='?'">cambiar</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-guardar Entrega / Terminado ──────────────────────────────────────
    if st.session_state.entrega_lista:
        st.session_state.entrega_lista = False
        ok, err = guardar_registro(
            st.session_state.orden_val, 0, "-",
            st.session_state.op_confirmado, st.session_state.sector_confirmado,
        )
        if ok:
            agregar_historial(st.session_state.orden_val, st.session_state.sector_confirmado)
            st.session_state.ultimo    = {"orden": st.session_state.orden_val,
                                           "sector": st.session_state.sector_confirmado,
                                           "op": st.session_state.op_confirmado,
                                           "offline": err == "OFFLINE"}
            st.session_state.orden_val = ""
            st.session_state.ord_n    += 1
            st.session_state.reg_error = None
            st.rerun()
        else:
            st.session_state.reg_error = err

    # ── Título según sector ───────────────────────────────────────────────────
    if es_terminado:
        st.markdown("### ⏳ Escaneá la orden terminada")
        st.markdown('<div style="background:#1a1500;border:1px solid #7a6000;border-radius:10px;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#f0c040;">Modo Terminado — queda en espera de entrega al cliente</div>', unsafe_allow_html=True)
    elif es_entrega:
        st.markdown("### 📦 Escaneá la orden a entregar")
        st.markdown('<div style="background:#0d2a1a;border:1px solid #1a6a35;border-radius:10px;padding:8px 14px;margin-bottom:12px;font-size:13px;color:#4ada75;">Modo Entrega — se registra automáticamente al escanear</div>', unsafe_allow_html=True)
    else:
        st.markdown("### 🔢 Escaneá la orden")

    # ── INPUT PRINCIPAL: escaner/teclado por defecto ──────────────────────────
    if not st.session_state.modo_camara:
        ord_key = f"_inp_ord_{st.session_state.ord_n}"
        st.text_input(
            "Número de Orden", key=ord_key, on_change=cb_orden,
            placeholder="Apuntá el escáner acá o escribí el número...",
        )
        # Camara como opcion secundaria discreta
        if CAMARA_DISPONIBLE:
            if st.button("📷 Usar cámara en cambio", key="btn_usar_cam",
                         use_container_width=False):
                st.session_state.modo_camara = True
                st.session_state.ord_n += 1
                st.rerun()
    else:
        # ── MODO CÁMARA ───────────────────────────────────────────────────────
        st.caption("📸 Sacá foto a la etiqueta.")
        foto = st.camera_input("Capturar", key=f"_cam_{st.session_state.ord_n}", label_visibility="collapsed")
        if foto is not None:
            codigo_auto = decodificar_imagen(foto)
            if codigo_auto:
                st.success(f"✅ Código detectado: **{codigo_auto}**")
                procesar_orden(codigo_auto)
                st.session_state.ord_n += 1
                st.rerun()
            else:
                st.markdown('<div style="font-size:13px;color:#f0c040;margin-bottom:6px;">👀 Ingresá el número de la etiqueta:</div>', unsafe_allow_html=True)
                cod_manual = st.text_input("Código", key=f"_cam_manual_{st.session_state.ord_n}",
                                           placeholder="Ej: 65365-3", label_visibility="collapsed")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", use_container_width=True, type="primary", key=f"_cam_ok_{st.session_state.ord_n}"):
                        if cod_manual.strip():
                            procesar_orden(cod_manual.strip())
                            st.session_state.ord_n += 1
                            st.rerun()
                        else:
                            st.warning("Ingresá el código.")
                with c2:
                    if st.button("🔄 Otra foto", use_container_width=True, key=f"_cam_retry_{st.session_state.ord_n}"):
                        st.session_state.ord_n += 1
                        st.rerun()

        if st.button("⌨️ Volver al escáner / teclado", key="btn_volver_scan"):
            st.session_state.modo_camara = False
            st.session_state.ord_n += 1
            st.rerun()

    st.write("")
    if st.button("← Cambiar sector", use_container_width=True):
        st.session_state.paso = 1
        st.rerun()

    # ── Error de guardado ─────────────────────────────────────────────────────
    if st.session_state.reg_error:
        st.error(f"❌ Error al guardar: {st.session_state.reg_error}")

    # ── Panel de éxito ────────────────────────────────────────────────────────
    if st.session_state.ultimo:
        u = st.session_state.ultimo
        if u["sector"] == SECTOR_ENTREGA:
            icono, titulo = "📦", "¡Entregado!"
        elif u["sector"] == SECTOR_TERMINADO:
            icono, titulo = "⏳", "¡Terminado!"
        else:
            icono, titulo = "✅", "¡Registrado!"

        extra = ""
        if u.get("enviado_a"):
            if u["enviado_a"] == "Dañado":
                extra = '<div style="font-size:13px;color:#ff8a8a;margin-top:6px;">⚠️ Marcado como Dañado</div>'
            elif u["enviado_a"] == SECTOR_TERMINADO:
                extra = '<div style="font-size:13px;color:#f0c040;margin-top:8px;">⏳ Enviado a Terminado</div>'
            else:
                extra = f'<div style="font-size:13px;color:#4ade80;margin-top:8px;">📤 Enviado a: {u["enviado_a"]}</div>'
        if u.get("offline"):
            extra += '<div style="font-size:13px;font-weight:bold;color:#f97316;margin-top:8px;border:1px solid #f97316;padding:5px 8px;border-radius:6px;text-align:center;">⚠️ Guardado en Caché Local</div>'

        st.markdown(f"""
        <div class="success-panel">
            <div style="font-size:40px;">{icono}</div>
            <div style="font-size:18px;font-weight:800;margin:6px 0;">{titulo}</div>
            <div style="font-size:14px;opacity:.85;">Orden <b>{u['orden']}</b> · {u['sector']}</div>
            {extra}
        </div>""", unsafe_allow_html=True)

        # Beep
        beep_path = Path(__file__).parent.parent / "beep.wav"
        if beep_path.exists():
            import base64
            with open(beep_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay style="display:none"><source src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>', unsafe_allow_html=True)

        # ── Mini-historial de últimos escaneos ────────────────────────────────
        hist_prev = [h for h in st.session_state.historial
                     if h["orden"] != u["orden"] or h == st.session_state.historial[-1]][:3]
        if len(st.session_state.historial) > 1:
            st.markdown("<div style='margin-top:10px;'>", unsafe_allow_html=True)
            st.caption("Últimos de esta sesión:")
            for h in st.session_state.historial[1:4]:
                destino = f" → {h['enviado_a']}" if h.get("enviado_a") else ""
                st.markdown(f"""
                <div class="hist-row">
                    <span class="hist-check">✓</span>
                    <span class="hist-orden">{h['orden']}</span>
                    <span style="font-size:11px;color:#475569;">{h['sector']}{destino}</span>
                    <span style="margin-left:auto;font-size:11px;color:#334155;">{h['hora']}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ── KANBAN DE PRODUCCIÓN ──────────────────────────────────────────────────
    st.markdown("<hr style='margin:24px 0 16px;border:1px dashed #334155;'>", unsafe_allow_html=True)

    if not es_terminado and not es_entrega:
        entrantes, en_proceso = obtener_activos(st.session_state.sector_confirmado)

        # PENDIENTES — expander con contador
        with st.expander(
            f"📥 PENDIENTES DE RECIBIR  ·  {len(entrantes)} orden{'es' if len(entrantes) != 1 else ''}",
            expanded=len(entrantes) > 0
        ):
            if not entrantes:
                st.info("No hay órdenes entrantes en este momento.")
            else:
                for row in entrantes:
                    _urg = "[URGENTE]" in str(row['orden']).upper()
                    _bg  = "#2d0a0a" if _urg else "#1e293b"
                    _brd = "#ef4444" if _urg else "#3b82f6"
                    _badge = ' <span style="background:#ef4444;color:#fff;font-size:11px;padding:1px 6px;border-radius:4px;font-weight:bold;margin-left:6px;">URGENTE</span>' if _urg else ""
                    st.markdown(f"""
                    <div style="background:{_bg};border-left:4px solid {_brd};border-radius:6px;padding:10px 12px;margin-bottom:8px;">
                        <div style="font-size:17px;font-weight:bold;color:#60a5fa;">📄 {row['orden']}{_badge}</div>
                        <div style="font-size:12px;color:#94a3b8;margin-top:4px;">
                            🛒 Carro {row['carro']} · Lado {row['lado']} · {row['usuario']} · {row['fecha_hora']}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"↘️ TOMAR — {row['orden']}", key=f"rec_{row['orden']}", use_container_width=True):
                        ok, err = guardar_registro(
                            row['orden'], row.get('carro', 0), row.get('lado', '-'),
                            st.session_state.op_confirmado,
                            f"En Proceso en {st.session_state.sector_confirmado}"
                        )
                        if ok:
                            agregar_historial(row['orden'], f"En Proceso en {st.session_state.sector_confirmado}")
                            st.session_state.ultimo = {
                                "orden": row['orden'],
                                "sector": f"En Proceso en {st.session_state.sector_confirmado}",
                                "op": st.session_state.op_confirmado,
                                "offline": err == "OFFLINE"
                            }
                            st.session_state.ord_n += 1
                            st.rerun()
                        else:
                            st.error(err)

        st.write("")

        # EN PROCESO — expander con contador
        with st.expander(
            f"⚙️ EN PROCESO EN MI MESA  ·  {len(en_proceso)} pieza{'s' if len(en_proceso) != 1 else ''}",
            expanded=len(en_proceso) > 0
        ):
            if not en_proceso:
                st.info("No tenés piezas en tu mesa actualmente.")
            else:
                for row in en_proceso:
                    _urg = "[URGENTE]" in str(row['orden']).upper()
                    _bg  = "#2d0a0a" if _urg else "#1f1605"
                    _brd = "#ef4444" if _urg else "#eab308"
                    _badge = ' <span style="background:#ef4444;color:#fff;font-size:11px;padding:1px 6px;border-radius:4px;font-weight:bold;margin-left:6px;">URGENTE</span>' if _urg else ""
                    st.markdown(f"""
                    <div style="background:{_bg};border-left:4px solid {_brd};border-radius:6px;padding:10px 12px;margin-bottom:8px;">
                        <div style="font-size:17px;font-weight:bold;color:#facc15;">⚙️ {row['orden']}{_badge}</div>
                        <div style="font-size:12px;color:#a1a1aa;margin-top:4px;">
                            🛒 Carro {row['carro']} · Lado {row['lado']} · desde las {row['fecha_hora']}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"📤 DESPACHAR — {row['orden']}", key=f"fin_{row['orden']}", use_container_width=True):
                        st.session_state.orden_val    = row['orden']
                        st.session_state.carro_previo = int(row.get('carro') or 0)
                        st.session_state.lado_previo  = str(row.get('lado') or 'A')
                        st.session_state.paso3_fresh  = True
                        st.session_state.paso         = 4  # despachar directo
                        st.rerun()

    # ── KANBAN ENTREGA ────────────────────────────────────────────────────────
    if es_entrega:
        pendientes = obtener_pendientes_entrega()
        with st.expander(
            f"📥 LISTAS PARA ENTREGAR  ·  {len(pendientes)} orden{'es' if len(pendientes) != 1 else ''}",
            expanded=len(pendientes) > 0
        ):
            if not pendientes:
                st.info("No hay productos terminados esperando entrega.")
            else:
                for row in pendientes:
                    col_info, col_btn = st.columns([7, 3])
                    with col_info:
                        st.markdown(f"""
                        <div style="background:#0d2a1a;border-left:4px solid #4ada75;border-radius:6px;
                                    padding:8px 10px;display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-size:15px;font-weight:bold;color:#4ada75;">📦 {row['orden']}</span>
                            <span style="font-size:11px;color:#86efac;">🛒 {row['carro']} · {row['lado']} · {row['fecha_hora']}</span>
                        </div>""", unsafe_allow_html=True)
                    with col_btn:
                        if st.button("🚀 ENTREGAR", key=f"ent_{row['orden']}", use_container_width=True):
                            st.session_state.orden_val     = row['orden']
                            st.session_state.entrega_lista = True
                            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  PASO 3 — SOLO TOMAR PIEZA (escaneo manual → nueva pieza)
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 3:
    _orden    = st.session_state.orden_val
    _cp       = st.session_state.carro_previo
    _lp       = st.session_state.lado_previo
    _LADOS    = ["A", "B", "Ambos"]

    st.markdown(f"""
    <div style="background:#0d1f3c;border:1px solid #1e3a6a;border-radius:12px;
                padding:12px 16px;margin-bottom:16px;text-align:center;">
        <div style="font-size:11px;color:#4a6a9a;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px;">
            Orden detectada
        </div>
        <div style="font-size:26px;font-weight:900;color:#4a90d9;letter-spacing:2px;">{_orden}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## ↘️ Iniciar trabajo en este sector")
    st.caption(f"Sector: **{st.session_state.sector_confirmado}**")
    st.write("")

    if st.session_state.sector_confirmado == "Optimización":
        # ── BLOQUE EXCLUSIVO OPTIMIZACIÓN ────────────────────────────────────
        es_error = st.checkbox("Es orden de error", key="_t_es_error")

        if not es_error:
            col_c, col_l = st.columns(2)
            with col_c:
                st.markdown("**🛒 Carro**")
                carro_str = st.text_input("Carro", key="_t_carro", placeholder="Número...", label_visibility="collapsed")
                carro_ok  = carro_str.strip().isdigit() and int(carro_str.strip()) >= 1
                if carro_str.strip() and not carro_ok:
                    st.caption("⚠️ Número inválido")
            with col_l:
                st.markdown("**↔️ Lado**")
                lado = st.selectbox("Lado", _LADOS, key="_t_lado", label_visibility="collapsed")
        else:
            carro_str = ""
            carro_ok  = True
            lado      = _lp if _lp else "A"

        _destinos_opt = [s for s in SECTORES if s != "Optimización" and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]] + [SECTOR_TERMINADO]
        destino_opt   = st.selectbox("📍 Enviar a:", _destinos_opt, key="_t_destino_opt")

        st.write("")
        if st.button("📤 ENVIAR", type="primary", use_container_width=True, key="btn_enviar_opt"):
            if not es_error and not carro_ok:
                st.warning("⚠️ Ingresá el número de carro.")
            else:
                carro_val = int(carro_str.strip()) if (carro_ok and carro_str.strip()) else (_cp if _cp > 0 else 0)
                ok, err = guardar_registro(_orden, carro_val, lado,
                                           st.session_state.op_confirmado,
                                           f"Enviado a {destino_opt}")
                if ok:
                    agregar_historial(_orden, st.session_state.sector_confirmado, enviado_a=destino_opt)
                    st.session_state.ultimo = {"orden": _orden, "sector": st.session_state.sector_confirmado,
                                               "op": st.session_state.op_confirmado,
                                               "enviado_a": destino_opt, "offline": err == "OFFLINE"}
                    st.session_state.orden_val = ""
                    st.session_state.ord_n += 1
                    st.session_state.reg_error = None
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.error(f"❌ {err}")

    elif _cp > 0:
        # Datos del sector anterior disponibles → 1 solo toque
        st.markdown(f"""
        <div style="background:#0f2336;border-left:4px solid #3b82f6;border-radius:8px;
                    padding:10px 14px;margin-bottom:16px;">
            <div style="font-size:11px;color:#4a6a9a;text-transform:uppercase;letter-spacing:1px;">
                Datos del sector anterior
            </div>
            <div style="font-size:17px;font-weight:700;color:#93c5fd;margin-top:4px;">
                🛒 Carro {_cp} &nbsp;·&nbsp; ↔️ Lado {_lp}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("↘️ TOMAR PIEZA", type="primary", use_container_width=True, key="btn_tomar_prev"):
            ok, err = guardar_registro(_orden, _cp, _lp,
                                       st.session_state.op_confirmado,
                                       f"En Proceso en {st.session_state.sector_confirmado}")
            if ok:
                agregar_historial(_orden, f"En Proceso en {st.session_state.sector_confirmado}")
                st.session_state.ultimo = {"orden": _orden, "sector": st.session_state.sector_confirmado,
                                            "op": st.session_state.op_confirmado,
                                            "enviado_a": None, "offline": err == "OFFLINE"}
                st.session_state.orden_val = ""
                st.session_state.ord_n += 1
                st.session_state.reg_error = None
                st.session_state.paso = 2
                st.rerun()
            else:
                st.error(f"❌ {err}")
    else:
        # Orden nueva → pedir carro y lado
        col_c, col_l = st.columns(2)
        with col_c:
            st.markdown("**🛒 Carro**")
            carro_str  = st.text_input("Carro", key="_t_carro", placeholder="Número...", label_visibility="collapsed")
            carro_ok   = carro_str.strip().isdigit() and int(carro_str.strip()) >= 1
            if carro_str.strip() and not carro_ok:
                st.caption("⚠️ Número inválido")
        with col_l:
            st.markdown("**↔️ Lado**")
            lado = st.selectbox("Lado", _LADOS, key="_t_lado", label_visibility="collapsed")

        st.write("")
        if st.button("↘️ TOMAR PIEZA", type="primary", use_container_width=True, key="btn_tomar_nuevo"):
            if not carro_ok:
                st.warning("⚠️ Ingresá el número de carro.")
            else:
                ok, err = guardar_registro(_orden, int(carro_str.strip()), lado,
                                           st.session_state.op_confirmado,
                                           f"En Proceso en {st.session_state.sector_confirmado}")
                if ok:
                    agregar_historial(_orden, f"En Proceso en {st.session_state.sector_confirmado}")
                    st.session_state.ultimo = {"orden": _orden, "sector": st.session_state.sector_confirmado,
                                                "op": st.session_state.op_confirmado,
                                                "enviado_a": None, "offline": err == "OFFLINE"}
                    st.session_state.orden_val = ""
                    st.session_state.ord_n += 1
                    st.session_state.reg_error = None
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.error(f"❌ {err}")

    st.write("")
    if st.button("← Volver a escanear", use_container_width=True):
        st.session_state.orden_val = ""
        st.session_state.ord_n += 1
        st.session_state.paso = 2
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  PASO 4 — SOLO DESPACHAR (pieza ya tomada → enviar al siguiente sector)
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 4:
    _orden = st.session_state.orden_val
    _cp    = st.session_state.carro_previo
    _lp    = st.session_state.lado_previo
    _LADOS = ["A", "B", "Ambos"]

    # Pre-llenar keys la primera vez
    if st.session_state.get("paso3_fresh", False):
        st.session_state["_d_carro"] = str(_cp) if _cp > 0 else ""
        st.session_state["_d_lado"]  = _lp if _lp in _LADOS else "A"
        st.session_state.paso3_fresh = False

    st.markdown(f"""
    <div style="background:#0d1f3c;border:1px solid #1e3a6a;border-radius:12px;
                padding:12px 16px;margin-bottom:16px;text-align:center;">
        <div style="font-size:11px;color:#4a6a9a;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px;">
            Terminaste con esta pieza
        </div>
        <div style="font-size:26px;font-weight:900;color:#facc15;letter-spacing:2px;">{_orden}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 📤 Despachar al siguiente sector")
    st.caption(f"Desde: **{st.session_state.sector_confirmado}**")
    st.write("")

    es_error = False
    if st.session_state.sector_confirmado == "Optimización":
        es_error = st.checkbox("Es orden de error", key="_d_es_error")

    col_c, col_l = st.columns(2)
    with col_c:
        st.markdown("**🛒 Carro**")
        carro_str = st.text_input("Carro", key="_d_carro", placeholder="Número...", label_visibility="collapsed")
        _carro_ef = carro_str.strip() if carro_str.strip() else (str(_cp) if _cp > 0 else "")
        carro_ok  = _carro_ef.isdigit() and int(_carro_ef) >= 1
        if carro_str.strip() and not carro_ok:
            st.caption("⚠️ Número inválido")
    with col_l:
        st.markdown("**↔️ Lado**")
        lado = st.selectbox("Lado", _LADOS, key="_d_lado", label_visibility="collapsed")

    st.write("")
    opciones_destino = [
        s for s in SECTORES
        if s != st.session_state.sector_confirmado and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]
    ] + [SECTOR_TERMINADO, "Dañado"]

    destino = st.selectbox("📍 Enviar a:", opciones_destino, key="_d_destino")

    st.write("")
    if st.button("📤 FINALIZAR Y ENVIAR", type="primary", use_container_width=True):
        if not carro_ok and not es_error:
            st.warning("⚠️ Ingresá el número de carro.")
        else:
            carro = int(_carro_ef) if carro_ok else 0
            ok, err = True, None
            es_offline = False

            if destino == "Dañado":
                ok, err = guardar_registro(_orden, carro, lado,
                                           st.session_state.op_confirmado, "Dañado")
            elif destino == SECTOR_TERMINADO:
                ok, err = guardar_registro(_orden, 0, "-",
                                           st.session_state.op_confirmado, SECTOR_TERMINADO)
            else:
                ok, err = guardar_registro(_orden, carro, lado,
                                           st.session_state.op_confirmado, f"Enviado a {destino}")

            if ok:
                if err == "OFFLINE": es_offline = True
                agregar_historial(_orden, st.session_state.sector_confirmado, enviado_a=destino)
                st.session_state.ultimo = {
                    "orden": _orden, "sector": st.session_state.sector_confirmado,
                    "op": st.session_state.op_confirmado,
                    "enviado_a": destino, "offline": es_offline
                }
                st.session_state.orden_val = ""
                st.session_state.ord_n    += 1
                st.session_state.reg_error = None
                st.session_state.paso      = 2
                st.rerun()
            else:
                st.error(f"❌ {err}")

    st.write("")
    if st.button("← Volver a escanear", use_container_width=True):
        st.session_state.orden_val = ""
        st.session_state.ord_n += 1
        st.session_state.paso = 2
        st.rerun()
