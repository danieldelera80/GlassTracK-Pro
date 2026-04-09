import re
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
import csv
from pathlib import Path

from config import SECTORES, SECTORES_ESCANEO_DIRECTO, verificar_licencia, get_connection, verificar_estado_sistema
from styles import CSS_GLOBAL, render_sb_header, render_sb_operario, render_steps, render_contexto

st.set_page_config(page_title="Carga de Producción", page_icon="📋", layout="centered")


verificar_licencia()
verificar_estado_sistema()
conn = get_connection()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_DISPONIBLE = True
except ImportError:
    PYZBAR_DISPONIBLE = False

# Cámara siempre disponible (la foto se usa como referencia visual)
CAMARA_DISPONIBLE = True

SECTOR_ENTREGA = "Entrega"
SECTOR_TERMINADO = "Terminado"

# ── Utilidad: normalizar prefijos [URGENTE]/[INCIDENCIA] ─────────────────────
_PFX_RE = re.compile(r'^\s*\[(URGENTE|INCIDENCIA)\]\s*', re.IGNORECASE)

def _normalizar_df_ordenes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Unifica 'orden' y '[URGENTE] orden' como el mismo pedido físico:
    - Extrae el número base quitando prefijos
    - Si algún registro tiene [URGENTE], todos adoptan ese prefijo
    - Dedup por nombre normalizado, conservando el registro más reciente
    """
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
#  BASE DE DATOS (NEON)
# ══════════════════════════════════════════════════════════════════════════════

OFFLINE_FILE = Path(__file__).parent.parent / "offline_records.csv"

def guardar_registro_offline(orden: str, carro: int, lado: str, usuario: str, sector: str):
    """Guarda el registro en un CSV local cuando no hay conexión a Neon."""
    file_exists = OFFLINE_FILE.exists()
    try:
        with open(OFFLINE_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["fecha_hora", "orden", "carro", "lado", "usuario", "sector"])
            writer.writerow([datetime.now().isoformat(), orden.strip(), carro, lado, usuario.strip(), sector])
        return True
    except Exception as e:
        print(f"Error escribiendo offline: {e}")
        return False

def guardar_registro(orden: str, carro: int, lado: str, usuario: str, sector: str):
    import time
    for intento in range(3):  # hasta 3 reintentos
        try:
            with conn.session as s:
                s.execute(text("""
                    INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
                    VALUES (:f, :o, :c, :l, :u, :s)
                """), {
                    "f": datetime.now(), "o": orden.strip(), "c": carro,
                    "l": lado, "u": usuario.strip(), "s": sector
                })
                s.commit()
            return True, None
        except Exception as e:
            if intento < 2:
                time.sleep(2)  # espera 2 segundos y reintenta
            else:
                if guardar_registro_offline(orden, carro, lado, usuario, sector):
                    return True, "OFFLINE"
                else:
                    return False, str(e)


def obtener_activos(sector_actual: str):
    """Consulta la DB para obtener órdenes 'Enviadas a' y 'En Proceso en' de forma eficiente."""
    try:
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros ORDER BY fecha_hora DESC"
        with conn.session as s:
            df = pd.read_sql(text(query), s.connection())
        if df.empty: return [], []

        # Normalizar: unifica "22" y "[URGENTE] 22" → 1 fila por pedido real
        df = _normalizar_df_ordenes(df)

        # Pendientes de recibir (Panel A)
        mask_in  = df["sector"].str.strip() == f"Enviado a {sector_actual}"
        res_in   = df[mask_in].copy()
        res_in["fecha_hora"] = res_in["fecha_hora"].dt.strftime("%Y-%m-%d %H:%M")

        # Ya recibidas / En proceso (Panel B)
        mask_pro = df["sector"].str.strip() == f"En Proceso en {sector_actual}"
        res_pro  = df[mask_pro].copy()
        res_pro["fecha_hora"] = res_pro["fecha_hora"].dt.strftime("%Y-%m-%d %H:%M")

        return res_in.to_dict("records"), res_pro.to_dict("records")
    except Exception as e:
        print(f"Error obtener_activos: {e}")
        return [], []

def obtener_pendientes_entrega():
    """Obtiene las órdenes que ya pasaron por Terminado y esperan entrega al cliente."""
    try:
        query = "SELECT orden, carro, lado, sector, usuario, fecha_hora FROM registros ORDER BY fecha_hora DESC"
        with conn.session as s:
            df = pd.read_sql(text(query), s.connection())
        if df.empty: return []

        # Normalizar: unifica versiones con/sin prefijo
        df = _normalizar_df_ordenes(df)

        mask = (df["sector"].str.strip() == SECTOR_TERMINADO) | (df["sector"].str.strip() == f"Enviado a {SECTOR_ENTREGA}")
        res  = df[mask].copy()
        res["fecha_hora"] = res["fecha_hora"].dt.strftime("%Y-%m-%d %H:%M")
        return res.to_dict("records")
    except Exception as e:
        print(f"Error obtener_pendientes_entrega: {e}")
        return []


def resolver_nombre_orden(orden_base: str) -> str:
    """Verifica si la orden ya existe en el sistema y, de ser así, le auto-asigna un sub-índice."""
    try:
        # Buscamos todas las órdenes que sean exactamente 'orden_base' o que empiecen con 'orden_base - '
        query = f"SELECT DISTINCT orden FROM registros WHERE orden = '{orden_base}' OR orden LIKE '{orden_base} - %'"
        df = conn.query(query, ttl=0)
        
        if df.empty:
            return orden_base  # Es la primera de su especie
            
        # Si ya existen, contamos cuántas hay y generamos la siguiente en la saga
        cantidad = len(df)
        return f"{orden_base} - {cantidad + 1}"
    except Exception as e:
        print(f"Error al resolver nombre de orden: {e}")
        return orden_base


def decodificar_imagen(img_bytes) -> str | None:
    """Intenta decodificar un código de barras con pyzbar (si está disponible)."""
    if not PYZBAR_DISPONIBLE:
        return None
    try:
        from PIL import Image as PILImage
        img     = PILImage.open(img_bytes)
        codigos = zbar_decode(img)
        if codigos:
            return codigos[0].data.decode("utf-8").strip()
        return None
    except Exception:
        return None


def obtener_carro_lado(orden: str):
    """Retorna (carro, lado) del último registro de la orden, o (0, 'A') si no hay datos."""
    try:
        df = conn.query(
            "SELECT carro, lado FROM registros WHERE TRIM(orden) = :ord ORDER BY fecha_hora DESC LIMIT 1",
            params={"ord": orden.strip()}, ttl=0
        )
        if not df.empty:
            return int(df.iloc[0]["carro"] or 0), str(df.iloc[0]["lado"] or "A")
    except:
        pass
    return 0, "A"


def procesar_orden(valor: str):
    """Evalúa la orden, genera sub-piezas si es necesario, y avanza al paso siguiente."""
    if not valor.strip():
        return

    orden_limpia  = valor.strip()
    orden_resuelta = resolver_nombre_orden(orden_limpia)

    st.session_state.orden_val = orden_resuelta

    # Pre-cargar Carro y Lado del sector anterior (si existen)
    carro_p, lado_p = obtener_carro_lado(orden_resuelta)
    st.session_state.carro_previo  = carro_p
    st.session_state.lado_previo   = lado_p
    st.session_state.paso3_fresh   = True   # señal para pre-llenar widgets

    if st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO:
        st.session_state.entrega_lista = True
    else:
        st.session_state.paso = 3


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "paso":              0,
    "op_confirmado":     "",
    "sector_confirmado": SECTORES[0],
    "orden_val":         "",
    "es_dup":            False,
    "ord_n":             0,
    "reg_error":         None,
    "ultimo":            None,
    "modo_camara":       False,
    "entrega_lista":     False,
    "ir_a_terminado":    False,
    "ir_a_danado":       False,
    "carro_previo":      0,
    "lado_previo":       "A",
    "paso3_fresh":       False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def cb_operario():
    val = st.session_state.get("_inp_op", "").strip()
    if val:
        st.session_state.op_confirmado = val
        st.session_state.paso = 1


def cb_orden():
    key = f"_inp_ord_{st.session_state.ord_n}"
    val = st.session_state.get(key, "").strip()
    procesar_orden(val)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def get_step_labels():
    if st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO:
        return ["Operario", "Sector", "Escanear"]
    return ["Operario", "Sector", "Orden", "Confirmar"]


with st.sidebar:
    render_sb_header()
    if st.session_state.op_confirmado:
        render_sb_operario(
            st.session_state.op_confirmado,
            st.session_state.sector_confirmado,
        )
        if st.button("🔄 Cambiar operario", use_container_width=True):
            st.session_state.paso          = 0
            st.session_state.op_confirmado = ""
            st.session_state.orden_val     = ""
            st.session_state.es_dup        = False
            st.session_state.entrega_lista = False
            st.rerun()
    else:
        st.caption("Iniciá sesión para comenzar a cargar.")
    st.divider()
    if st.button("🏠 Inicio", use_container_width=True):
        st.switch_page("main.py")
    st.markdown(
        '<div class="sb-footer">Control de Produccion · v1.0</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  WIZARD
# ══════════════════════════════════════════════════════════════════════════════
es_escaneo_directo = st.session_state.sector_confirmado in SECTORES_ESCANEO_DIRECTO
es_entrega = st.session_state.sector_confirmado == SECTOR_ENTREGA
es_terminado = st.session_state.sector_confirmado == SECTOR_TERMINADO

render_steps(st.session_state.paso, get_step_labels())

# ── Alerta de órdenes urgentes activas (filtrada por sector del operario) ─────
# Solo visible cuando el operario ya confirmó su sector (paso >= 2)
if st.session_state.paso >= 2:
    try:
        _sector_op = st.session_state.sector_confirmado
        # Sectores que "pertenecen" al operario actual:
        # la orden está en su sector exacto, en proceso en él, o fue enviada a él
        _sectores_visibles = {
            _sector_op,
            f"En Proceso en {_sector_op}",
            f"Enviado a {_sector_op}",
        }
        _df_urg_sector = conn.query(
            "SELECT DISTINCT ON (orden) orden, sector FROM registros "
            "WHERE orden ILIKE '%[URGENTE]%' ORDER BY orden, fecha_hora DESC",
            ttl=30
        )
        if _df_urg_sector is not None and not _df_urg_sector.empty:
            # Filtrar: solo órdenes cuyo sector actual pertenece a este operario
            _df_urg_sector = _df_urg_sector[
                _df_urg_sector["sector"].str.strip().isin(_sectores_visibles)
            ]
            for _, _urg_row in _df_urg_sector.iterrows():
                _urg_orden = _urg_row["orden"]
                _urg_sector = _urg_row["sector"].strip()
                st.markdown(f"""
                <div class="alerta-urgente">
                    <span style="font-size:28px; flex-shrink:0;">🚨</span>
                    <div>
                        <div class="alerta-urgente-titulo">⚡ Prioridad Urgente Activa</div>
                        <div class="alerta-urgente-ordenes">{_urg_orden}</div>
                        <div style="font-size:12px; color:#fca5a5; margin-top:4px;">
                            📍 Sector actual: <b>{_urg_sector}</b>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass  # Si falla la consulta, no interrumpir el flujo del formulario

