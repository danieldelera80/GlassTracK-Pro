import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image

from config import SECTORES, DB_PATH, init_db, verificar_licencia
from styles import CSS_GLOBAL, render_sb_header, render_sb_operario, render_steps, render_contexto

st.set_page_config(
    page_title="Carga de Producción",
    page_icon="📋",
    layout="centered",
)

verificar_licencia()
init_db()

st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

try:
    from pyzbar.pyzbar import decode as zbar_decode
    CAMARA_DISPONIBLE = True
except ImportError:
    CAMARA_DISPONIBLE = False

SECTOR_ENTREGA = "Entrega"


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def es_duplicado(orden: str, sector: str) -> bool:
    if not orden.strip():
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        res  = pd.read_sql_query(
            "SELECT 1 FROM registros WHERE TRIM(orden) = ? AND sector = ? LIMIT 1",
            conn, params=(orden.strip(), sector),
        )
        conn.close()
        return not res.empty
    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar duplicado: {e}")
        return False


def guardar_registro(orden: str, carro: int, lado: str, usuario: str, sector: str):
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO registros (fecha_hora, orden, carro, lado, usuario, sector)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             orden.strip(), carro, lado, usuario.strip(), sector),
        )
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


def decodificar_imagen(img_bytes) -> str | None:
    try:
        img     = Image.open(img_bytes)
        codigos = zbar_decode(img)
        if codigos:
            return codigos[0].data.decode("utf-8").strip()
        return None
    except Exception:
        return None


def procesar_orden(valor: str):
    """
    Evalúa la orden escaneada.
    - Sector normal  → va a paso 3 (carro + lado)
    - Sector Entrega → marca flag para guardar directo sin paso 3
    """
    if not valor.strip():
        return
    dup = es_duplicado(valor, st.session_state.sector_confirmado)
    st.session_state.orden_val   = valor.strip()
    st.session_state.es_dup      = dup

    if not dup:
        if st.session_state.sector_confirmado == SECTOR_ENTREGA:
            # Entrega: guardar directo, sin pedir carro ni lado
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
    "entrega_lista":     False,   # flag: guardar entrega directo
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

# Pasos del wizard según sector
def get_step_labels():
    if st.session_state.sector_confirmado == SECTOR_ENTREGA:
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
        '<div class="sb-footer">Camara Fabrica Produccion · v1.0</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  WIZARD
# ══════════════════════════════════════════════════════════════════════════════
es_entrega = st.session_state.sector_confirmado == SECTOR_ENTREGA

st.markdown("## 📋 Carga de Producción")
render_steps(st.session_state.paso, get_step_labels())

