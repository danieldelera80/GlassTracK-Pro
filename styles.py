"""
Estilos globales compartidos entre todas las páginas.
Importar con: from styles import CSS_GLOBAL, sidebar_html
"""

CSS_GLOBAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

/* ══════════════════════════════════════════════════════════
   FORZAR TEMA OSCURO
   ══════════════════════════════════════════════════════════ */
:root { color-scheme: dark !important; }
html, body { color-scheme: dark !important; }
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #0d1117 !important;
}

/* ── Fuente global ── */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}

/* ══════════════════════════════════════════════════════════
   OCULTAR BOTONES DE STREAMLIT CLOUD
   REGLA CRÍTICA: NO ocultar ningún CONTENEDOR padre porque
   puede contener el botón de sidebar. Solo ocultar hojas.
   ══════════════════════════════════════════════════════════ */

/* Contenedor de acciones de la derecha — este SÍ es seguro ocultar */
[data-testid="stToolbarActions"] {
    display: none !important;
    visibility: hidden !important;
}

/* Elementos decorativos y badges */
[data-testid="stDecoration"],
[data-testid="stBottom"],
[data-testid="stStatusWidget"],
[class*="viewerBadge"],
[class*="managedApp"],
[data-testid="stShareButton"],
.stDeployButton,
footer,
#MainMenu {
    display: none !important;
    visibility: hidden !important;
}

/* Botones individuales por nombre — capa extra de seguridad */
button[title="Manage app"],
button[aria-label="Manage app"],
button[title="Share"],
button[aria-label="Share"],
button[title="Star app"],
button[aria-label="Star app"],
button[title="Edit app"],
button[aria-label="Edit app"],
button[title="View on Github"],
button[aria-label="View on Github"],
button[title="View source"],
button[aria-label="View source"],
button[title="Fork"],
button[aria-label="Fork"] {
    display: none !important;
    visibility: hidden !important;
}

/* ══════════════════════════════════════════════════════════
   GARANTIZAR VISIBILIDAD DEL BOTÓN DE SIDEBAR
   Cubre tanto el botón abierto como el colapsado
   ══════════════════════════════════════════════════════════ */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNavButton"],
[data-testid="stBaseButton-headerNoPadding"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 1000 !important;
}

