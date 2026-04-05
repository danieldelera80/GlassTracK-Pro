# GlassTrack Pro — Sistema de Control de Produccion

## Instalacion (primera vez, solo una vez)

1. Doble click en **`instalar.bat`** (ejecutar como Administrador)
2. Esperar que termine — instala todo automaticamente
3. Listo. El sistema ya queda configurado para arrancar solo.

---

## Uso diario

El sistema **arranca automaticamente** cuando se enciende la PC.

Si necesitas iniciarlo manualmente:
→ Doble click en **`iniciar_https.bat`**

Desde cualquier celular o PC en la misma WiFi, abrir:
```
https://192.168.1.XX:8501
```
(La IP exacta aparece en la ventana negra al arrancar)

> La primera vez el navegador muestra advertencia de seguridad.
> Tocar **Avanzado** → **Continuar de todos modos**. Solo pasa una vez.

---

## Como usar el sistema

### Operarios — Cargar una orden
1. Abrir la URL en el celular
2. Tocar **Cargar Orden**
3. Seguir los pasos: Nombre → Sector → Escanear orden → Carro/Lado → Registrar

### Supervisores — Ver el monitor
1. Abrir la URL en cualquier dispositivo
2. Tocar **Monitor de Produccion**
3. Ver registros en tiempo real de todos los sectores

---

## Referencia de colores en el Monitor

| Color | Significa |
|---|---|
| 🔴 Fila roja | Orden escaneada mas de una vez = fallo o rotura |
| 🟢 Celda verde | Orden entregada al cliente |

---

## Archivos del sistema

```
planilla--main/
├── instalar.bat              ← INSTALAR (primera vez)
├── iniciar_https.bat         ← ARRANCAR el sistema
├── desinstalar_arranque.bat  ← Quitar arranque automatico
├── main.py                   ← Pagina de inicio
├── config.py                 ← Configuracion y licencia
├── styles.py                 ← Estilos visuales
├── pages/
│   ├── 01_Monitor.py         ← Dashboard supervisores
│   └── 02_Formulario.py      ← Carga de ordenes
├── produccion.db             ← Base de datos (NO borrar)
└── .streamlit/               ← Configuracion HTTPS
```

---

## Soporte tecnico

**Daniel De Lera**
WhatsApp: +54 9 3624210356
Lunes a Sabado de 8 a 20 hs

---

*GlassTrack Pro v1.0 — 2026*