paso = st.session_state.paso

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 0 — Operario
# ─────────────────────────────────────────────────────────────────────────────
if paso == 0:
    st.markdown("### 👷 ¿Quién sos?")
    st.text_input(
        "Nombre o ID de operario", key="_inp_op", on_change=cb_operario,
        placeholder="Escribí tu nombre o escaneá tu ID...",
    )
    st.caption("Presioná Enter o usá el escáner para confirmar.")
    st.write("")
    if st.button("Confirmar →", use_container_width=True, type="primary"):
        cb_operario()
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 1 — Sector
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 1:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)
    st.markdown("### 📍 ¿En qué sector estás?")
    idx_actual = SECTORES.index(st.session_state.sector_confirmado) \
                 if st.session_state.sector_confirmado in SECTORES else 0
    sector_sel = st.selectbox("Sector", SECTORES, index=idx_actual, key="_sel_sector",
                              label_visibility="collapsed")
    st.write("")
    if st.button("Confirmar →", use_container_width=True, type="primary"):
        st.session_state.sector_confirmado = sector_sel
        st.session_state.paso = 2
        st.rerun()
    if st.button("← Volver", use_container_width=True):
        st.session_state.paso = 0
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 2 — Escanear orden
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 2:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)

    # ── Auto-guardar para Entrega ─────────────────────────────────────────────
    if st.session_state.entrega_lista:
        st.session_state.entrega_lista = False
        success, error = guardar_registro(
            st.session_state.orden_val, 0, "-",
            st.session_state.op_confirmado, SECTOR_ENTREGA,
        )
        if success:
            st.session_state.ultimo = {
                "orden":  st.session_state.orden_val,
                "sector": SECTOR_ENTREGA,
                "op":     st.session_state.op_confirmado,
            }
            st.session_state.orden_val = ""
            st.session_state.es_dup    = False
            st.session_state.ord_n    += 1
            st.session_state.reg_error = None
            st.cache_data.clear()
            st.rerun()
        else:
            st.session_state.reg_error = error

    # ── Título según sector ───────────────────────────────────────────────────
    if es_entrega:
        st.markdown("### 📦 Escaneá la orden a entregar")
        st.markdown("""
        <div style="background:#0d2a1a; border:1px solid #1a6a35; border-radius:10px;
                    padding:10px 14px; margin-bottom:16px; font-size:13px; color:#4ada75;">
            ⚡ Modo Entrega — se registra automáticamente al escanear
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("### 🔢 Escaneá la orden")

    # ── Aviso duplicado ───────────────────────────────────────────────────────
    if st.session_state.es_dup and st.session_state.orden_val:
        st.markdown(
            f'<div class="dup-box">⚠️ La orden <b>{st.session_state.orden_val}</b> '
            f'ya existe en <b>{st.session_state.sector_confirmado}</b></div>',
            unsafe_allow_html=True,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Registrar igual", use_container_width=True, type="primary"):
                st.session_state.es_dup = False
                if es_entrega:
                    # Entrega: guardar directo aunque sea duplicado
                    st.session_state.entrega_lista = True
                else:
                    st.session_state.paso = 3
                st.rerun()
        with col_b:
            if st.button("🔄 Nuevo escaneo", use_container_width=True):
                st.session_state.orden_val = ""
                st.session_state.es_dup    = False
                st.session_state.ord_n    += 1
                st.rerun()

    else:
        # ── Toggle modo escáner / cámara ──────────────────────────────────────
        if CAMARA_DISPONIBLE:
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
                ):
                    st.session_state.modo_camara = True
                    st.rerun()
            st.write("")

        # ── Modo texto ────────────────────────────────────────────────────────
        if not st.session_state.modo_camara or not CAMARA_DISPONIBLE:
            ord_key = f"_inp_ord_{st.session_state.ord_n}"
            st.text_input(
                "Número de Orden", key=ord_key, on_change=cb_orden,
                placeholder="Apuntá el escáner acá...",
            )
            if es_entrega:
                st.caption("✅ Al escanear se registra y entrega automáticamente.")
            else:
                st.caption("Avanza automáticamente al presionar Enter.")

        # ── Modo cámara ───────────────────────────────────────────────────────
        else:
            st.info("📱 Apuntá la cámara al código y tomá la foto.")
            foto = st.camera_input(
                "Capturar", key=f"_cam_{st.session_state.ord_n}",
                label_visibility="collapsed",
            )
            if foto is not None:
                codigo = decodificar_imagen(foto)
                if codigo:
                    st.success(f"✅ Código detectado: **{codigo}**")
                    procesar_orden(codigo)
                    st.session_state.ord_n += 1
                    st.rerun()
                else:
                    st.error("❌ No se detectó código. Intentá con mejor luz o más cerca.")
                    st.session_state.ord_n += 1
                    st.rerun()

        st.write("")
        if st.button("← Cambiar sector", use_container_width=True):
            st.session_state.paso = 1
            st.rerun()

    # ── Error de guardado ─────────────────────────────────────────────────────
    if st.session_state.reg_error:
        st.error(f"❌ Error al guardar: {st.session_state.reg_error}")

    # ── Panel éxito del registro anterior ─────────────────────────────────────
    if st.session_state.ultimo:
        u = st.session_state.ultimo
        icono  = "📦" if u["sector"] == SECTOR_ENTREGA else "✅"
        titulo = "¡Entregado!" if u["sector"] == SECTOR_ENTREGA else "¡Registrado!"
        st.markdown(f"""
        <div class="success-panel">
            <div style="font-size:44px;">{icono}</div>
            <div style="font-size:19px; font-weight:800; margin:8px 0;">{titulo}</div>
            <div style="font-size:14px; opacity:.85;">
                Orden <b>{u['orden']}</b> · {u['sector']}
            </div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  PASO 3 — Carro + Lado (solo sectores de producción, nunca Entrega)
# ─────────────────────────────────────────────────────────────────────────────
elif paso == 3:
    render_contexto(st.session_state.op_confirmado, st.session_state.sector_confirmado)

    st.markdown(f"""
    <div style="background:#0d1f3c; border:1px solid #1e3a6a; border-radius:12px;
                padding:14px 18px; margin-bottom:20px; text-align:center;">
        <div style="font-size:12px; color:#4a6a9a; text-transform:uppercase;
                    letter-spacing:1.5px; margin-bottom:4px;">Orden detectada</div>
        <div style="font-size:28px; font-weight:900; color:#4a90d9; letter-spacing:2px;">
            {st.session_state.orden_val}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_car, col_lad = st.columns(2)
    with col_car:
        st.markdown("**🛒 Carro**")
        carro = st.number_input("Carro", min_value=1, value=1,
                                key="_inp_carro", label_visibility="collapsed")
    with col_lad:
        st.markdown("**↔️ Lado**")
        lado = st.selectbox("Lado", ["A", "B"],
                            key="_sel_lado", label_visibility="collapsed")

    st.write("")

    if st.button("💾 REGISTRAR", type="primary", use_container_width=True):
        success, error = guardar_registro(
            st.session_state.orden_val, carro, lado,
            st.session_state.op_confirmado,
            st.session_state.sector_confirmado,
        )
        if success:
            st.session_state.ultimo = {
                "orden":  st.session_state.orden_val,
                "sector": st.session_state.sector_confirmado,
                "op":     st.session_state.op_confirmado,
            }
            st.session_state.orden_val = ""
            st.session_state.es_dup    = False
            st.session_state.ord_n    += 1
            st.session_state.reg_error = None
            st.session_state.paso      = 2
            st.cache_data.clear()
            st.rerun()
        else:
            st.session_state.reg_error = error

    if st.session_state.reg_error:
        st.error(f"❌ Error al guardar: {st.session_state.reg_error}")

    st.write("")
    if st.button("← Volver a escanear", use_container_width=True):
        st.session_state.orden_val = ""
        st.session_state.es_dup    = False
        st.session_state.ord_n    += 1
        st.session_state.paso      = 2
        st.rerun()
