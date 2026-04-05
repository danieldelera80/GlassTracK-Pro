"""
config.py — Configuración compartida entre todas las páginas.
"""
import sqlite3
import streamlit as st
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  🔒 CONTROL DE LICENCIA — editá solo esta sección
# ══════════════════════════════════════════════════════════════════════════════

BLOQUEADO: bool = False
FECHA_LIMITE: datetime = datetime(2026, 12, 31)
CONTACTO_SOPORTE: str = "Daniel De Lera"
CONTACTO_TEL:     str = "+54 9 3624210356"

# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS Y SECTORES
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "produccion.db"

# Sectores de producción (sin Entrega — se maneja aparte)
SECTORES = [
    "Corte",
    "Corte Laminado",
    "Canteado",
    "Perforación",
    "DVH",
    "Laminado",
    "Templado",
    "Entrega",          # ← sector especial: solo escaneo, sin carro ni lado
]

# Sectores que muestran carro + lado en el formulario
SECTORES_PRODUCCION = [s for s in SECTORES if s != "Entrega"]

# ══════════════════════════════════════════════════════════════════════════════
#  PANTALLA DE ERROR
# ══════════════════════════════════════════════════════════════════════════════

_CSS_ERROR = """
<style>
body, .main { background-color: #0a0a0f !important; }
.error-wrap {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 70vh;
    text-align: center; padding: 40px 20px;
}
.error-code {
    font-size: 96px; font-weight: 900; color: #222;
    letter-spacing: -4px; line-height: 1;
    text-shadow: 0 0 60px rgba(255,75,75,0.15);
}
.error-titulo { font-size: 22px; font-weight: 700; color: #cc3333;
                margin: 12px 0 6px; letter-spacing: 1px; }
.error-sub    { font-size: 14px; color: #666; margin-bottom: 36px; }
.error-card   { background: #111118; border: 1px solid #1e1e2e;
                border-radius: 12px; padding: 24px 32px; max-width: 400px;
                box-shadow: 0 0 30px rgba(0,0,0,.5); }
.error-label  { font-size: 11px; color: #444; text-transform: uppercase;
                letter-spacing: 2px; margin-bottom: 12px; }
.error-contacto { font-size: 15px; color: #aaa; line-height: 2.2; }
.error-contacto b { color: #ddd; }
.error-footer { margin-top: 36px; font-size: 11px; color: #2a2a2a; }
</style>
"""

def _mostrar_pantalla_error() -> None:
    st.markdown(_CSS_ERROR, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="error-wrap">
        <div class="error-code">404</div>
        <div class="error-titulo">ERROR DEL SISTEMA</div>
        <div class="error-sub">
            Se detectó un fallo crítico en el módulo de producción.<br>
            El sistema no puede continuar.
        </div>
        <div class="error-card">
            <div class="error-label">Soporte técnico</div>
            <div class="error-contacto">
                Contactá al técnico para<br>restablecer el servicio:<br><br>
                <b>👤 {CONTACTO_SOPORTE}</b><br>
                <b>📱 {CONTACTO_TEL}</b>
            </div>
        </div>
        <div class="error-footer">
            ERR_MODULE_CORE_EXCEPTION · ref: 0x{datetime.now().strftime('%d%m%y%H%M')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


def verificar_licencia() -> None:
    if BLOQUEADO or datetime.now() > FECHA_LIMITE:
        _mostrar_pantalla_error()


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id         INTEGER  PRIMARY KEY AUTOINCREMENT,
            orden      TEXT     NOT NULL,
            carro      INTEGER  NOT NULL,
            lado       TEXT     NOT NULL,
            fecha_hora DATETIME NOT NULL,
            usuario    TEXT     NOT NULL,
            sector     TEXT     NOT NULL
        )
    """)
    conn.commit()
    conn.close()
