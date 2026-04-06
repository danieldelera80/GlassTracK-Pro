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

# ── Identificador único de este cliente ───────────────────────────────────────
# Cada instalación tiene su propio archivo JSON en el repo de licencias.
# Cambiá este valor por el nombre del cliente cuando instalés en una PC nueva.
CLIENTE_ID: str = "contacto-sa"

# ── URL del archivo de licencia en GitHub ─────────────────────────────────────
# Apunta al repo privado "licencias" donde controlás todos los clientes.
LICENCIA_URL: str = (
    f"https://raw.githubusercontent.com/danieldelera80/"
    f"licencias/main/{CLIENTE_ID}.json"
)

# ── Respaldo local (se usa si no hay internet) ────────────────────────────────
# Si el sistema no puede consultar GitHub, usa esta fecha como límite.
# Actualizala cada vez que el cliente paga, junto con el JSON online.
FECHA_LIMITE: datetime = datetime(2026, 12, 31)

# ── Datos de contacto ─────────────────────────────────────────────────────────
CONTACTO_SOPORTE: str = "Daniel De Lera"
CONTACTO_TEL:     str = "+54 9 3624210356"

# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS Y SECTORES
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "produccion.db"

SECTORES = [
    "Corte",
    "Corte Laminado",
    "Canteado",
    "Perforación",
    "DVH",
    "Laminado",
    "Templado",
    "Entrega",
]

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
    """Muestra la pantalla de error 404 y detiene la ejecucion."""
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


def _consultar_licencia_online() -> bool | None:
    """
    Consulta el JSON de licencia en GitHub.
    Retorna:
        True  → licencia activa
        False → licencia bloqueada
        None  → sin internet o error (usar respaldo local)
    """
    try:
        import urllib.request
        import json

        req = urllib.request.Request(
            LICENCIA_URL,
            headers={"User-Agent": "GlassTrack/1.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())

        # Verificar si está activo
        if not data.get("activo", True):
            return False

        # Verificar fecha de vencimiento del JSON
        vence_str = data.get("vence", "")
        if vence_str:
            vence = datetime.strptime(vence_str, "%Y-%m-%d")
            if datetime.now() > vence:
                return False

        return True

    except Exception:
        # Sin internet o cualquier error → devuelve None (usar respaldo)
        return None


def verificar_licencia() -> None:
    """
    Sistema de licencia en dos capas:
      Capa 1 — Consulta GitHub (online): lee el JSON del cliente.
               Si está bloqueado o vencido → pantalla de error.
      Capa 2 — Respaldo local (offline):  si no hay internet,
               usa FECHA_LIMITE del config.py como fallback.
    """
    estado = _consultar_licencia_online()

    if estado is False:
        # GitHub dice bloqueado → mostrar error
        _mostrar_pantalla_error()

    elif estado is None:
        # Sin internet → usar respaldo local
        if datetime.now() > FECHA_LIMITE:
            _mostrar_pantalla_error()

    # estado is True → licencia activa → continuar normalmente


# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════

def init_db() -> None:
    """Crea la tabla registros si no existe."""
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
