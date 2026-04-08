"""
Estilos globales compartidos entre todas las páginas.
Importar con: from styles import CSS_GLOBAL, sidebar_html
"""

CSS_GLOBAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

/* ── Fuente Moderna Global ── */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}

/* ── Ocultar "Manage app", toolbar y header de Streamlit Cloud ── */
header,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
[data-testid="stBottom"],
.stDeployButton,
button[title="Manage app"],
button[aria-label="Manage app"],
[class*="viewerBadge"],
[class*="managedApp"],
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}

/* ── Animaciones ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(15px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Animación solo en primer render (sin parpadeo en autorefresh) */
[data-testid="stVerticalBlock"] > div:first-child {
    animation: fadeInUp 0.3s ease-out forwards;
}

/* ── Ocultar navegación automática de Streamlit ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Sidebar general ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b27 100%);
    border-right: 1px solid #1e2a3a;
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

/* ── Tarjeta de operario en sidebar ── */
.sb-op-card {
    background: rgba(13, 31, 60, 0.6);
    backdrop-filter: blur(5px);
    border: 1px solid rgba(74, 144, 217, 0.2);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    transition: background 0.3s;
}
.sb-op-card:hover { background: rgba(13, 31, 60, 0.9); }
.sb-op-label { font-size: 10px; color: #60a5fa; text-transform: uppercase;
               letter-spacing: 1.5px; margin-bottom: 4px; }
.sb-op-name  { font-size: 16px; font-weight: 700; color: #f8fafc; }
.sb-op-sector {
    font-size: 12px; color: #93c5fd; margin-top: 4px;
    display: flex; align-items: center; gap: 4px;
}

/* ── Estilos globales de botones ── */
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
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 16px rgba(59, 130, 246, 0.3) !important;
    border-color: #3b82f6 !important;
}

/* Boton Primario sobreescritura */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    box-shadow: 0 8px 15px rgba(37, 99, 235, 0.4) !important;
}

/* Campos de texto */
div[data-baseweb="input"] {
    border-radius: 12px !important;
    background-color: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid #475569 !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
}

/* ── Barra de pasos ── */
.steps-bar {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 28px; position: relative;
}
.steps-bar::before {
    content: ''; position: absolute; top: 18px; left: 10%; right: 10%;
    height: 3px; background: #1e293b; z-index: 0;
}
.step-item {
    display: flex; flex-direction: column; align-items: center;
    flex: 1; z-index: 1;
}
.step-circle {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; border: 2px solid #334155;
    background: #0f172a; color: #64748b;
    transition: all 0.3s ease;
}
.step-circle.done   { background: #064e3b; border-color: #059669; color: #34d399; }
.step-circle.active { background: #1e3a8a; border-color: #3b82f6; color: #bfdbfe; box-shadow: 0 0 15px rgba(59, 130, 246, 0.4); }
.step-label { font-size: 12px; color: #64748b; margin-top: 6px; text-align: center; }
.step-label.active  { color: #60a5fa; font-weight: 700; }
.step-label.done    { color: #059669; }

/* ── Glassmorphism Custom Metric Cards ── */
.glass-metric {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    transition: transform 0.3s ease, border-color 0.3s ease;
    margin-bottom: 16px;
}
.glass-metric:hover {
    transform: translateY(-4px);
    border-color: rgba(59, 130, 246, 0.5);
}
.glass-title {
    font-size: 13px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
}
.glass-value {
    font-size: 46px;
    font-weight: 800;
    margin-top: 8px;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.glass-value.green {
    background: linear-gradient(135deg, #34d399, #10b981);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ── Responsive Mobile / Tablet ── */
@media screen and (max-width: 768px) {
    /* Columnas Streamlit apiladas */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    /* Métricas compactas */
    .glass-metric { padding: 14px 10px; margin-bottom: 8px; }
    .glass-value  { font-size: 34px; }
    .glass-title  { font-size: 11px; letter-spacing: 1px; }
    /* Botones touch-friendly (mínimo 44px WCAG) */
    .stButton > button { min-height: 3.8em !important; font-size: 16px !important; }
    /* Tabs más compactos */
    button[data-baseweb="tab"] { font-size: 13px !important; padding: 8px 10px !important; }
    /* Inputs full-width */
    [data-testid="stTextInput"] input { font-size: 16px !important; } /* evita zoom iOS */
    /* Radio horizontal pasa a vertical */
    [data-testid="stRadio"] > div { flex-direction: column !important; }
    /* Sidebar más estrecho */
    [data-testid="stSidebar"] { min-width: 200px !important; max-width: 260px !important; }
    /* Plotly chart: quitar toolbar en mobile */
    .modebar { display: none !important; }
}

@media screen and (max-width: 480px) {
    .glass-value  { font-size: 26px; }
    .glass-title  { font-size: 10px; }
    /* Tabla: fuente más pequeña para caber en pantalla */
    [data-testid="stDataFrame"] { font-size: 12px !important; }
}

/* ── Panel de éxito ── */
.success-panel {
    padding: 28px 20px; margin: 16px 0;
    background: linear-gradient(135deg, rgba(6,78,59,0.8), rgba(2,44,34,0.8));
    backdrop-filter: blur(8px);
    border: 1px solid #059669; border-radius: 16px;
    color: #a7f3d0; text-align: center;
    box-shadow: 0 0 30px rgba(16,185,129,0.2);
}

</style>
"""


def render_sb_header():
    """Cabecera con marca en el sidebar."""
    import streamlit as st
    st.markdown("""
    <div class="sb-header">
        <div class="sb-logo">🏭</div>
        <div class="sb-empresa">Contacto S.A.</div>
        <div class="sb-sistema">Control de Producción</div>
    </div>
    """, unsafe_allow_html=True)


def render_sb_operario(op: str, sector: str):
    """Tarjeta de operario activo en el sidebar."""
    import streamlit as st
    st.markdown(f"""
    <div class="sb-op-card">
        <div class="sb-op-label">Sesión activa</div>
        <div class="sb-op-name">👷 {op}</div>
        <div class="sb-op-sector">📍 {sector}</div>
    </div>
    """, unsafe_allow_html=True)


def render_steps(paso_actual: int, labels: list):
    """Barra de progreso de pasos."""
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
    """Barra de contexto con avatar."""
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