paso = st.session_state.paso

# ──────────────────────────────────────────────────────────────────────────────
#  PASO 0 — Operario
# ──────────────────────────────────────────────────────────────────────────────
if paso == 0:
    st.markdown("### 👷 ¿Quién sos?")
    st.text_input(
        "Nombre o ID de operario", key="_inp_op", on_change=cb_operario,
        placeholder="Escribí tu nombre o escaneá tu ID...",
    )
    st.caption("Presioná Enter o usá el escáner para confirmar.")
    st.write("")
    if st.button("Confirmar →", key="btn_confirmar_op", use_container_width=True, type="primary"):
        cb_operario()
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
#  PASO 1 — Sector
# ──────────────────────────────────────────────────────────────────────────────
elif paso == 1:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)
    st.markdown("### 📍 ¿En qué sector estás?")
    idx_actual = SECTORES.index(st.session_state.sector_confirmado) \
                 if st.session_state.sector_confirmado in SECTORES else 0
    sector_sel = st.selectbox("Sector", SECTORES, index=idx_actual, key="_sel_sector",
                              label_visibility="collapsed")
    st.write("")
    if st.button("Confirmar →", key="btn_confirmar_sec", use_container_width=True, type="primary"):
        st.session_state.sector_confirmado = sector_sel
        st.session_state.paso = 2
        st.rerun()
    if st.button("← Volver", key="btn_volver_sec", use_container_width=True):
        st.session_state.paso = 0
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
#  PASO 2 — Escanear orden
# ──────────────────────────────────────────────────────────────────────────────
elif paso == 2:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)

    # ── Auto-guardar para Entrega / Terminado ──────────────────────────────────
    if st.session_state.entrega_lista:
        st.session_state.entrega_lista = False
        success, error = guardar_registro(
            st.session_state.orden_val, 0, "-",
            st.session_state.op_confirmado, st.session_state.sector_confirmado,
        )
        if success:
            st.session_state.ultimo = {
                "orden":  st.session_state.orden_val,
                "sector": st.session_state.sector_confirmado,
                "op":     st.session_state.op_confirmado,
                "offline": error == "OFFLINE"
            }
            st.session_state.orden_val = ""
            st.session_state.es_dup    = False
            st.session_state.ord_n    += 1
            st.session_state.reg_error = None
            st.rerun()
        else:
            st.session_state.reg_error = error

    # ── Título según sector ──────────────────────────────────────────────────
    if es_terminado:
        st.markdown("### ⏳ Escaneá la orden terminada")
        st.markdown("""
        <div style="background:#1a1500; border:1px solid #7a6000; border-radius:10px;
                    padding:10px 14px; margin-bottom:16px; font-size:13px; color:#f0c040;">
            ⏳ Modo Terminado — el producto queda en espera de entrega
        </div>
        """, unsafe_allow_html=True)
    elif es_entrega:
        st.markdown("### 📦 Escaneá la orden a entregar")
        st.markdown("""
        <div style="background:#0d2a1a; border:1px solid #1a6a35; border-radius:10px;
                    padding:10px 14px; margin-bottom:16px; font-size:13px; color:#4ada75;">
            ⚡ Modo Entrega — se registra automáticamente al escanear
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 🔢 Escaneá la orden")

    # ── Toggle modo escáner / cámara ────────────────────────────────────────
    col_t, col_c = st.columns(2)
    with col_t:
        if st.button(
            "⌨️ Escáner / Teclado", use_container_width=True,
            type="primary" if not st.session_state.modo_camara else "secondary",
        ):
            st.session_state.modo_camara = False
            st.session_state.ord_n += 1
            st.rerun()
    with col_c:
        if st.button(
            "📷 Cámara", use_container_width=True,
            type="primary" if st.session_state.modo_camara else "secondary",
            disabled=not CAMARA_DISPONIBLE,
        ):
            st.session_state.modo_camara = True
            st.rerun()
    st.write("")

    # ── Modo texto ───────────────────────────────────────────────────────────
    if not st.session_state.modo_camara:
        ord_key = f"_inp_ord_{st.session_state.ord_n}"
        st.text_input(
            "Número de Orden", key=ord_key, on_change=cb_orden,
            placeholder="Apuntá el escáner acá...",
        )
        if es_terminado:
            st.caption("⏳ Al escanear se marca como Terminado automáticamente.")
        elif es_entrega:
            st.caption("✅ Al escanear se registra y entrega automáticamente.")
        else:
            st.caption("Avanza automáticamente al presionar Enter.")

    # ── Modo cámara: foto + entrada manual del código visible ────────────
    else:
        st.caption("📸 Sacá foto a la etiqueta y escribí el número que ves.")
        foto = st.camera_input(
            "Capturar etiqueta",
            key=f"_cam_{st.session_state.ord_n}",
            label_visibility="collapsed",
        )
        if foto is not None:
            codigo_auto = decodificar_imagen(foto)
            if codigo_auto:
                st.success(f"✅ Código detectado: **{codigo_auto}**")
                procesar_orden(codigo_auto)
                st.session_state.ord_n += 1
                st.rerun()
            else:
                st.markdown(
                    '<div style="font-size:13px;color:#f0c040;margin-bottom:6px;">'
                    '👀 Mirá el número en la etiqueta e ingresálo:'
                    '</div>',
                    unsafe_allow_html=True,
                )
                cod_manual = st.text_input(
                    "Código de la etiqueta",
                    key=f"_cam_manual_{st.session_state.ord_n}",
                    placeholder="Ej: 65365-3",
                    label_visibility="collapsed",
                )
                if st.button("✅ Confirmar código", use_container_width=True, type="primary",
                             key=f"_cam_ok_{st.session_state.ord_n}"):
                    if cod_manual.strip():
                        procesar_orden(cod_manual.strip())
                        st.session_state.ord_n += 1
                        st.rerun()
                    else:
                        st.warning("⚠️ Ingresá el código antes de confirmar.")
                if st.button("🔄 Sacar otra foto", use_container_width=True,
                             key=f"_cam_retry_{st.session_state.ord_n}"):
                    st.session_state.ord_n += 1
                    st.rerun()

    st.write("")
    if st.button("← Cambiar sector", use_container_width=True):
        st.session_state.paso = 1
        st.rerun()

    # ── Error de guardado ──────────────────────────────────────────────────
    if st.session_state.reg_error:
        st.error(f"❌ Error al guardar: {st.session_state.reg_error}")

    # ── Panel éxito del registro anterior ─────────────────────────────────────────
    if st.session_state.ultimo:
        u = st.session_state.ultimo
        if u["sector"] == SECTOR_ENTREGA:
            icono, titulo = "📦", "¡Entregado!"
        elif u["sector"] == SECTOR_TERMINADO:
            icono, titulo = "⏳", "¡Terminado!"
        else:
            icono, titulo = "✅", "¡Registrado!"

        extra = ""
        envio = u.get("enviado_a")
        if envio:
            if envio == "Dañado":
                extra = '<div style="font-size:13px; color:#ff8a8a; margin-top:6px;">⚠️ Marcado como Dañado</div>'
            elif envio == SECTOR_TERMINADO:
                extra = '<div style="font-size:13px; color:#f0c040; margin-top:8px;">⏳ Enviado a Terminado</div>'
            else:
                extra = f'<div style="font-size:13px; color:#4ade80; margin-top:8px;">📤 Enviado a: {envio}</div>'
                
        if u.get("offline"):
            extra += '<div style="font-size:14px; font-weight:bold; color:#f97316; margin-top:10px; border: 1px solid #f97316; padding: 6px; border-radius: 6px; text-align:center;">⚠️ Guardado en Caché Local (Sin Internet)</div>'

        st.markdown(f"""
        <div class="success-panel">
            <div style="font-size:44px;">{icono}</div>
            <div style="font-size:19px; font-weight:800; margin:8px 0;">{titulo}</div>
            <div style="font-size:14px; opacity:.85;">
                Orden <b>{u['orden']}</b> · {u['sector']}
            </div>
            {extra}
        </div>""", unsafe_allow_html=True)
        
        # Emitir el BEEP sonoro de éxito de forma oculta
        beep_path = Path(__file__).parent.parent / "beep.wav"
        if beep_path.exists():
            import base64
            with open(beep_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay="true" style="display:none;"><source src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>', unsafe_allow_html=True)


    # ── TABLERO KANBAN DE PLANTA ────────────────────────────────────────────
    st.markdown("<hr style='margin: 30px 0 20px 0; border: 1px dashed #334155;'>", unsafe_allow_html=True)

    if not es_terminado and not es_entrega:
        entrantes, en_proceso = obtener_activos(st.session_state.sector_confirmado)
        
        tab_pendientes, tab_proceso = st.tabs([
            f"📥 PENDIENTES ({len(entrantes)})", 
            f"⚙️ EN PROCESO ({len(en_proceso)})"
        ])
        
        # PANEL A: PENDIENTES DE RECIBIR
        with tab_pendientes:
            if not entrantes:
                st.info("No hay órdenes entrantes.")
            else:
                for row in entrantes:
                    _es_urgente = "[URGENTE]" in str(row['orden']).upper()
                    _bg   = "#2d0a0a" if _es_urgente else "#1e293b"
                    _bord = "#ef4444" if _es_urgente else "#3b82f6"
                    _badge = ' <span style="background:#ef4444;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;font-weight:bold;margin-left:6px;">⚡ URGENTE</span>' if _es_urgente else ""
                    with st.container():
                        st.markdown(f"""
                        <div style="background:{_bg}; border-left:4px solid {_bord}; border-radius:6px; padding:12px; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:start;">
                                <span style="font-size:18px; font-weight:bold; color:#60a5fa;">📄 {row['orden']}{_badge}</span>
                                <span style="font-size:13px; color:#cbd5e1; background:#0f172a; padding:2px 6px; border-radius:4px;">🛒 {row['carro']} | ↔️ {row['lado']}</span>
                            </div>
                            <div style="font-size:12px; color:#94a3b8; margin-top:6px;">Enviado por: {row['usuario']} — {row['fecha_hora']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"↘️ TOMAR PIEZA {row['orden']}", key=f"rec_{row['orden']}", use_container_width=True):
                            success, error = guardar_registro(
                                row['orden'], row.get('carro', 0), row.get('lado', '-'), 
                                st.session_state.op_confirmado, 
                                f"En Proceso en {st.session_state.sector_confirmado}"
                            )
                            if success:
                                if error == "OFFLINE":
                                    st.warning("Guardado en Caché Local ⚠️")
                                else:
                                    st.success(f"¡Orden {row['orden']} recibida!")
                                st.rerun()
                            else:
                                st.error(error)
                
        # PANEL B: EN PROCESO (Listas para finalizar)
        with tab_proceso:
            if not en_proceso:
                st.info("No tenés piezas en tu mesa.")
            else:
                for row in en_proceso:
                    _es_urgente = "[URGENTE]" in str(row['orden']).upper()
                    _bg   = "#2d0a0a" if _es_urgente else "#1f1605"
                    _bord = "#ef4444" if _es_urgente else "#eab308"
                    _badge = ' <span style="background:#ef4444;color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;font-weight:bold;margin-left:6px;">⚡ URGENTE</span>' if _es_urgente else ""
                    with st.container():
                        st.markdown(f"""
                        <div style="background:{_bg}; border-left:4px solid {_bord}; border-radius:6px; padding:12px; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:start;">
                                <span style="font-size:18px; font-weight:bold; color:#facc15;">⚙️ {row['orden']}{_badge}</span>
                                <span style="font-size:13px; color:#fde047; background:#422006; padding:2px 6px; border-radius:4px;">🛒 {row['carro']} | ↔️ {row['lado']}</span>
                            </div>
                            <div style="font-size:12px; color:#a1a1aa; margin-top:6px;">Iniciado el: {row['fecha_hora']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"📤 DESPACHAR {row['orden']}", key=f"fin_{row['orden']}", use_container_width=True):
                            st.session_state.orden_val    = row['orden']
                            st.session_state.carro_previo = int(row.get('carro') or 0)
                            st.session_state.lado_previo  = str(row.get('lado') or 'A')
                            st.session_state.paso3_fresh  = True
                            st.session_state.paso         = 3
                            st.rerun()
                            


    # ── KANBAN DE ENTREGA ───────────────────────────────────────────────────
    if es_entrega:
        pendientes_entrega = obtener_pendientes_entrega()
        st.markdown(f"#### 📥 LISTAS PARA ENTREGAR ({len(pendientes_entrega)})")
        if not pendientes_entrega:
            st.info("No hay productos terminados esperando entrega.")
        else:
            for row in pendientes_entrega:
                with st.container():
                    col_info, col_btn = st.columns([7.5, 2.5])
                    with col_info:
                        st.markdown(f"""
                        <div style="background:#0d2a1a; border-left:4px solid #4ada75; border-radius:6px; padding:0 10px; display:flex; justify-content:space-between; align-items:center; height:43px;">
                            <div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                                <span style="font-size:16px; font-weight:bold; color:#4ada75; margin-right:8px;">📦 {row['orden']}</span>
                                <span style="font-size:12px; color:#86efac; opacity:0.9;">por {row['usuario']} — {row['fecha_hora']}</span>
                            </div>
                            <span style="font-size:12px; color:#a7f3d0; background:#064e3b; padding:2px 6px; border-radius:4px; margin-left:10px; white-space:nowrap;">🛒 {row['carro']}  |  ↔️ {row['lado']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_btn:
                        if st.button("🚀 ENTREGAR", key=f"ent_{row['orden']}", use_container_width=True):
                            st.session_state.orden_val = row['orden']
                            st.session_state.entrega_lista = True
                            st.rerun()



# ──────────────────────────────────────────────────────────────────────────────
#  PASO 3 — Carro + Lado (solo sectores de producción, nunca Entrega)
# ──────────────────────────────────────────────────────────────────────────────
elif paso == 3:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)

    # ── Pre-llenar widgets con datos del sector anterior (solo al entrar) ──
    _LADOS = ["A", "B", "Ambos"]
    if st.session_state.get("paso3_fresh", False):
        _cp_init = st.session_state.carro_previo
        _lp_init = st.session_state.lado_previo if st.session_state.lado_previo in _LADOS else "A"
        # Pre-llenar la sección DESPACHAR (keys fijas _d)
        st.session_state["_inp_carro_d"] = str(_cp_init) if _cp_init > 0 else ""
        st.session_state["_sel_lado_d"]  = _lp_init
        st.session_state.paso3_fresh     = False

    # ── Badge de orden ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#0d1f3c; border:1px solid #1e3a6a; border-radius:12px;
                padding:14px 18px; margin-bottom:16px; text-align:center;">
        <div style="font-size:12px; color:#4a6a9a; text-transform:uppercase;
                    letter-spacing:1.5px; margin-bottom:4px;">Orden detectada</div>
        <div style="font-size:28px; font-weight:900; color:#4a90d9; letter-spacing:2px;">
            {st.session_state.orden_val}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Panel informativo: datos que vienen del sector anterior ────────────
    _cp = st.session_state.carro_previo
    _lp = st.session_state.lado_previo
    tiene_datos_previos = _cp > 0

    if tiene_datos_previos:
        st.markdown(f"""
        <div style="background:#0f2336; border-left:4px solid #3b82f6; border-radius:8px;
                    padding:10px 16px; margin-bottom:16px; display:flex; align-items:center; gap:16px;">
            <span style="font-size:22px;">📦</span>
            <div>
                <div style="font-size:11px; color:#4a6a9a; text-transform:uppercase;
                            letter-spacing:1px;">Datos del sector anterior</div>
                <div style="font-size:18px; font-weight:700; color:#93c5fd; margin-top:2px;">
                    🛒 Carro {_cp} &nbsp;·&nbsp; ↔️ Lado {_lp}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Verificar si la pieza ya fue tomada en este sector ─────────────────
    pieza_ya_tomada = False
    try:
        res_chk = conn.query(
            "SELECT sector FROM registros WHERE TRIM(orden) = :ord ORDER BY fecha_hora DESC LIMIT 1",
            params={"ord": st.session_state.orden_val.strip()}, ttl=0
        )
        if not res_chk.empty:
            if res_chk.iloc[0]["sector"].strip() == f"En Proceso en {st.session_state.sector_confirmado}":
                pieza_ya_tomada = True
    except: pass

    st.write("")

    # ── ACCIÓN 1: TOMAR PIEZA ───────────────────────────────────────────────
    if not pieza_ya_tomada:
        st.markdown("#### 1. Iniciar Trabajo")

        if tiene_datos_previos:
            # 1 solo click — usa automáticamente los datos del sector anterior
            st.caption(f"Se usará Carro {_cp} · Lado {_lp} (del sector anterior).")
            if st.button("↘️ TOMAR PIEZA", type="secondary", use_container_width=True, key="btn_tomar_prev"):
                success, error = guardar_registro(
                    st.session_state.orden_val, _cp, _lp,
                    st.session_state.op_confirmado,
                    f"En Proceso en {st.session_state.sector_confirmado}"
                )
                if success:
                    st.session_state.ultimo = {
                        "orden": st.session_state.orden_val, "sector": st.session_state.sector_confirmado,
                        "op": st.session_state.op_confirmado, "enviado_a": None, "offline": (error == "OFFLINE")
                    }
                    st.session_state.orden_val = ""; st.session_state.es_dup = False
                    st.session_state.ord_n += 1; st.session_state.reg_error = None
                    st.session_state.paso = 2
                    st.rerun()
                else:
                    st.session_state.reg_error = error
        else:
            # Orden nueva — pedir carro/lado (keys fijas _inp_carro_t / _sel_lado_t)
            col_car_t, col_lad_t = st.columns(2)
            with col_car_t:
                st.markdown("**🛒 Carro**")
                carro_str_t = st.text_input("Carro", key="_inp_carro_t",
                    placeholder="Número de carro...", label_visibility="collapsed")
                carro_valido_t = carro_str_t.strip().isdigit() and int(carro_str_t.strip()) >= 1
                if carro_str_t.strip() and not carro_valido_t:
                    st.caption("⚠️ Ingresá un número válido")
            with col_lad_t:
                st.markdown("**↔️ Lado**")
                lado_t = st.selectbox("Lado", _LADOS, key="_sel_lado_t", label_visibility="collapsed")
            if st.button("↘️ TOMAR PIEZA", type="secondary", use_container_width=True, key="btn_tomar_nuevo"):
                if not carro_valido_t:
                    st.warning("⚠️ Ingresá el número de carro.")
                else:
                    success, error = guardar_registro(
                        st.session_state.orden_val, int(carro_str_t.strip()), lado_t,
                        st.session_state.op_confirmado,
                        f"En Proceso en {st.session_state.sector_confirmado}"
                    )
                    if success:
                        st.session_state.ultimo = {
                            "orden": st.session_state.orden_val, "sector": st.session_state.sector_confirmado,
                            "op": st.session_state.op_confirmado, "enviado_a": None, "offline": (error == "OFFLINE")
                        }
                        st.session_state.orden_val = ""; st.session_state.es_dup = False
                        st.session_state.ord_n += 1; st.session_state.reg_error = None
                        st.session_state.paso = 2
                        st.rerun()
                    else:
                        st.session_state.reg_error = error

        st.markdown("<hr style='margin: 20px 0; border: 1px dashed #334155;'>", unsafe_allow_html=True)

    # ── ACCIÓN 2: DESPACHAR — keys siempre fijas _inp_carro_d / _sel_lado_d ──
    titulo_acc2 = "Despachar Pieza" if pieza_ya_tomada else "2. Despachar Pieza (Finalizar)"
    st.markdown(f"#### {titulo_acc2}")

    col_car, col_lad = st.columns(2)
    with col_car:
        st.markdown("**🛒 Carro**")
        carro_str = st.text_input("Carro", key="_inp_carro_d",
            placeholder="Número de carro...", label_visibility="collapsed")
        # Si el campo está vacío, usar el valor previo como fallback
        _carro_efectivo = carro_str.strip() if carro_str.strip() else (str(_cp) if _cp > 0 else "")
        carro_valido = _carro_efectivo.isdigit() and int(_carro_efectivo) >= 1
        if carro_str.strip() and not carro_valido:
            st.caption("⚠️ Ingresá un número válido")
    with col_lad:
        st.markdown("**↔️ Lado**")
        lado = st.selectbox("Lado", _LADOS, key="_sel_lado_d", label_visibility="collapsed")

    opciones_destino = [
        s for s in SECTORES
        if s != st.session_state.sector_confirmado and s not in [SECTOR_ENTREGA, SECTOR_TERMINADO]
    ] + [SECTOR_TERMINADO, "Dañado"]

    destino_sel = st.selectbox("Elegir a quién enviarlo:", opciones_destino, key="_sel_destino")

    if st.button("📤 FINALIZAR Y ENVIAR", type="primary", use_container_width=True):
        if not carro_valido:
            st.warning("⚠️ Ingresá el número de carro antes de enviar.")
        else:
            carro = int(_carro_efectivo)
            if not pieza_ya_tomada:
                success, error = guardar_registro(
                    st.session_state.orden_val, carro, lado,
                    st.session_state.op_confirmado,
                    f"En Proceso en {st.session_state.sector_confirmado}"
                )
            else:
                success, error = True, None

            if success:
                es_offline = (error == "OFFLINE")
                if destino_sel == "Dañado":
                    _, err_d = guardar_registro(st.session_state.orden_val, carro, lado, st.session_state.op_confirmado, "Dañado")
                    if err_d == "OFFLINE": es_offline = True
                elif destino_sel == SECTOR_TERMINADO:
                    _, err_t = guardar_registro(st.session_state.orden_val, 0, "-", st.session_state.op_confirmado, SECTOR_TERMINADO)
                    if err_t == "OFFLINE": es_offline = True
                else:
                    _, err_n = guardar_registro(st.session_state.orden_val, carro, lado, st.session_state.op_confirmado, f"Enviado a {destino_sel}")
                    if err_n == "OFFLINE": es_offline = True

                st.session_state.ultimo = {
                    "orden": st.session_state.orden_val, "sector": st.session_state.sector_confirmado,
                    "op": st.session_state.op_confirmado, "enviado_a": destino_sel, "offline": es_offline
                }
                st.session_state.orden_val = ""; st.session_state.es_dup = False
                st.session_state.ord_n += 1; st.session_state.reg_error = None
                st.session_state.paso = 2
                st.rerun()
            else:
                st.session_state.reg_error = error

    if st.session_state.reg_error:
        st.error(f"❌ Error al guardar: {st.session_state.reg_error}")

    st.write("")
    if st.button("← Volver a escanear", use_container_width=True):
        st.session_state.orden_val = ""; st.session_state.es_dup = False
        st.session_state.ord_n += 1; st.session_state.paso = 2
        st.rerun()