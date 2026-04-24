"""
Componente reutilizable para renderizar una tarjeta de orden con botón de acción.
"""
import re
import streamlit as st

# Regex para detectar número maestro y pieza: "9147973-1" o "9147973 1"
# Acepta cualquier separador de guión o espacio antes del número de pieza final.
_MAESTRO_RE = re.compile(r'^(.*?)[-\s](\d+)$')
# Prefijos [URGENTE] / [INCIDENCIA] que se deben ignorar al detectar el maestro
_PFX_STRIP  = re.compile(r'^\s*\[(URGENTE|INCIDENCIA)\]\s*', re.IGNORECASE)


def agrupar_por_orden_maestra(ordenes: list) -> dict:
    """
    Agrupa órdenes por su número maestro.

    Detecta el patrón NNNNNNN-M o NNNNNNN M (guión o espacio como separador).
    Las órdenes que no coinciden quedan como grupos de 1 elemento.
    Devuelve dict ordenado {maestro: [lista de dicts de orden]}.
    """
    grupos: dict = {}
    for orden in ordenes:
        nombre = str(orden.get("orden", ""))
        base   = _PFX_STRIP.sub("", nombre).strip()
        m      = _MAESTRO_RE.match(base)
        clave  = m.group(1).strip() if m else nombre
        grupos.setdefault(clave, []).append(orden)
    return grupos

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
    """Inyecta el CSS de tarjetas. Llamar una vez al inicio de cada página."""
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
    .orden-card:hover { filter: brightness(1.06); }
    .orden-card.en-grupo:hover { filter: none; }
    .orden-card .orden-num {
        font-size: 18px;
        font-weight: 900;
        letter-spacing: 0.3px;
    }
    .orden-card .orden-meta {
        font-size: 13px;
        font-weight: 600;
        color: #cbd5e1;
        margin-top: 5px;
        letter-spacing: 0.2px;
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


def render_grupo_maestro_header(maestro: str, n_piezas: int, carro, estado: str = "pendiente") -> None:
    """Encabezado visual diferenciado para un grupo de subórdenes."""
    borde = _BORDE.get(estado, _BORDE["pendiente"])
    fondo_claro = {
        "pendiente":  "#1a2f4a",
        "en_proceso": "#2a1f08",
        "danado":     "#3d0f0f",
        "terminado":  "#0f3320",
    }.get(estado, "#1a2f4a")
    st.markdown(
        f'<div style="'
        f'background:{fondo_claro};'
        f'border-left:5px solid {borde};'
        f'border-radius:8px;'
        f'padding:10px 14px;'
        f'margin-bottom:4px;'
        f'display:flex;align-items:center;gap:10px;'
        f'">'
        f'<span style="font-size:20px;">📋</span>'
        f'<span style="font-size:16px;font-weight:800;color:#e2e8f0;">{maestro}</span>'
        f'<span style="background:#eab308;color:#0f172a;font-size:12px;font-weight:700;'
        f'padding:2px 9px;border-radius:12px;margin-left:4px;">{n_piezas} piezas</span>'
        f'<span style="font-size:12px;color:#94a3b8;margin-left:6px;">Carro {carro}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_tarjeta_orden(
    orden: dict,
    accion_label: str,
    accion_key: str,
    estado: str = "pendiente",
    meta_texto: str | None = None,
    dentro_de_grupo: bool = False,
) -> bool:
    """
    Renderiza la tarjeta de una orden + botón de acción.

    Devuelve True si el botón fue clickeado, False si no.

    Parámetros:
        orden       : dict con claves orden, carro, lado, usuario, fecha_hora
        accion_label: texto del botón (ej. "↘️ TOMAR")
        accion_key  : key único de Streamlit para el botón
        estado      : "pendiente" | "en_proceso" | "danado" | "terminado"
        meta_texto  : texto de la línea de metadatos; si es None se construye
                      automáticamente a partir de carro/lado/usuario/fecha_hora
    """
    nombre = str(orden.get("orden", ""))
    nombre_up = nombre.upper()
    es_urgente    = "[URGENTE]"    in nombre_up
    es_incidencia = "[INCIDENCIA]" in nombre_up

    # Si es urgente el estado visual siempre es rojo
    estado_visual = "danado" if es_urgente else estado

    borde = _BORDE.get(estado_visual, _BORDE["pendiente"])
    fondo = _FONDO.get(estado_visual, _FONDO["pendiente"])
    color = _COLOR_ORDEN.get(estado_visual, _COLOR_ORDEN["pendiente"])
    icono = _ICONO.get(estado, _ICONO["pendiente"])

    if dentro_de_grupo:
        fondo = "#1e293b"
        color = "#e2e8f0"

    badges = ""
    if es_urgente:
        badges += '<span class="badge-urgente">URGENTE</span>'
    if es_incidencia:
        badges += '<span class="badge-incidencia">INCIDENCIA</span>'

    if meta_texto is None:
        carro      = orden.get("carro", "")
        lado       = orden.get("lado", "")
        usuario    = orden.get("usuario", "")
        fecha_hora = orden.get("fecha_hora", "")
        partes = [
            f"🛒 Carro {carro}" if carro != "" else None,
            f"Lado {lado}"      if lado         else None,
            str(usuario)        if usuario       else None,
            str(fecha_hora)     if fecha_hora    else None,
        ]
        meta_texto = " · ".join(p for p in partes if p)

    clases = "orden-card en-grupo" if dentro_de_grupo else "orden-card"
    st.markdown(
        f'<div class="{clases}" style="background:{fondo};--borde:{borde};">'
        f'  <div class="orden-num" style="color:{color};">{icono} {nombre}{badges}</div>'
        f'  <div class="orden-meta">{meta_texto}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    return st.button(accion_label, key=accion_key, use_container_width=True)
