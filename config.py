"""
config.py — Configuración compartida entre todas las páginas con conexión a NEON.
"""
import streamlit as st
from datetime import datetime
from pathlib import Path
from sqlalchemy import text  # Necesario para Neon

# ══════════════════════════════════════════════════════════════════════════════
#  🔒 CONTROL DE LICENCIA
# ══════════════════════════════════════════════════════════════════════════════
CLIENTE_ID: str = "contacto-sa"
LICENCIA_URL: str = f"https://raw.githubusercontent.com/danieldelera80/licencias/main/{CLIENTE_ID}.json"
FECHA_LIMITE: datetime = datetime(2026, 12, 31)
CONTACTO_SOPORTE: str = "Daniel De Lera"
CONTACTO_TEL:     str = "+54 9 3624210356"

# Contraseña global para acciones críticas — definida en st.secrets, nunca en código
ADMIN_PASSWORD: str = st.secrets.get("ADMIN_PASSWORD", "")


def es_admin_valido(intento: str) -> bool:
    """
    Valida una contraseña de admin de forma segura.
    Devuelve True SOLO si ADMIN_PASSWORD está configurado en secrets Y coincide con `intento`.
    Cierra el bypass que ocurría cuando ADMIN_PASSWORD quedaba vacío y `pass_input == ""` daba True.
    """
    return bool(ADMIN_PASSWORD) and intento == ADMIN_PASSWORD

# ══════════════════════════════════════════════════════════════════════════════
#  RUTAS Y SECTORES
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).parent

SECTORES = [
    "Corte", "Corte Laminado", "Canteado", "Biselado", "Perforación",
    "DVH", "Laminado", "Sala de Laminado", "Autoclave", "Templado", "Optimización", "Terminado", "Entrega",
]

# Sectores que requieren escaneo directo (sin carro ni lado)
SECTORES_ESCANEO_DIRECTO = {"Terminado", "Entrega"}

SECTORES_PRODUCCION = [s for s in SECTORES if s not in SECTORES_ESCANEO_DIRECTO]

# ══════════════════════════════════════════════════════════════════════════════
#  BASE DE DATOS EN LA NUBE (NEON)
# ══════════════════════════════════════════════════════════════════════════════

def get_connection():
    """Retorna la conexión activa a Neon definida en secrets.toml"""
    return st.connection("postgresql", type="sql")

def verificar_estado_sistema():
    """Kill Switch maestro: si BLOQUEO_ACTIVO es true en secrets, tira la app abajo."""
    bloqueado = False
    
    # Chequeamos si existe en los secrets locales o de Streamlit Cloud
    if "BLOQUEO_ACTIVO" in st.secrets:
        if str(st.secrets["BLOQUEO_ACTIVO"]).lower() in ['true', '1', 'yes', 't']:
            bloqueado = True
            
    if bloqueado:
        st.error("🚨 **MANTENIMIENTO URGENTE REQUERIDO** 🚨\n\nEl sistema se encuentra temporalmente fuera de servicio por tareas de mantenimiento crítico. Por favor, aguarde a que el administrador restablezca los servicios.")
        st.stop()

def init_db() -> None:
    """Crea la tabla registros en Neon si no existe."""
    conn = get_connection()
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS registros (
                id         SERIAL PRIMARY KEY,
                orden      TEXT     NOT NULL,
                carro      INTEGER  NOT NULL,
                lado       TEXT     NOT NULL,
                fecha_hora TIMESTAMP NOT NULL,
                usuario    TEXT     NOT NULL,
                sector     TEXT     NOT NULL
            );
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS incidencias_detalle (
                id         SERIAL PRIMARY KEY,
                orden_base TEXT     NOT NULL UNIQUE,
                detalle    TEXT     NOT NULL,
                fecha_hora TIMESTAMP NOT NULL
            );
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS auditoria_incidencias (
                id               SERIAL PRIMARY KEY,
                orden_original   TEXT      NOT NULL,
                orden_resultante TEXT      NOT NULL,
                admin_usuario    TEXT      NOT NULL,
                fecha_hora       TIMESTAMP NOT NULL DEFAULT NOW(),
                motivo           TEXT
            );
        """))
        s.commit()

# ══════════════════════════════════════════════════════════════════════════════
#  SISTEMA DE LICENCIA (Mantenido)
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
        <div class="error-sub">Se detectó un fallo crítico en el módulo de producción.</div>
        <div class="error-card">
            <div class="error-label">Soporte técnico</div>
            <div class="error-contacto">
                Contactá al técnico:<br><br>
                <b>👤 {CONTACTO_SOPORTE}</b><br>
                <b>📱 {CONTACTO_TEL}</b>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

def _consultar_licencia_online() -> bool | None:
    """
    Consulta el JSON de licencia en GitHub.

    Retorna:
        True  -> licencia confirmada activa
        False -> licencia explicitamente revocada o vencida (bloquear sistema)
        None  -> no se pudo verificar (red caida / payload corrupto) -> fail-open: usa FECHA_LIMITE
    """
    import urllib.request
    import urllib.error
    import json
    import socket

    # Etapa 1 - red. Cualquier fallo de conectividad/timeout no bloquea al cliente.
    try:
        req = urllib.request.Request(LICENCIA_URL, headers={"User-Agent": "GlassTrack/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw = resp.read().decode()
    except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError):
        return None  # GitHub caido / DNS / sin internet -> fail-open

    # Etapa 2 - parseo. JSON corrupto tampoco bloquea (asumimos transient).
    try:
        data = json.loads(raw)
        if not data.get("activo", True):
            return False  # revocada explicitamente
        vence_str = data.get("vence", "")
        if vence_str:
            if datetime.now() > datetime.strptime(vence_str, "%Y-%m-%d"):
                return False  # vencida explicitamente
        return True
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return None  # payload corrupto/inesperado -> fail-open

def verificar_licencia() -> None:
    estado = _consultar_licencia_online()
    if estado is False: _mostrar_pantalla_error()
    elif estado is None:
        if datetime.now() > FECHA_LIMITE: _mostrar_pantalla_error()