"""
Estilos globales compartidos entre todas las páginas.
Importar con: from styles import CSS_GLOBAL, sidebar_html
"""

CSS_GLOBAL = """
<style>

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
    padding: 20px 16px 16px;
    margin: -1rem -1rem 20px;
    border-bottom: 1px solid #2a4a7a;
    text-align: center;
}
.sb-logo { font-size: 32px; margin-bottom: 4px; }
.sb-empresa {
    font-size: 13px; font-weight: 800; color: #4a90d9;
    letter-spacing: 2px; text-transform: uppercase;
}
.sb-sistema { font-size: 11px; color: #5a7a9a; margin-top: 2px; }

/* ── Tarjeta de operario en sidebar ── */
.sb-op-card {
    background: #0d1f3c;
    border: 1px solid #1e3a6a;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 12px;
}
.sb-op-label { font-size: 10px; color: #4a6a9a; text-transform: uppercase;
               letter-spacing: 1.5px; margin-bottom: 4px; }
.sb-op-name  { font-size: 16px; font-weight: 700; color: #e0e8f5; }
.sb-op-sector {
    font-size: 12px; color: #4a90d9; margin-top: 3px;
    display: flex; align-items: center; gap: 4px;
}

/* ── Botones del sidebar ── */
.sb-btn-group { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }

/* ── Estilos globales de botones ── */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    height: 3.2em !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(74,144,217,0.3) !important;
}

/* ── Barra de pasos ── */
.steps-bar {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 28px; position: relative;
}
.steps-bar::before {
    content: ''; position: absolute; top: 18px; left: 10%; right: 10%;
    height: 3px; background: #1e2a3a; z-index: 0;
}
.step-item {
    display: flex; flex-direction: column; align-items: center;
    flex: 1; z-index: 1;
}
.step-circle {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; border: 2px solid #1e2a3a;
    background: #0d1117; color: #3a4a5a;
}
.step-circle.done   { background: #1a4a2e; border-color: #2a8a45; color: #4ada75; }
.step-circle.active { background: #1a3a6b; border-color: #4a90d9; color: #90c0ff; }
.step-label { font-size: 11px; color: #3a4a5a; margin-top: 5px; text-align: center; }
.step-label.active  { color: #4a90d9; font-weight: 700; }
.step-label.done    { color: #2a8a45; }

/* ── Barra de contexto operario/sector ── */
.ctx-bar {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; background: #0d1f3c;
    border-radius: 10px; margin-bottom: 20px;
    border: 1px solid #1e3a6a;
}
.ctx-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, #1a3a6b, #0d1f3c);
    border: 2px solid #4a90d9;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.ctx-info { flex: 1; min-width: 0; }
.ctx-name  { font-size: 14px; font-weight: 700; color: #e0e8f5;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ctx-sector { font-size: 12px; color: #4a90d9; }

/* ── Aviso duplicado ── */
.dup-box {
    padding: 16px; background: #1a0808;
    border: 1px solid #6a2020; border-radius: 12px;
    color: #ff8a8a; text-align: center; margin-bottom: 16px;
    font-size: 15px;
}

/* ── Panel de éxito ── */
.success-panel {
    padding: 28px 20px; margin: 16px 0;
    background: linear-gradient(135deg, #001a10, #002b1b);
    border: 1px solid #2a8a45; border-radius: 16px;
    color: #d4edda; text-align: center;
    box-shadow: 0 0 30px rgba(40,160,70,.15);
}

/* ── Footer sidebar ── */
.sb-footer {
    position: absolute; bottom: 16px; left: 0; right: 0;
    text-align: center; font-size: 10px; color: #1e2a3a;
    padding: 0 16px;
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
