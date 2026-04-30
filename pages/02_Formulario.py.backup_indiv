import re
import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
import csv
from pathlib import Path

from config import (SECTORES, SECTORES_ESCANEO_DIRECTO, verificar_licencia,
                    get_connection, verificar_estado_sistema,
                    marcar_dvh, desmarcar_dvh, obtener_dvh_info, obtener_par_dvh,
                    obtener_dvh_info_bulk, obtener_pares_dvh_bulk)
from styles import CSS_GLOBAL, render_sb_header, render_sb_operario, render_steps
from components.tarjeta_orden import render_tarjeta_orden, inyectar_css_tarjetas, agrupar_por_orden_maestra, render_grupo_maestro_header
from components.camara_foto import capturar_foto as qrcode_scanner

st.set_page_config(page_title="Carga de Producción", page_icon="📋", layout="centered")

verificar_licencia()
verificar_estado_sistema()
conn = get_connection()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

st.markdown("""
<style>
.numpad-btn button {
    min-height: 55px !important;
    font-size: 22px !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

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
_PFX_RE = re.compile(r'^(?:\s*\[(?:URGENTE|INCIDENCIA)\]\s*)+', re.IGNORECASE)


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
    from sqlalchemy.exc import IntegrityError, DataError
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
        except (IntegrityError, DataError) as e:
            # Errores de constraint/validación: no reintentables
            if guardar_registro_offline(orden, carro, lado, usuario, sector):
                return True, "OFFLINE"
            return False, str(e)
        except Exception as e:
            if intento < 2:
                time.sleep(2)
            else:
                if guardar_registro_offline(orden, carro, lado, usuario, sector):
                    return True, "OFFLINE"
                return False, str(e)


def obtener_activos(sector_actual):
    try:
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros WHERE fecha_hora >= NOW() - INTERVAL '30 days' AND sector != 'Consolidada en DVH' ORDER BY fecha_hora DESC"
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
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros WHERE fecha_hora >= NOW() - INTERVAL '30 days' AND sector != 'Consolidada en DVH' ORDER BY fecha_hora DESC"
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
        sufijos = []
        for o in ordenes:
            parts = o.rsplit(" - ", 1)
            if len(parts) == 2:
                try:
                    sufijos.append(int(parts[1]))
                except ValueError:
                    pass
        siguiente = (max(sufijos) + 1) if sufijos else 2
        return f"{base} - {siguiente}"
    except Exception as e:
        print(f"Error resolver_nombre_orden: {e}")
        return orden_base


def verificar_orden_en_otro_sector(orden_base, sector_actual):
    """Verifica si la orden o sus sub-piezas existen. Devuelve info completa."""
    try:
        base = _PFX_RE.sub("", orden_base).strip()
        # Extraer parte base sin sufijo numérico (66464-1 → 66464)
        import re
        match_base = re.match(r'^(.+?)(?:-(\d+))?$', base)
        orden_sin_sufijo = match_base.group(1) if match_base else base
        
        # Buscar TODAS las piezas con esa base
        df = conn.query(
            "SELECT orden, sector FROM registros "
            "WHERE (TRIM(orden) LIKE :base_pattern OR TRIM(orden) LIKE :urg OR TRIM(orden) LIKE :inc) "
            "  AND sector != 'Consolidada en DVH' "
            "ORDER BY fecha_hora DESC",
            params={
                "base_pattern": f"{orden_sin_sufijo}%",
                "urg": f"[URGENTE] {orden_sin_sufijo}%",
                "inc": f"[INCIDENCIA] {orden_sin_sufijo}%"
            },
            ttl=0
        )
        
        if not df.empty:
            # Encontrar el último número de sub-pieza
            ultimo_numero = 0
            for ord_str in df["orden"].unique():
                ord_clean = _PFX_RE.sub("", ord_str).strip()
                match_num = re.match(rf'^{re.escape(orden_sin_sufijo)}-(\d+)$', ord_clean)
                if match_num:
                    num = int(match_num.group(1))
                    if num > ultimo_numero:
                        ultimo_numero = num
            
            primera = df.iloc[0]
            return {
                "existe": True,
                "orden": primera["orden"],
                "sector": primera["sector"].strip(),
                "orden_base": orden_sin_sufijo,
                "ultimo_numero": ultimo_numero,
                "total_piezas": len(df["orden"].unique())
            }
        return {"existe": False}
    except Exception as e:
        print(f"Error verificar_orden_en_otro_sector: {e}")
        return {"existe": False}


def obtener_carro_lado(orden):
    try:
        base = _PFX_RE.sub("", orden).strip()
        with conn.session as s:
            df = pd.read_sql(
                text(
                    "SELECT carro, lado FROM registros "
                    "WHERE TRIM(orden) = :base OR TRIM(orden) ILIKE :urg OR TRIM(orden) ILIKE :inc "
                    "ORDER BY fecha_hora DESC LIMIT 1"
                ),
                s.connection(),
                params={"base": base, "urg": f"[URGENTE] {base}", "inc": f"[INCIDENCIA] {base}"},
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
    "batch_desp_show":              False,
    "mostrar_advertencia_duplicado": False,
    "orden_duplicada":               None,
    "modal_modo": None,
    "orden_nueva_trigger": None,
    "orden_existe_trigger": None,
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
    
    sector_actual = st.session_state.sector_confirmado
    orden_buscada = valor.strip()
    
    # Obtener listas del sector actual
    entrantes, en_proceso = obtener_activos(sector_actual)
    
    # Normalizar búsqueda (ignorar prefijos)
    orden_normalizada = _PFX_RE.sub("", orden_buscada).strip()
    
    # Buscar en PENDIENTES del sector actual
    orden_en_pendientes = None
    for ord_pend in entrantes:
        ord_norm_pend = _PFX_RE.sub("", ord_pend['orden']).strip()
        if ord_norm_pend == orden_normalizada or ord_pend['orden'].strip() == orden_buscada:
            orden_en_pendientes = ord_pend
            break
    
    # Buscar en EN PROCESO del sector actual
    orden_en_proceso = None
    for ord_proc in en_proceso:
        ord_norm_proc = _PFX_RE.sub("", ord_proc['orden']).strip()
        if ord_norm_proc == orden_normalizada or ord_proc['orden'].strip() == orden_buscada:
            orden_en_proceso = ord_proc
            break
    
    # Si existe EXACTAMENTE en el sector actual → ir al paso correcto (TOMAR/DESPACHAR)
    if sector_actual in ["Corte", "Corte Laminado"]:
        if orden_en_proceso or orden_en_pendientes:
            orden_encontrada = orden_en_proceso or orden_en_pendientes
            st.session_state.orden_val = orden_encontrada['orden']
            st.session_state.carro_previo = orden_encontrada.get('carro', 0)
            st.session_state.lado_previo = orden_encontrada.get('lado', 'A')
            st.session_state.paso3_fresh = True
            st.session_state.paso = 4
            return
    else:
        if orden_en_proceso:
            st.session_state.orden_val = orden_en_proceso['orden']
            st.session_state.carro_previo = orden_en_proceso.get('carro', 0)
            st.session_state.lado_previo = orden_en_proceso.get('lado', 'A')
            st.session_state.paso3_fresh = True
            st.session_state.paso = 4
            return
        elif orden_en_pendientes:
            st.session_state.orden_val = orden_en_pendientes['orden']
            st.session_state.carro_previo = orden_en_pendientes.get('carro', 0)
            st.session_state.lado_previo = orden_en_pendientes.get('lado', 'A')
            st.session_state.paso3_fresh = True
            st.session_state.paso = 3
            return
    
    # Verificar si la ORDEN BASE existe en cualquier sector
    import re
    # Mantener el código escaneado COMPLETO como base de la orden
    # 65455 → base = 65455 → piezas: 65455-1, 65455-2, etc
    # 65455-1 → base = 65455-1 → piezas: 65455-1-1, 65455-1-2, etc
    orden_base = orden_normalizada
    
    # Query mejorado: solo trae el ESTADO ACTUAL de cada pieza (último registro)
    # y hace match EXACTO de la orden base (no captura 648470 cuando buscas 64847)
    df_existencias = conn.query(
        """
        WITH ultimo_estado AS (
            SELECT DISTINCT ON (TRIM(orden)) 
                TRIM(orden) as orden, 
                TRIM(sector) as sector,
                fecha_hora
            FROM registros
            WHERE sector != 'Consolidada en DVH'
            ORDER BY TRIM(orden), fecha_hora DESC
        )
        SELECT orden, sector FROM ultimo_estado
        WHERE (
            orden = :exacto
            OR orden ~ :patron_pieza
            OR orden = :urg_exacto
            OR orden ~ :urg_pieza
            OR orden = :inc_exacto
            OR orden ~ :inc_pieza
        )
        AND sector NOT LIKE 'Terminado%'
        AND sector NOT LIKE 'Entrega%'
        AND sector != 'Dañado'
        ORDER BY fecha_hora DESC
        """,
        params={
            "exacto": orden_base,
            "patron_pieza": f"^{re.escape(orden_base)}-[0-9]+$",
            "urg_exacto": f"[URGENTE] {orden_base}",
            "urg_pieza": f"^\\[URGENTE\\] {re.escape(orden_base)}-[0-9]+$",
            "inc_exacto": f"[INCIDENCIA] {orden_base}",
            "inc_pieza": f"^\\[INCIDENCIA\\] {re.escape(orden_base)}-[0-9]+$"
        },
        ttl=0
    )
    
    if not df_existencias.empty:
        # ═══════════════════════════════════════════════════════════════
        # ORDEN EXISTE → mostrar opciones (agregar piezas o traer)
        # ═══════════════════════════════════════════════════════════════
        # Calcular último número de pieza
        ultimo_numero = 0
        for ord_str in df_existencias["orden"].unique():
            ord_clean = _PFX_RE.sub("", ord_str).strip()
            match_num = re.match(rf'^{re.escape(orden_base)}-(\d+)$', ord_clean)
            if match_num:
                num = int(match_num.group(1))
                if num > ultimo_numero:
                    ultimo_numero = num
        
        # Determinar sector más reciente
        sector_origen = df_existencias.iloc[0]["sector"].strip()
        orden_ejemplo = df_existencias.iloc[0]["orden"]
        
        st.session_state.orden_existe_trigger = {
            "orden_base": orden_base,
            "orden_ejemplo": orden_ejemplo,
            "sector_origen": sector_origen,
            "ultimo_numero": ultimo_numero,
            "total_piezas": len(df_existencias["orden"].unique()),
            "orden_escaneada": orden_buscada
        }
        return
    
    # ═══════════════════════════════════════════════════════════════
    # ORDEN NUEVA → preguntar cuántas piezas tiene
    # ═══════════════════════════════════════════════════════════════
    st.session_state.orden_nueva_trigger = {
        "orden_base": orden_base,
        "orden_escaneada": orden_buscada
    }


def cb_orden():
    val = st.session_state.get(f"_inp_ord_{st.session_state.ord_n}", "").strip()
    procesar_orden(val)


def render_numpad(current_value=""):
    """Teclado numérico para tablets - retorna el valor ingresado."""

    with st.expander("📱 Teclado Numérico", expanded=False):
        st.markdown(f"""
        <div style="background:#1e293b;border:2px solid #3b82f6;border-radius:8px;
                    padding:12px;margin-bottom:12px;text-align:center;">
            <span style="font-size:26px;font-weight:800;color:#60a5fa;letter-spacing:2px;">
                {current_value or '---'}
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="numpad-btn">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            b7 = st.button("7", key="np_7", use_container_width=True)
        with col2:
            b8 = st.button("8", key="np_8", use_container_width=True)
        with col3:
            b9 = st.button("9", key="np_9", use_container_width=True)

        with col1:
            b4 = st.button("4", key="np_4", use_container_width=True)
        with col2:
            b5 = st.button("5", key="np_5", use_container_width=True)
        with col3:
            b6 = st.button("6", key="np_6", use_container_width=True)

        with col1:
            b1 = st.button("1", key="np_1", use_container_width=True)
        with col2:
            b2 = st.button("2", key="np_2", use_container_width=True)
        with col3:
            b3 = st.button("3", key="np_3", use_container_width=True)

        with col1:
            bdel = st.button("⌫", key="np_del", use_container_width=True, type="secondary")
        with col2:
            b0 = st.button("0", key="np_0", use_container_width=True)
        with col3:
            bdash = st.button("-", key="np_dash", use_container_width=True, type="secondary")

        st.markdown('</div>', unsafe_allow_html=True)

        col_c, col_ok = st.columns(2)
        with col_c:
            bclear = st.button("🗑️ LIMPIAR", key="np_clear", use_container_width=True, type="secondary")
        with col_ok:
            bok = st.button("✅ BUSCAR", key="np_ok", use_container_width=True, type="primary")

        if b7: return current_value + "7"
        if b8: return current_value + "8"
        if b9: return current_value + "9"
        if b4: return current_value + "4"
        if b5: return current_value + "5"
        if b6: return current_value + "6"
        if b1: return current_value + "1"
        if b2: return current_value + "2"
        if b3: return current_value + "3"
        if b0: return current_value + "0"
        if bdash: return current_value + "-"
        if bdel: return current_value[:-1] if current_value else ""
        if bclear: return ""
        if bok and current_value: return f"SEARCH:{current_value}"

    return current_value


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

    # ════════════════════════════════════════════════════════════════════
    # MODAL: ORDEN NUEVA (preguntar cuántas piezas tiene)
    # ════════════════════════════════════════════════════════════════════
    if st.session_state.get("orden_nueva_trigger"):
        _on = st.session_state.orden_nueva_trigger
        
        st.markdown(f"""
        <div style="background:#0d2a1a;border:2px solid #1a6a35;border-radius:12px;
                    padding:16px;margin-bottom:20px;">
            <div style="font-size:24px;text-align:center;margin-bottom:8px;">📦</div>
            <div style="font-size:16px;font-weight:700;color:#4ada75;text-align:center;margin-bottom:12px;">
                NUEVA ORDEN
            </div>
            <div style="font-size:14px;color:#a7f3d0;text-align:center;line-height:1.6;">
                Orden: <b>{_on['orden_escaneada']}</b><br>
                ¿Cuántas piezas tiene esta orden?
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_cant, col_dest = st.columns(2)
        with col_cant:
            cantidad_total = st.number_input(
                "Cantidad de piezas",
                min_value=1, max_value=200, value=1, step=1,
                key="modal_nueva_cantidad"
            )
            
            if cantidad_total == 1:
                st.info(f"Se creará: **{_on['orden_base']}-1**")
            else:
                st.info(f"Se crearán: **{_on['orden_base']}-1** hasta **{_on['orden_base']}-{cantidad_total}**")
        
        with col_dest:
            from config import SECTORES
            if st.session_state.sector_confirmado == "Optimización":
                destino_nueva = st.selectbox(
                    "Destino",
                    options=[s for s in SECTORES if s != "Optimización"],
                    key="modal_nueva_destino"
                )
            else:
                destino_nueva = st.session_state.sector_confirmado
                st.info(f"📍 Destino: **{destino_nueva}**")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("← Cancelar", use_container_width=True, key="btn_cancel_nueva"):
                st.session_state.orden_nueva_trigger = None
                st.rerun()
        
        with col_btn2:
            if st.button(f"✅ CARGAR {cantidad_total} pieza(s)", use_container_width=True, type="primary", key="btn_cargar_nueva"):
                creadas = 0
                errores = []
                
                for i in range(1, cantidad_total + 1):
                    orden_pieza = f"{_on['orden_base']}-{i}"
                    
                    if destino_nueva in ["Corte", "Corte Laminado"]:
                        estado = f"En Proceso en {destino_nueva}"
                    else:
                        estado = f"Enviado a {destino_nueva}"
                    
                    ok, err = guardar_registro(
                        orden_pieza, 0, "A",
                        st.session_state.op_confirmado,
                        estado
                    )
                    
                    if ok:
                        creadas += 1
                        agregar_historial(orden_pieza, estado)
                    else:
                        errores.append(f"{orden_pieza}: {err}")
                
                st.session_state.orden_nueva_trigger = None
                
                if errores:
                    st.warning(f"✅ {creadas} creadas. ⚠️ {len(errores)} errores")
                else:
                    st.success(f"✅ {creadas} pieza(s) cargada(s) en {destino_nueva}!")
                
                st.session_state.ord_n += creadas
                import time
                time.sleep(1.5)
                st.rerun()
        
        st.stop()

    # ════════════════════════════════════════════════════════════════════
    # MODAL: ORDEN YA EXISTE (agregar piezas / traer / cancelar)
    # ════════════════════════════════════════════════════════════════════
    if st.session_state.get("orden_existe_trigger"):
        _oe = st.session_state.orden_existe_trigger
        
        if "modal_modo" not in st.session_state:
            st.session_state.modal_modo = None
        
        st.markdown(f"""
        <div style="background:#1e3a8a;border:2px solid #3b82f6;border-radius:12px;
                    padding:16px;margin-bottom:20px;">
            <div style="font-size:24px;text-align:center;margin-bottom:8px;">📋</div>
            <div style="font-size:16px;font-weight:700;color:#93c5fd;text-align:center;margin-bottom:12px;">
                ORDEN YA EXISTE
            </div>
            <div style="font-size:14px;color:#bfdbfe;text-align:center;line-height:1.6;">
                Orden <b>{_oe['orden_base']}</b> ya tiene <b>{_oe['total_piezas']} pieza(s)</b><br>
                Última en: <b>{_oe['sector_origen']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Si NO se eligió modo aún, mostrar opciones principales
        if st.session_state.modal_modo is None:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("➡️ TRAER A MI SECTOR\n(es la misma)", use_container_width=True, type="primary", key="btn_traer"):
                    carro_p, lado_p = obtener_carro_lado(_oe['orden_ejemplo'])
                    ok, err = guardar_registro(
                        _oe['orden_ejemplo'], carro_p, lado_p or "A",
                        st.session_state.op_confirmado,
                        f"En Proceso en {st.session_state.sector_confirmado}"
                    )
                    if ok:
                        agregar_historial(_oe['orden_ejemplo'], f"En Proceso en {st.session_state.sector_confirmado}")
                        st.session_state.ultimo = {
                            "orden": _oe['orden_ejemplo'],
                            "sector": st.session_state.sector_confirmado,
                            "op": st.session_state.op_confirmado,
                            "offline": err == "OFFLINE"
                        }
                        st.session_state.orden_existe_trigger = None
                        st.session_state.modal_modo = None
                        st.session_state.ord_n += 1
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {err}")
            
            with col_b:
                if st.button("➕ AGREGAR PIEZAS\n(es otra pieza)", use_container_width=True, type="secondary", key="btn_agregar"):
                    st.session_state.modal_modo = "agregar"
                    st.rerun()
            
            st.write("")
            if st.button("← Cancelar", use_container_width=True, key="btn_cancel_existe"):
                st.session_state.orden_existe_trigger = None
                st.session_state.modal_modo = None
                st.rerun()
        
        # Modo "agregar" piezas
        elif st.session_state.modal_modo == "agregar":
            st.markdown(f"""
            <div style="background:#0d2a1a;border:1px solid #1a6a35;border-radius:8px;
                        padding:12px;margin-bottom:12px;font-size:13px;color:#a7f3d0;text-align:center;">
                Próxima pieza será: <b>{_oe['orden_base']}-{_oe['ultimo_numero'] + 1}</b>
            </div>
            """, unsafe_allow_html=True)
            
            col_cant, col_dest = st.columns(2)
            with col_cant:
                cantidad_agregar = st.number_input(
                    "¿Cuántas piezas agregar?",
                    min_value=1, max_value=100, value=1, step=1,
                    key="modal_agregar_cantidad"
                )
                
                _desde = _oe['ultimo_numero'] + 1
                _hasta = _oe['ultimo_numero'] + cantidad_agregar
                if cantidad_agregar == 1:
                    st.info(f"Se creará: **{_oe['orden_base']}-{_desde}**")
                else:
                    st.info(f"Se crearán: **{_oe['orden_base']}-{_desde}** hasta **{_oe['orden_base']}-{_hasta}**")
            
            with col_dest:
                from config import SECTORES
                if st.session_state.sector_confirmado == "Optimización":
                    destino_agregar = st.selectbox(
                        "Destino",
                        options=[s for s in SECTORES if s != "Optimización"],
                        key="modal_agregar_destino"
                    )
                else:
                    destino_agregar = st.session_state.sector_confirmado
                    st.info(f"📍 Destino: **{destino_agregar}**")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("← Volver", use_container_width=True, key="btn_volver_agregar"):
                    st.session_state.modal_modo = None
                    st.rerun()
            
            with col_btn2:
                if st.button(f"✅ AGREGAR {cantidad_agregar} pieza(s)", use_container_width=True, type="primary", key="btn_confirmar_agregar"):
                    creadas = 0
                    errores = []
                    
                    for i in range(1, cantidad_agregar + 1):
                        nuevo_num = _oe['ultimo_numero'] + i
                        orden_nueva = f"{_oe['orden_base']}-{nuevo_num}"
                        
                        if destino_agregar in ["Corte", "Corte Laminado"]:
                            estado = f"En Proceso en {destino_agregar}"
                        else:
                            estado = f"Enviado a {destino_agregar}"
                        
                        ok, err = guardar_registro(
                            orden_nueva, 0, "A",
                            st.session_state.op_confirmado,
                            estado
                        )
                        
                        if ok:
                            creadas += 1
                            agregar_historial(orden_nueva, estado)
                        else:
                            errores.append(f"{orden_nueva}: {err}")
                    
                    st.session_state.orden_existe_trigger = None
                    st.session_state.modal_modo = None
                    
                    if errores:
                        st.warning(f"✅ {creadas} creadas. ⚠️ {len(errores)} errores")
                    else:
                        st.success(f"✅ {creadas} pieza(s) agregada(s) en {destino_agregar}!")
                    
                    st.session_state.ord_n += creadas
                    import time
                    time.sleep(1.5)
                    st.rerun()
        
        st.stop()

    # ── Auto-guardar Entrega / Terminado ──────────────────────────────────────
    if st.session_state.entrega_lista:
        st.session_state.entrega_lista = False
        ok, err = guardar_registro(
            st.session_state.orden_val,
            st.session_state.carro_previo,
            st.session_state.lado_previo or "-",
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
        st.caption("📸 Enfocá la etiqueta con la cámara trasera y capturá.")
        raw_foto = qrcode_scanner(key=f"_cam_{st.session_state.ord_n}")
        if raw_foto and raw_foto.startswith("data:image"):
            import base64 as _b64
            from io import BytesIO as _BytesIO
            _, b64data = raw_foto.split(",", 1)
            img_bytes = _BytesIO(_b64.b64decode(b64data))
            codigo_auto = decodificar_imagen(img_bytes)
            if codigo_auto:
                st.success(f"✅ Código detectado: **{codigo_auto}**")
                procesar_orden(codigo_auto)
                st.session_state.ord_n += 1
                st.rerun()
            else:
                st.warning("No se pudo leer el código. La cámara se reactivó, intentá de nuevo.")
        st.markdown('<div style="font-size:13px;color:#f0c040;margin-bottom:6px;">👀 O ingresá el número de la etiqueta:</div>', unsafe_allow_html=True)
        cod_manual = st.text_input("Código", key=f"_cam_manual_{st.session_state.ord_n}",
                                   placeholder="Ej: 65365-3", label_visibility="collapsed")
        if st.button("✅ Confirmar", use_container_width=True, type="primary", key=f"_cam_ok_{st.session_state.ord_n}"):
            if cod_manual.strip():
                procesar_orden(cod_manual.strip())
                st.session_state.ord_n += 1
                st.rerun()
            else:
                st.warning("Ingresá el código.")

        if st.button("⌨️ Volver al escáner / teclado", key="btn_volver_scan"):
            st.session_state.modo_camara = False
            st.session_state.ord_n += 1
            st.rerun()

    # Teclado numérico para tablets
    if "numpad_value" not in st.session_state:
        st.session_state.numpad_value = ""

    resultado_numpad = render_numpad(st.session_state.numpad_value)

    if resultado_numpad.startswith("SEARCH:"):
        orden_buscar = resultado_numpad.replace("SEARCH:", "")
        procesar_orden(orden_buscar)
        st.session_state.numpad_value = ""
        st.rerun()
    elif resultado_numpad != st.session_state.numpad_value:
        st.session_state.numpad_value = resultado_numpad
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
    inyectar_css_tarjetas()

    if not es_terminado and not es_entrega:
        entrantes, en_proceso = obtener_activos(st.session_state.sector_confirmado)

        # Para Corte y Corte Laminado: no mostrar PENDIENTES, ir directo a DESPACHAR
        if st.session_state.sector_confirmado not in ["Corte", "Corte Laminado"]:
            # PENDIENTES — expander con contador
            with st.expander(
                f"📥 PENDIENTES DE RECIBIR  ·  {len(entrantes)} orden{'es' if len(entrantes) != 1 else ''}",
                expanded=len(entrantes) > 0
            ):
                _buscar_ent = st.text_input("", placeholder="🔍 Buscar orden o carro...", key="buscar_entrantes")
                _entrantes_fil = [r for r in entrantes if _buscar_ent.strip().lower() in str(r['orden']).lower() or _buscar_ent.strip().lower() in str(r.get('carro', '')).lower() or _buscar_ent.strip().lower() == str(r.get('lado', '')).lower()] if _buscar_ent.strip() else entrantes
                if not entrantes:
                    st.info("No hay órdenes entrantes en este momento.")
                elif not _entrantes_fil:
                    st.warning("No se encontraron órdenes.")
                else:
                    _sk = st.session_state.sector_confirmado
                    _pkey_e = f"pag_ent_{_sk}"
                    if st.session_state.get(f"_psrch_ent_{_sk}") != _buscar_ent:
                        st.session_state[_pkey_e] = 20
                        st.session_state[f"_psrch_ent_{_sk}"] = _buscar_ent
                    _lim_e = st.session_state.get(_pkey_e, 20)
                    _grupos_ent  = agrupar_por_orden_maestra(_entrantes_fil)
                    _glist_e     = list(_grupos_ent.items())
                    _visible_e   = _glist_e[:_lim_e]
                    _dvh_bulk_e  = obtener_dvh_info_bulk([r['orden'] for _, piezas in _visible_e for r in piezas])
                    if st.session_state.sector_confirmado == "DVH":
                        _maestras_e = [m for m, _ in _visible_e]
                        _pares_e = obtener_pares_dvh_bulk(_maestras_e)
                    else:
                        _pares_e = {}
    
                    # ── Selección múltiple ─────────────────────────────────────────
                    _sel_pend = {_m: _pzs for _m, _pzs in _visible_e if st.session_state.get(f"chk_pend_{_m}", False)}
                    _n_sel_pend = len(_sel_pend)
                    _total_piezas_pend = sum(len(piezas) for piezas in _sel_pend.values())
                    
                    if _n_sel_pend > 0:
                        st.info(f"☑️ {_total_piezas_pend} pieza(s) seleccionada(s)")
                    
                    # Mostrar botón si hay 2+ checkboxes O 2+ piezas totales
                    if _n_sel_pend >= 2 or _total_piezas_pend >= 2:
                        if st.button(f"↘️ TOMAR SELECCIONADAS ({_total_piezas_pend} piezas)", type="primary",
                                     use_container_width=True, key="btn_batch_tomar"):
                            _tomadas_b, _errores_tb = 0, []
                            for _bm, _bpzs in _sel_pend.items():
                                for _brow in _bpzs:
                                    _bok, _berr = guardar_registro(
                                        _brow['orden'], _brow.get('carro', 0), _brow.get('lado', '-'),
                                        st.session_state.op_confirmado,
                                        f"En Proceso en {st.session_state.sector_confirmado}"
                                    )
                                    if _bok:
                                        agregar_historial(_brow['orden'], f"En Proceso en {st.session_state.sector_confirmado}")
                                        _tomadas_b += 1
                                    else:
                                        _errores_tb.append(_brow['orden'])
                            for _bm in list(_sel_pend.keys()):
                                st.session_state[f"chk_pend_{_bm}"] = False
                            st.session_state.ord_n += 1
                            if _tomadas_b > 0:
                                st.session_state.ultimo = {
                                    "orden": f"{_tomadas_b} órdenes",
                                    "sector": f"En Proceso en {st.session_state.sector_confirmado}",
                                    "op": st.session_state.op_confirmado, "offline": False
                                }
                            if _errores_tb:
                                st.session_state.reg_error = f"Errores en: {', '.join(_errores_tb[:5])}"
                            st.rerun()
    
                    for _maestro_e, _piezas_e in _visible_e:
                        if st.session_state.sector_confirmado == "DVH":
                            _par_e = _pares_e.get(_maestro_e, {"ambas_marcadas": False, "cara1": None, "cara2": None, "ambas_en_dvh": False})
                            if _par_e["ambas_marcadas"]:
                                _ambas_e = _par_e["ambas_en_dvh"]
                                _estado_badge_e = "&#x2705; Pareja lista" if _ambas_e else "&#x23F3; Esperando Cara"
                                st.markdown(
                                    f'<div style="background:#0c2a3a;border-left:4px solid #0ea5e9;'
                                    f'border-radius:6px;padding:6px 12px;margin-bottom:4px;font-size:13px;">'
                                    f'&#x1FA9F; DVH {_maestro_e} &nbsp; <b>{_estado_badge_e}</b></div>',
                                    unsafe_allow_html=True
                                )
                                for _cn_e in [1, 2]:
                                    _ci_e = _par_e.get(f"cara{_cn_e}")
                                    if _ci_e:
                                        _icon_e = "&#x2705;" if _ci_e["esta_en_dvh"] else f"&#x23F3; En {_ci_e['sector_actual']}"
                                        st.markdown(f'<div style="font-size:12px;color:#94a3b8;padding-left:16px;">'
                                                    f'Cara {_cn_e} ({_ci_e["orden_pieza"]}): {_icon_e}</div>',
                                                    unsafe_allow_html=True)
                            elif _par_e["cara1"] or _par_e["cara2"]:
                                _falta_n_e = 2 if _par_e["cara1"] else 1
                                st.markdown(
                                    f'<div style="background:#2a1f00;border-left:4px solid #eab308;'
                                    f'border-radius:6px;padding:6px 12px;margin-bottom:4px;font-size:13px;color:#fcd34d;">'
                                    f'&#x26A0;&#xFE0F; {_maestro_e} — Falta marcar Cara {_falta_n_e} en sectores anteriores</div>',
                                    unsafe_allow_html=True
                                )
                        _col_chk_e, _col_card_e = st.columns([0.06, 0.94])
                        with _col_chk_e:
                            st.checkbox("", key=f"chk_pend_{_maestro_e}", label_visibility="collapsed")
                        with _col_card_e:
                            if len(_piezas_e) > 1:
                                _carro_g = _piezas_e[0].get('carro', '')
                                render_grupo_maestro_header(_maestro_e, len(_piezas_e), _carro_g, estado="pendiente")
                                with st.expander("ver piezas", expanded=False):
                                    for row in _piezas_e:
                                        _di_e = _dvh_bulk_e.get(row['orden'])
                                        if render_tarjeta_orden(
                                            row, f"↘️ TOMAR — {row['orden']}", f"rec_{row['orden']}",
                                            estado="pendiente", dentro_de_grupo=True,
                                            dvh_cara=_di_e["cara"] if _di_e else None
                                        ):
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
                            else:
                                row = _piezas_e[0]
                                _di_e = _dvh_bulk_e.get(row['orden'])
                                if render_tarjeta_orden(
                                    row, f"↘️ TOMAR — {row['orden']}", f"rec_{row['orden']}",
                                    estado="pendiente", dvh_cara=_di_e["cara"] if _di_e else None
                                ):
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
                    _resto_e = len(_glist_e) - _lim_e
                    if _resto_e > 0:
                        if st.button(f"Mostrar más ({_resto_e} restantes)", key=f"mas_ent_{_sk}"):
                            st.session_state[_pkey_e] = _lim_e + 20
                            st.rerun()
    
            st.write("")

        # EN PROCESO — expander con contador
        with st.expander(
            f"⚙️ EN PROCESO EN MI MESA  ·  {len(en_proceso)} pieza{'s' if len(en_proceso) != 1 else ''}",
            expanded=len(en_proceso) > 0
        ):
            _buscar_proc = st.text_input("", placeholder="🔍 Buscar orden o carro...", key="buscar_en_proceso")
            _en_proceso_fil = [r for r in en_proceso if _buscar_proc.strip().lower() in str(r['orden']).lower() or _buscar_proc.strip().lower() in str(r.get('carro', '')).lower() or _buscar_proc.strip().lower() == str(r.get('lado', '')).lower()] if _buscar_proc.strip() else en_proceso
            if not en_proceso:
                st.info("No tenés piezas en tu mesa actualmente.")
            elif not _en_proceso_fil:
                st.warning("No se encontraron órdenes.")
            else:
                _sk = st.session_state.sector_confirmado
                _pkey_p = f"pag_proc_{_sk}"
                if st.session_state.get(f"_psrch_proc_{_sk}") != _buscar_proc:
                    st.session_state[_pkey_p] = 20
                    st.session_state[f"_psrch_proc_{_sk}"] = _buscar_proc
                _lim_p = st.session_state.get(_pkey_p, 20)
                _grupos_proc = agrupar_por_orden_maestra(_en_proceso_fil)
                _glist_p     = list(_grupos_proc.items())
                _visible_p   = _glist_p[:_lim_p]
                _dvh_bulk_p  = obtener_dvh_info_bulk([r['orden'] for _, piezas in _visible_p for r in piezas])
                if st.session_state.sector_confirmado == "DVH":
                    _maestras_p = [m for m, _ in _visible_p]
                    _pares_p = obtener_pares_dvh_bulk(_maestras_p)
                else:
                    _pares_p = {}

                # ── Selección múltiple ─────────────────────────────────────────
                _sel_proc = {_m: _pzs for _m, _pzs in _visible_p if st.session_state.get(f"chk_proc_{_m}", False)}
                _n_sel_proc = len(_sel_proc)
                _total_piezas = sum(len(piezas) for piezas in _sel_proc.values())
                
                if _n_sel_proc > 0:
                    st.info(f"☑️ {_total_piezas} pieza(s) seleccionada(s)")

                # ── Formulario batch despachar (se muestra directo si hay 2+ piezas) ──
                if _n_sel_proc >= 2 or _total_piezas >= 2:
                    st.markdown("---")
                    st.markdown(f"**📤 Despachar {_total_piezas} piezas seleccionadas**")
                    _LADOS_B = ["A", "B", "Ambos"]
                    _es_dvh_b = (st.session_state.sector_confirmado == "DVH")
                    _es_opt_b = (st.session_state.sector_confirmado == "Optimización")

                    _es_error_b = False
                    if _es_opt_b:
                        _es_error_b = st.checkbox("Es orden de error (aplica a todas)", value=False, key="_bd_es_error")

                    _col_bc, _col_bl = st.columns(2)
                    with _col_bc:
                        st.markdown("**🛒 Carro**")
                        _b_carro_str = st.text_input("Carro", key="_bd_carro", placeholder="Número...", label_visibility="collapsed")
                        _b_carro_ok = bool(_b_carro_str.strip()) and _b_carro_str.strip().isdigit() and int(_b_carro_str.strip()) >= 1
                        if _b_carro_str.strip() and not _b_carro_ok:
                            st.caption("⚠️ Número inválido")
                    with _col_bl:
                        st.markdown("**↔️ Lado**")
                        _b_lado = st.selectbox("Lado", _LADOS_B, key="_bd_lado", label_visibility="collapsed")

                    if not _es_dvh_b:
                        _destinos_b = [s for s in SECTORES if s != st.session_state.sector_confirmado and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]] + [SECTOR_TERMINADO, "Dañado"]
                        if _es_opt_b:
                            _destinos_b = [s for s in SECTORES if s != "Optimización" and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]] + [SECTOR_TERMINADO]
                        _b_destino = st.selectbox("📍 Enviar a:", _destinos_b, key="_bd_destino")
                    else:
                        _b_destino = "Terminado"

                    st.write("")
                    _btn_lbl_conf = "🪟 CONSOLIDAR TODAS" if _es_dvh_b else "📤 CONFIRMAR DESPACHO"
                    if st.button(_btn_lbl_conf, type="primary", use_container_width=True, key="btn_confirm_batch_desp"):
                        if not _es_dvh_b and not _b_carro_ok and not _es_error_b:
                            st.warning("⚠️ Ingresá el número de carro.")
                        else:
                            _b_carro_val = int(_b_carro_str.strip()) if _b_carro_ok else 0
                            _despachadas_b, _errores_db = 0, []
                            if _es_dvh_b:
                                for _bm_dvh in list(_sel_proc.keys()):
                                    _par_b = _pares_p.get(_bm_dvh, {})
                                    if _par_b.get("ambas_en_dvh", False):
                                        _c1_b = _par_b["cara1"]
                                        _c2_b = _par_b["cara2"]
                                        try:
                                            _ts_b = _now_utc()
                                            _op_b = st.session_state.op_confirmado
                                            with conn.session as _sb:
                                                for _cp_b in [_c1_b, _c2_b]:
                                                    _sb.execute(text("""
                                                        INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                                        VALUES (:f, :o, :c, :l, :u, 'Consolidada en DVH')
                                                    """), {"f": _ts_b, "o": _cp_b["orden_pieza"],
                                                           "c": _b_carro_val, "l": _b_lado, "u": _op_b})
                                                _sb.execute(text("""
                                                    INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                                    VALUES (:f, :o, :c, :l, :u, 'Enviado a Terminado')
                                                """), {"f": _ts_b, "o": _bm_dvh, "c": _b_carro_val, "l": _b_lado, "u": _op_b})
                                                _sb.commit()
                                            agregar_historial(_bm_dvh, "DVH", enviado_a="Terminado (DVH)")
                                            _despachadas_b += 1
                                        except Exception as _exc_dvh:
                                            _errores_db.append(_bm_dvh)
                                    else:
                                        _errores_db.append(_bm_dvh)
                            else:
                                for _bm_n, _bpzs_n in _sel_proc.items():
                                    for _brow_n in _bpzs_n:
                                        if _b_destino == "Dañado":
                                            _bok_n, _berr_n = guardar_registro(_brow_n['orden'], _b_carro_val, _b_lado, st.session_state.op_confirmado, "Dañado")
                                        elif _b_destino == SECTOR_TERMINADO:
                                            _bok_n, _berr_n = guardar_registro(_brow_n['orden'], _b_carro_val, _b_lado, st.session_state.op_confirmado, SECTOR_TERMINADO)
                                        else:
                                            # Para Corte y Corte Laminado, enviar directo a EN PROCESO
                                            if _b_destino in ["Corte", "Corte Laminado"]:
                                                _bok_n, _berr_n = guardar_registro(_brow_n['orden'], _b_carro_val, _b_lado, st.session_state.op_confirmado, f"En Proceso en {_b_destino}")
                                            else:
                                                _bok_n, _berr_n = guardar_registro(_brow_n['orden'], _b_carro_val, _b_lado, st.session_state.op_confirmado, f"Enviado a {_b_destino}")
                                        if _bok_n:
                                            agregar_historial(_brow_n['orden'], st.session_state.sector_confirmado, enviado_a=_b_destino)
                                            _despachadas_b += 1
                                        else:
                                            _errores_db.append(_brow_n['orden'])
                            for _bm_c in list(_sel_proc.keys()):
                                st.session_state[f"chk_proc_{_bm_c}"] = False
                            st.session_state.ord_n += 1
                            if _despachadas_b > 0:
                                _dest_lbl = "Terminado (DVH)" if _es_dvh_b else _b_destino
                                st.session_state.ultimo = {
                                    "orden": f"{_despachadas_b} órdenes",
                                    "sector": st.session_state.sector_confirmado,
                                    "op": st.session_state.op_confirmado,
                                    "enviado_a": _dest_lbl, "offline": False
                                }
                            if _errores_db:
                                st.session_state.reg_error = f"Errores en: {', '.join(_errores_db[:5])}"
                            st.rerun()
                    st.markdown("---")

                for _maestro_p, _piezas_p in _visible_p:
                    if st.session_state.sector_confirmado == "DVH":
                        _par_p = _pares_p.get(_maestro_p, {"ambas_marcadas": False, "cara1": None, "cara2": None, "ambas_en_dvh": False})
                        if _par_p["ambas_marcadas"]:
                            _ambas_p = _par_p["ambas_en_dvh"]
                            _estado_badge_p = "&#x2705; Pareja lista" if _ambas_p else "&#x23F3; Esperando Cara"
                            st.markdown(
                                f'<div style="background:#0c2a3a;border-left:4px solid #0ea5e9;'
                                f'border-radius:6px;padding:6px 12px;margin-bottom:4px;font-size:13px;">'
                                f'&#x1FA9F; DVH {_maestro_p} &nbsp; <b>{_estado_badge_p}</b></div>',
                                unsafe_allow_html=True
                            )
                            for _cn_p in [1, 2]:
                                _ci_p = _par_p.get(f"cara{_cn_p}")
                                if _ci_p:
                                    _icon_p = "&#x2705;" if _ci_p["esta_en_dvh"] else f"&#x23F3; En {_ci_p['sector_actual']}"
                                    st.markdown(f'<div style="font-size:12px;color:#94a3b8;padding-left:16px;">'
                                                f'Cara {_cn_p} ({_ci_p["orden_pieza"]}): {_icon_p}</div>',
                                                unsafe_allow_html=True)
                        elif _par_p["cara1"] or _par_p["cara2"]:
                            _falta_n_p = 2 if _par_p["cara1"] else 1
                            st.markdown(
                                f'<div style="background:#2a1f00;border-left:4px solid #eab308;'
                                f'border-radius:6px;padding:6px 12px;margin-bottom:4px;font-size:13px;color:#fcd34d;">'
                                f'&#x26A0;&#xFE0F; {_maestro_p} — Falta marcar Cara {_falta_n_p} en sectores anteriores</div>',
                                unsafe_allow_html=True
                            )
                    # En DVH: mostrar indicador visual pero NO bloquear (permite despachar piezas viejas)
                    _tiene_par_dvh = True
                    if st.session_state.sector_confirmado == "DVH":
                        _par_for_chk = _pares_p.get(_maestro_p, {"ambas_en_dvh": False})
                        _tiene_par_dvh = _par_for_chk.get("ambas_en_dvh", False)
                    
                    # Estructura de columnas según sector
                    if st.session_state.sector_confirmado == "DVH":
                        _col_chk_p, _col_ind, _col_card_p = st.columns([0.06, 0.04, 0.90])
                    else:
                        _col_chk_p, _col_card_p = st.columns([0.06, 0.94])
                        _col_ind = None
                    
                    with _col_chk_p:
                        st.checkbox("", key=f"chk_proc_{_maestro_p}", label_visibility="collapsed")
                    
                    # Indicador visual SOLO en DVH
                    if _col_ind is not None:
                        with _col_ind:
                            if _tiene_par_dvh:
                                st.markdown('<div style="font-size:18px;text-align:center;padding-top:8px;" title="Tiene su par">🟢</div>', unsafe_allow_html=True)
                            else:
                                st.markdown('<div style="font-size:18px;text-align:center;padding-top:8px;" title="Falta el par">🟡</div>', unsafe_allow_html=True)
                    with _col_card_p:
                        if len(_piezas_p) > 1:
                            _carro_g = _piezas_p[0].get('carro', '')
                            render_grupo_maestro_header(_maestro_p, len(_piezas_p), _carro_g, estado="en_proceso")
                            with st.expander("ver piezas", expanded=False):
                                for row in _piezas_p:
                                    _di_p = _dvh_bulk_p.get(row['orden'])
                                    _meta_proc = f"&#x1F6D2; Carro {row['carro']} · Lado {row['lado']} · desde las {row['fecha_hora']}"
                                    if render_tarjeta_orden(
                                        row, f"📤 DESPACHAR — {row['orden']}", f"fin_{row['orden']}",
                                        estado="en_proceso", meta_texto=_meta_proc, dentro_de_grupo=True,
                                        dvh_cara=_di_p["cara"] if _di_p else None
                                    ):
                                        st.session_state.orden_val    = row['orden']
                                        st.session_state.carro_previo = int(row.get('carro') or 0)
                                        st.session_state.lado_previo  = str(row.get('lado') or 'A')
                                        st.session_state.paso3_fresh  = True
                                        st.session_state.paso         = 4
                                        st.rerun()
                        else:
                            row = _piezas_p[0]
                            _di_p = _dvh_bulk_p.get(row['orden'])
                            _meta_proc = f"&#x1F6D2; Carro {row['carro']} · Lado {row['lado']} · desde las {row['fecha_hora']}"
                            if render_tarjeta_orden(
                                row, f"📤 DESPACHAR — {row['orden']}", f"fin_{row['orden']}",
                                estado="en_proceso", meta_texto=_meta_proc,
                                dvh_cara=_di_p["cara"] if _di_p else None
                            ):
                                st.session_state.orden_val    = row['orden']
                                st.session_state.carro_previo = int(row.get('carro') or 0)
                                st.session_state.lado_previo  = str(row.get('lado') or 'A')
                                st.session_state.paso3_fresh  = True
                                st.session_state.paso         = 4
                                st.rerun()
                _resto_p = len(_glist_p) - _lim_p
                if _resto_p > 0:
                    if st.button(f"Mostrar más ({_resto_p} restantes)", key=f"mas_proc_{_sk}"):
                        st.session_state[_pkey_p] = _lim_p + 20
                        st.rerun()

    # ── KANBAN ENTREGA ────────────────────────────────────────────────────────
    if es_entrega:
        pendientes = obtener_pendientes_entrega()
        with st.expander(
            f"📥 LISTAS PARA ENTREGAR  ·  {len(pendientes)} orden{'es' if len(pendientes) != 1 else ''}",
            expanded=len(pendientes) > 0
        ):
            _buscar_pend = st.text_input("", placeholder="🔍 Buscar orden o carro...", key="buscar_entrega")
            _pendientes_fil = [r for r in pendientes if _buscar_pend.strip().lower() in str(r['orden']).lower() or _buscar_pend.strip().lower() in str(r.get('carro', '')).lower() or _buscar_pend.strip().lower() == str(r.get('lado', '')).lower()] if _buscar_pend.strip() else pendientes
            if not pendientes:
                st.info("No hay productos terminados esperando entrega.")
            elif not _pendientes_fil:
                st.warning("No se encontraron órdenes.")
            else:
                _pkey_d = "pag_entrega"
                if st.session_state.get("_psrch_entrega") != _buscar_pend:
                    st.session_state[_pkey_d] = 20
                    st.session_state["_psrch_entrega"] = _buscar_pend
                _lim_d = st.session_state.get(_pkey_d, 20)
                _grupos_pend = agrupar_por_orden_maestra(_pendientes_fil)
                _glist_d     = list(_grupos_pend.items())
                _visible_d   = _glist_d[:_lim_d]
                _dvh_bulk_d  = obtener_dvh_info_bulk([r['orden'] for _, piezas in _visible_d for r in piezas])
                for _maestro_d, _piezas_d in _visible_d:
                    if len(_piezas_d) > 1:
                        _carro_g = _piezas_d[0].get('carro', '')
                        render_grupo_maestro_header(_maestro_d, len(_piezas_d), _carro_g, estado="terminado")
                        with st.expander("ver piezas", expanded=False):
                            for row in _piezas_d:
                                _di_d = _dvh_bulk_d.get(row['orden'])
                                _meta_ent = f"&#x1F6D2; {row['carro']} · {row['lado']} · {row['fecha_hora']}"
                                if render_tarjeta_orden(
                                    row, "🚀 ENTREGAR", f"ent_{row['orden']}",
                                    estado="terminado", meta_texto=_meta_ent, dentro_de_grupo=True,
                                    dvh_cara=_di_d["cara"] if _di_d else None
                                ):
                                    st.session_state.orden_val     = row['orden']
                                    st.session_state.carro_previo  = int(row.get('carro') or 0)
                                    st.session_state.lado_previo   = str(row.get('lado') or '-')
                                    st.session_state.entrega_lista = True
                                    st.rerun()
                    else:
                        row = _piezas_d[0]
                        _di_d = _dvh_bulk_d.get(row['orden'])
                        _meta_ent = f"&#x1F6D2; {row['carro']} · {row['lado']} · {row['fecha_hora']}"
                        if render_tarjeta_orden(
                            row, "🚀 ENTREGAR", f"ent_{row['orden']}",
                            estado="terminado", meta_texto=_meta_ent,
                            dvh_cara=_di_d["cara"] if _di_d else None
                        ):
                            st.session_state.orden_val     = row['orden']
                            st.session_state.carro_previo  = int(row.get('carro') or 0)
                            st.session_state.lado_previo   = str(row.get('lado') or '-')
                            st.session_state.entrega_lista = True
                            st.rerun()
                _resto_d = len(_glist_d) - _lim_d
                if _resto_d > 0:
                    if st.button(f"Mostrar más ({_resto_d} restantes)", key="mas_entrega"):
                        st.session_state[_pkey_d] = _lim_d + 20
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
        es_error = st.checkbox("Es orden de error", value=True, key="_t_es_error")

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
                # Para Corte y Corte Laminado, las órdenes van directo a EN PROCESO (sin pasar por TOMAR)
                if destino_opt in ["Corte", "Corte Laminado"]:
                    ok, err = guardar_registro(_orden, carro_val, lado,
                                               st.session_state.op_confirmado,
                                               f"En Proceso en {destino_opt}")
                else:
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
        st.session_state.setdefault("_d_carro", str(_cp) if _cp > 0 else "")
        st.session_state["_d_lado"]  = _lp if (_cp > 0 and _lp in _LADOS) else "A"
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

    # ── Marcado DVH en sectores de origen ────────────────────────────────────
    _sector_es_origen_dvh = st.session_state.sector_confirmado in ("Optimización", "Corte", "Corte Laminado")
    if _sector_es_origen_dvh:
        _dvh_info_actual = obtener_dvh_info(_orden)
        _es_dvh_actual   = _dvh_info_actual is not None
        es_dvh = st.checkbox("🪟 Esta pieza es parte de un DVH", value=_es_dvh_actual, key="_d_es_dvh")
        if es_dvh:
            _cara_default = (_dvh_info_actual["cara"] - 1) if _es_dvh_actual else 0
            cara_dvh = st.radio("Cara", [1, 2], index=_cara_default, horizontal=True, key="_d_cara_dvh")
        else:
            cara_dvh = None
    else:
        es_dvh       = False
        cara_dvh     = None
        _es_dvh_actual = False

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

    # ── Lógica de despacho: DVH vs resto ─────────────────────────────────────
    if st.session_state.sector_confirmado == "DVH":
        _info_dvh = obtener_dvh_info(_orden)

        if _info_dvh is None:
            # Pieza NO marcada como DVH → flujo idéntico al actual + opción soft
            _marcar_ahora = st.checkbox("🪟 ¿Marcar como DVH ahora?", value=False, key="_d_marcar_dvh_soft")
            if _marcar_ahora:
                _cara_soft = st.radio("Cara", [1, 2], index=0, horizontal=True, key="_d_cara_soft")
            else:
                _cara_soft = None

            opciones_destino = [
                s for s in SECTORES
                if s != st.session_state.sector_confirmado and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]
            ] + [SECTOR_TERMINADO, "Dañado"]
            destino = st.selectbox("📍 Enviar a:", opciones_destino, key="_d_destino")

            st.write("")
            if st.button("📤 FINALIZAR Y ENVIAR", type="primary", use_container_width=True):
                if not carro_ok:
                    st.warning("⚠️ Ingresá el número de carro.")
                else:
                    carro = int(_carro_ef) if carro_ok else 0
                    if _marcar_ahora and _cara_soft:
                        marcar_dvh(_orden, _cara_soft, st.session_state.op_confirmado, "DVH")
                        _info_dvh = obtener_dvh_info(_orden)
                        _par_soft = obtener_par_dvh(_info_dvh["maestra"]) if _info_dvh else None
                        if _par_soft and _par_soft["ambas_en_dvh"]:
                            # Ambas caras presentes → despacho consolidado
                            _maestra_s  = _info_dvh["maestra"]
                            _cara1_s    = _par_soft["cara1"]
                            _cara2_s    = _par_soft["cara2"]
                            _op         = st.session_state.op_confirmado
                            _ts         = _now_utc()
                            with conn.session as _s:
                                for _cp_data in [_cara1_s, _cara2_s]:
                                    _s.execute(text("""
                                        INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                        VALUES (:f, :o, :c, :l, :u, 'Consolidada en DVH')
                                    """), {"f": _ts, "o": _cp_data["orden_pieza"],
                                           "c": carro, "l": lado, "u": _op})
                                _s.execute(text("""
                                    INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                    VALUES (:f, :o, :c, :l, :u, 'Enviado a Terminado')
                                """), {"f": _ts, "o": _maestra_s, "c": carro, "l": lado, "u": _op})
                                _s.commit()
                            agregar_historial(_orden, "DVH", enviado_a="Terminado (DVH)")
                            st.session_state.ultimo = {
                                "orden": _maestra_s, "sector": "DVH",
                                "op": _op, "enviado_a": "Terminado", "offline": False
                            }
                            st.session_state.orden_val = ""
                            st.session_state.ord_n    += 1
                            st.session_state.reg_error = None
                            st.session_state.paso      = 2
                            st.rerun()
                        # Si no ambas_en_dvh, despacho normal (la marca queda guardada)
                    ok, err = True, None
                    if destino == "Dañado":
                        ok, err = guardar_registro(_orden, carro, lado, st.session_state.op_confirmado, "Dañado")
                    elif destino == SECTOR_TERMINADO:
                        ok, err = guardar_registro(_orden, carro, lado, st.session_state.op_confirmado, SECTOR_TERMINADO)
                    else:
                        # Para Corte y Corte Laminado, las órdenes van directo a EN PROCESO (sin pasar por TOMAR)
                        if destino in ["Corte", "Corte Laminado"]:
                            ok, err = guardar_registro(_orden, carro, lado, st.session_state.op_confirmado, f"En Proceso en {destino}")
                        else:
                            ok, err = guardar_registro(_orden, carro, lado, st.session_state.op_confirmado, f"Enviado a {destino}")
                    if ok:
                        agregar_historial(_orden, st.session_state.sector_confirmado, enviado_a=destino)
                        st.session_state.ultimo = {
                            "orden": _orden, "sector": st.session_state.sector_confirmado,
                            "op": st.session_state.op_confirmado,
                            "enviado_a": destino, "offline": err == "OFFLINE"
                        }
                        st.session_state.orden_val = ""
                        st.session_state.ord_n    += 1
                        st.session_state.reg_error = None
                        st.session_state.paso      = 2
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")

        else:
            # Pieza marcada como DVH → verificar pareja
            _par = obtener_par_dvh(_info_dvh["maestra"])
            _cara_falta = 2 if _info_dvh["cara"] == 1 else 1

            if not _par["ambas_en_dvh"]:
                _info_falta = _par.get(f"cara{_cara_falta}")
                if _info_falta is None:
                    st.error(f"⏳ Cara {_cara_falta} todavia no fue marcada como DVH en sectores anteriores.")
                else:
                    st.warning(f"⏳ Esperando Cara {_cara_falta}. Actualmente en: {_info_falta['sector_actual']}")
                st.button("🔒 DESPACHO BLOQUEADO — esperando pareja DVH",
                          disabled=True, use_container_width=True)
            else:
                # Ambas caras presentes en DVH → despacho consolidado
                _maestra  = _info_dvh["maestra"]
                _cara1    = _par["cara1"]
                _cara2    = _par["cara2"]
                st.success(f"✅ Pareja DVH completa — se consolidará la orden {_maestra}")
                st.markdown(f"""
- **Cara 1** ({_cara1['orden_pieza']}): ✅ Aqui en DVH
- **Cara 2** ({_cara2['orden_pieza']}): ✅ Aqui en DVH
""")
                st.write("")
                if st.button("🪟 CONSOLIDAR Y ENVIAR A TERMINADO", type="primary", use_container_width=True):
                    if not carro_ok:
                        st.warning("⚠️ Ingresá el número de carro.")
                    else:
                        carro = int(_carro_ef) if carro_ok else 0
                        _op   = st.session_state.op_confirmado
                        _ts   = _now_utc()
                        try:
                            with conn.session as _s:
                                for _cp_data in [_cara1, _cara2]:
                                    _s.execute(text("""
                                        INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                        VALUES (:f, :o, :c, :l, :u, 'Consolidada en DVH')
                                    """), {"f": _ts, "o": _cp_data["orden_pieza"],
                                           "c": carro, "l": lado, "u": _op})
                                _s.execute(text("""
                                    INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                                    VALUES (:f, :o, :c, :l, :u, 'Enviado a Terminado')
                                """), {"f": _ts, "o": _maestra, "c": carro, "l": lado, "u": _op})
                                _s.commit()
                            agregar_historial(_orden, "DVH", enviado_a="Terminado (DVH consolidado)")
                            st.session_state.ultimo = {
                                "orden": _maestra, "sector": "DVH",
                                "op": _op, "enviado_a": "Terminado", "offline": False
                            }
                            st.session_state.orden_val = ""
                            st.session_state.ord_n    += 1
                            st.session_state.reg_error = None
                            st.session_state.paso      = 2
                            st.rerun()
                        except Exception as _e:
                            st.error(f"❌ Error al consolidar: {_e}")

    else:
        # ── Flujo normal para todos los demás sectores ────────────────────────
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

                # Marcar / desmarcar DVH si corresponde (sectores de origen)
                if _sector_es_origen_dvh:
                    if es_dvh and cara_dvh:
                        marcar_dvh(_orden, cara_dvh, st.session_state.op_confirmado,
                                   st.session_state.sector_confirmado)
                    elif _es_dvh_actual and not es_dvh:
                        desmarcar_dvh(_orden)

                if destino == "Dañado":
                    ok, err = guardar_registro(_orden, carro, lado,
                                               st.session_state.op_confirmado, "Dañado")
                elif destino == SECTOR_TERMINADO:
                    ok, err = guardar_registro(_orden, carro, lado,
                                               st.session_state.op_confirmado, SECTOR_TERMINADO)
                else:
                    # Para Corte y Corte Laminado, las órdenes van directo a EN PROCESO (sin pasar por TOMAR)
                    if destino in ["Corte", "Corte Laminado"]:
                        ok, err = guardar_registro(_orden, carro, lado,
                                                   st.session_state.op_confirmado, f"En Proceso en {destino}")
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
