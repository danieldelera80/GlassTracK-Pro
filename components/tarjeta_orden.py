"""
Componente reutilizable para renderizar una tarjeta de orden con botón de acción.
"""
import streamlit as st

_CSS_INYECTADO = False

# Colores de borde por estado
_BORDE = {
    "pendiente":  "#3b82f6",   # azul
    "en_proceso": "#eab308",   # amarillo
    "danado":     "#ef4444",   # rojo
    "terminado":  "#22c55e",   # verde
}

# Colores de fondo por estado
_FONDO = {
    "pendiente":  "#1e293b",
    "en_proceso": "#1f1605",
    "danado":     "#2d0a0a",
    "terminado":  "#0d2a1a",
}

# Color del número de orden por estado
_COLOR_ORDEN = {
    "pendiente":  "#60a5fa",
    "en_proceso": "#facc15",
    "danado":     "#f87171",
    "terminado":  "#4ade80",
}

# Ícono por estado
_ICONO = {
    "pendiente":  "📄",
    "en_proceso": "⚙️",
    "danado":     "⚠️",
    "terminado":  "📦",
}


def inyectar_css_tarjetas():
    """Inyecta el CSS de tarjetas una sola vez por página."""
    global _CSS_INYECTADO
    if _CSS_INYECTADO:
        return
    st.markdown("""
    <style>
    .orden-card {
        border-left: 4px solid var(--borde, #3b82f6);
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 6px;
        text-align: left;
        white-space: normal;
        line-height: 1.4;
        transition: background 0.15s;
    }
    .orden-card:hover { filter: brightness(1.12); }
    .orden-card .orden-num {
        font-size: 17px;
        font-weight: bold;
    }
    .orden-card .orden-meta {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }
    .badge-urgente {
        background: #ef4444;
        color: #fff;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: bold;
        margin-left: 6px;
        vertical-align: middle;
    }
    .badge-incidencia {
        background: #f59e0b;
        color: #1c1c1c;
        font-size: 11px;
        padding: 1px 6px;
        border-radius: 4px;
        font-weight: bold;
        margin-left: 6px;
        vertical-align: middle;
    }
    @media screen and (min-width: 768px) {
        .orden-card { max-width: 600px; }
    }
    </style>
    """, unsafe_allow_html=True)
    _CSS_INYECTADO = True


def render_tarjeta_orden(
    orden: dict,
    accion_label: str,
    accion_key: str,
    estado: str = "pendiente",
) -> bool:
    """
    Renderiza la tarjeta de una orden + botón de acción.

    Devuelve True si el botón fue clickeado, False si no.

    Parámetros:
        orden        : dict con claves orden, carro, lado, usuario, fecha_hora
        accion_label : texto del botón (ej. "↘️ TOMAR")
        accion_key   : key único de Streamlit para el botón
        estado       : "pendiente" | "en_proceso" | "danado" | "terminado"
    """
    nombre = str(orden.get("orden", ""))
    nombre_up = nombre.upper()
    es_urgente    = "[URGENTE]"    in nombre_up
    es_incidencia = "[INCIDENCIA]" in nombre_up

    # Si es urgente, el estado visual siempre es "danado" (rojo)
    estado_visual = "danado" if es_urgente else estado

    borde = _BORDE.get(estado_visual, _BORDE["pendiente"])
    fondo = _FONDO.get(estado_visual, _FONDO["pendiente"])
    color = _COLOR_ORDEN.get(estado_visual, _COLOR_ORDEN["pendiente"])
    icono = _ICONO.get(estado, _ICONO["pendiente"])

    badges = ""
    if es_urgente:
        badges += '<span class="badge-urgente">URGENTE</span>'
    if es_incidencia:
        badges += '<span class="badge-incidencia">INCIDENCIA</span>'

    usuario    = orden.get("usuario", "")
    carro      = orden.get("carro", "")
    lado       = orden.get("lado", "")
    fecha_hora = orden.get("fecha_hora", "")

    # Línea de metadatos: omitir campos vacíos
    meta_partes = [f"🛒 Carro {carro}" if carro != "" else None,
                   f"Lado {lado}"       if lado       else None,
                   str(usuario)         if usuario    else None,
                   str(fecha_hora)      if fecha_hora else None]
    meta = " · ".join(p for p in meta_partes if p)

    st.markdown(
        f'<div class="orden-card" style="background:{fondo};--borde:{borde};">'
        f'  <div class="orden-num" style="color:{color};">{icono} {nombre}{badges}</div>'
        f'  <div class="orden-meta">{meta}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    return st.button(accion_label, key=accion_key, use_container_width=True)