/* Header transparente — SIN height:0, SIN overflow:hidden */
header[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

/* Reducir padding superior */
.main .block-container {
    padding-top: 0.5rem !important;
}

/* ── Animaciones ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(15px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stVerticalBlock"] > div:first-child {
    animation: fadeInUp 0.3s ease-out forwards;
}

/* ── Ocultar navegación automática de páginas ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b27 100%) !important;
    border-right: 1px solid #1e2a3a !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* ── Header del sidebar ── */
.sb-header {
    background: linear-gradient(135deg, #1a3a6b 0%, #0d1f3c 100%);
    padding: 24px 16px 20px;
    margin: -1rem -1rem 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    text-align: center;
}
.sb-logo { font-size: 38px; margin-bottom: 8px; transition: transform 0.3s; }
.sb-header:hover .sb-logo { transform: rotate(10deg) scale(1.1); }
.sb-empresa {
    font-size: 14px; font-weight: 800; color: #60a5fa;
    letter-spacing: 2px; text-transform: uppercase;
}
.sb-sistema { font-size: 11px; color: #94a3b8; margin-top: 2px; }

/* ── Tarjeta operario ── */
.sb-op-card {
    background: rgba(13,31,60,0.6);
    border: 1px solid rgba(74,144,217,0.2);
    border-radius: 12px; padding: 14px; margin-bottom: 12px;
    transition: background 0.3s;
}
.sb-op-card:hover { background: rgba(13,31,60,0.9); }
.sb-op-label { font-size: 10px; color: #60a5fa; text-transform: uppercase;
               letter-spacing: 1.5px; margin-bottom: 4px; }
.sb-op-name  { font-size: 16px; font-weight: 700; color: #f8fafc; }
.sb-op-sector { font-size: 12px; color: #93c5fd; margin-top: 4px; }

/* ── Botones globales ── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    min-height: 3.2em !important;
    height: auto !important;
    padding: 0.5em 1em !important;
    background: linear-gradient(135deg, #1e293b, #0f172a) !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 16px rgba(59,130,246,0.3) !important;
    border-color: #3b82f6 !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border: none !important; color: #ffffff !important;
    box-shadow: 0 4px 6px rgba(37,99,235,0.2) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    box-shadow: 0 8px 15px rgba(37,99,235,0.4) !important;
}

/* Campos de texto */
div[data-baseweb="input"] {
    border-radius: 12px !important;
    background-color: rgba(30,41,59,0.7) !important;
    border: 1px solid #475569 !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.3) !important;
}

/* ── Barra de pasos sticky ── */
.steps-bar {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 20px;
    position: sticky; top: 0; z-index: 100;
    background: #0f172a;
    padding: 12px 8px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-left: -1rem; margin-right: -1rem;
}
.steps-bar::before {
    content: ''; position: absolute; top: 18px; left: 10%; right: 10%;
    height: 3px; background: #1e293b; z-index: 0;
}
.step-item { display: flex; flex-direction: column; align-items: center; flex: 1; z-index: 1; }
.step-circle {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; border: 2px solid #334155;
    background: #0f172a; color: #64748b; transition: all 0.3s ease;
}
.step-circle.done   { background: #064e3b; border-color: #059669; color: #34d399; }
.step-circle.active { background: #1e3a8a; border-color: #3b82f6; color: #bfdbfe;
                      box-shadow: 0 0 15px rgba(59,130,246,0.4); }
.step-label { font-size: 12px; color: #64748b; margin-top: 6px; text-align: center; }
.step-label.active { color: #60a5fa; font-weight: 700; }
.step-label.done   { color: #059669; }

/* ── Metric Cards ── */
.glass-metric {
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(148,163,184,0.1);
    border-radius: 16px; padding: 24px; text-align: center;
    transition: transform 0.3s ease, border-color 0.3s ease;
    margin-bottom: 16px;
}
.glass-metric:hover { transform: translateY(-4px); border-color: rgba(59,130,246,0.5); }
.glass-title { font-size: 13px; color: #94a3b8; text-transform: uppercase;
               letter-spacing: 1.5px; font-weight: 600; }
.glass-value {
    font-size: 46px; font-weight: 800; margin-top: 8px;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.glass-value.green {
    background: linear-gradient(135deg, #34d399, #10b981);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

/* ── Alerta Urgente ── */
@keyframes pulseUrgente {
    0%   { box-shadow: 0 0 0 0 rgba(239,68,68,0.85); border-color: #ef4444; }
    60%  { box-shadow: 0 0 0 14px rgba(239,68,68,0); border-color: #991b1b; }
    100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); border-color: #ef4444; }
}
.alerta-urgente {
    display: flex; align-items: center; gap: 14px;
    background: linear-gradient(135deg, #7f1d1d 0%, #3b0808 100%);
    border: 2px solid #ef4444; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 18px;
    animation: pulseUrgente 1.8s ease-out infinite;
}
.alerta-urgente-titulo {
    font-weight: 800; font-size: 12px;
    letter-spacing: 2px; text-transform: uppercase; color: #fca5a5;
}
.alerta-urgente-ordenes {
    font-size: 15px; margin-top: 5px; color: #ffffff;
    font-weight: 700; word-break: break-all;
}

/* ── Responsive Mobile / Tablet ── */
@media screen and (max-width: 768px) {
    .glass-metric { padding: 14px 10px; margin-bottom: 8px; }
    .glass-value  { font-size: 34px; }
    .glass-title  { font-size: 11px; }
    .stButton > button { min-height: 3.8em !important; font-size: 16px !important; }
    [data-testid="stTextInput"] input { font-size: 16px !important; }
    [data-testid="stSidebar"] { min-width: 200px !important; max-width: 260px !important; }
    .modebar { display: none !important; }
}
@media screen and (max-width: 480px) {
    .glass-value { font-size: 26px; }
    .glass-title { font-size: 10px; }
    [data-testid="stDataFrame"] { font-size: 12px !important; }
}

/* ── Panel de éxito ── */
.success-panel {
    padding: 28px 20px; margin: 16px 0;
    background: linear-gradient(135deg, rgba(6,78,59,0.8), rgba(2,44,34,0.8));
    border: 1px solid #059669; border-radius: 16px;
    color: #a7f3d0; text-align: center;
    box-shadow: 0 0 30px rgba(16,185,129,0.2);
}

/* ── Historial mini ── */
.hist-row {
    display: flex; gap: 10px; align-items: center;
    font-size: 12px; color: #64748b;
    padding: 4px 0; border-bottom: 0.5px solid rgba(148,163,184,0.1);
}
.hist-orden { font-weight: 600; color: #94a3b8; }
.hist-check { color: #34d399; font-size: 14px; }

</style>
"""


def render_sb_header():
    import streamlit as st
    st.markdown("""
    <div class="sb-header">
        <div class="sb-logo">🏭</div>
        <div class="sb-empresa">Contacto S.A.</div>
        <div class="sb-sistema">Control de Producción</div>
    </div>
    """, unsafe_allow_html=True)


def render_sb_operario(op: str, sector: str):
    import streamlit as st
    st.markdown(f"""
    <div class="sb-op-card">
        <div class="sb-op-label">Sesión activa</div>
        <div class="sb-op-name">👷 {op}</div>
        <div class="sb-op-sector">📍 {sector}</div>
    </div>
    """, unsafe_allow_html=True)


def render_steps(paso_actual: int, labels: list):
    import streamlit as st
    items = ""
    for i, label in enumerate(labels):
        if i < paso_actual:
            cls_c, cls_l, icon = "done",   "done",   "✓"
        elif i == paso_actual:
            cls_c, cls_l, icon = "active", "active", str(i + 1)
        else:
            cls_c, cls_l, icon = "",       "",       str(i + 1)
        items += f"""
        <div class="step-item">
            <div class="step-circle {cls_c}">{icon}</div>
            <div class="step-label  {cls_l}">{label}</div>
        </div>"""
    st.markdown(f'<div class="steps-bar">{items}</div>', unsafe_allow_html=True)


def render_contexto(op: str, sector: str):
    import streamlit as st
    inicial = op[0].upper() if op else "?"
    st.markdown(f"""
    <div class="ctx-bar">
        <div class="ctx-avatar">{inicial}</div>
        <div class="ctx-info">
            <div class="ctx-name">{op}</div>
            <div class="ctx-sector">📍 {sector}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
