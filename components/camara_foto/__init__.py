from pathlib import Path
from typing import Optional
import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).parent / "frontend"
_component_func = components.declare_component("camara_foto", path=str(_FRONTEND_DIR))


def capturar_foto(key: Optional[str] = None) -> Optional[str]:
    return _component_func(key=key, default=None)
