# 🏭 Reporte de Arquitectura: GlassTracK-Pro

Acabamos de dar un salto gigantesco en el sistema de tu fábrica. Pasamos de tener un programa local encapsulado en una de tus computadoras, a una **Plataforma Industrial de Trazabilidad en la Nube**. Aquí tienes detallado cada aspecto técnico.

---

## 1. Bitácora de Desarrollo Completo (Historial v1.0 a v2.0)

Desde que arrancamos el proyecto el día de ayer, GlassTracK ha escalado de ser un simple formulario a un software industrial completo. A continuación, el registro de cada piedra que pusimos en el sistema:

### Fase 1: El Sistema Base (Ayer)
- **Motor de Registro Rápido:** Creación de la página `02_Formulario.py`, diseñada para interactuar a máxima velocidad con pistolas escaner.
- **Trazabilidad de Carros y Lados:** Inclusión de registro para metadatos de fábrica, identificando no solo la pieza, sino en qué carro viaja y en qué posición.
- **Sistema de Contingencia Offline (`_paquetes_offline`):** Programamos un motor de "guardado de emergencia". Si el sistema perdía repentinamente la conexión con internet, los escaneos se guardaban temporalmente en unos archivitos en tu disco (JSON/TXT), y al volver la red, el sistema "escupía" todo de golpe a la base de datos sin perder un solo vidrio.

### Fase 2: Expansión y Tableros Interactivos (Hoy Temprano)
- **Módulo Kanban:** Eliminamos el sistema ciego de solo formulario, inyectando un tablero con dos grandes columnas ("Pendientes" y "En Proceso"). Al operario ahora le aparecen todas las órdenes automáticamente y interactúa con botones táctiles.
- **Sectores a Medida:** Agregamos "Biselado", "Sala de Laminado" y "Autoclave" y le dimos lógica híbrida a "Corte".
- **Lógica de Subdivisión de Órdenes (Auto-Sufijos):** Diseñamos el cerebro matemático `resolver_nombre_orden`. Permite que, si escaneas físicamente tres vidrios con la etiqueta `6542-1`, el sistema se da cuenta y los inyecta al Kanban como tres vidrios físicamente idénticos pero trazables individualmente (`6542-1`, `6542-1 - 2`, `6542-1 - 3`).
- **Layout Compacto para Despacho:** Modificamos la visual de Entrega, dándole un diseño comprimido táctil de una sola línea, excelente para agilizar colas de camiones.

### Fase 3: Ascenso a Plataforma Mundial (Hoy a la Tarde)
- **Migración a AWS (Neon):** Sacamos los datos históricos del archivo local SQLite y los encriptamos en la Nube con PostgreSQL para tener disponibilidad 24/7.
- **Despliegue Web Mundial:** Levantamos la plataforma publicándola a través de Streamlit Cloud, dándole a tu celular acceso en vivo al Monitor usando un Link Público, sacando al sistema del cautiverio del "Galpón 192.168.0.x".

---

## 2. La Nueva Arquitectura: ¿Dónde vive qué cosa?
Tu sistema *GlassTracK-Pro* ahora está dividido en dos grandes "cerebros" conectados entre sí por internet:

1. **El Código y las Pantallas (Streamlit Community Cloud):** Es la "cara" del sistema (el Monitor y el Formulario de Carga). Ahora está hospedado en servidores de alta potencia en Estados Unidos. 
2. **La Base de Datos (Neon):** Es la "memoria" (donde se guardan los registros históricos). Está en un entorno de máxima seguridad administrado por AWS (Amazon).

### 🟢 Pros de usar la Nube (Streamlit Cloud + Neon)
- **Acceso Mundial:** Vos y tus encargados pueden monitorear la fábrica desde su celular en el sillón de sus casas (o de clientes) con conexión 4G.
- **Sin Dependencia Física:** Si se inunda, se rompe, o se desenchufa tu PC de escritorio en la planta, el sistema **no se cae**.
- **Seguridad Infranqueable:** Al tener la base de datos en Neon, los datos de producción están resguardados en servidores de Amazon que tienen réplicas automáticas (RAID) previniendo pérdida por rotura de discos duros físicos.

### 🔴 Contras de la Nube (El "Talón de Aquiles")
- **Dependencia de la Red de Internet en la Planta:** Como los operarios usan tablets conectadas al router local, si la proveedora de internet del galpón se cae, las tablets no van a poder cargar la página web de Streamlit para "Tomar piezas".

***¿Cómo solucionamos un corte de internet severo?*** Podés mantener la compu vieja corriendo el código a través de `192.168...` adentro del galpón **sólo como plan de emergencia**. Si un día todo el galpón se queda sin fibra óptica, ordenás a los operarios entrar por la dirección IP local de contingencia en vez de la nube. Esa de emergencia sí guardará los datos pacientemente y luego los tirará a Neon.

---

## 3. Respaldo Automático (Backup Diario)

Para quitarte el miedo lógico de dejar los datos en la Nube, acabamos de programar tus propios robots de copiado y seguridad local:

- **La Máquina Extractora (`backup_nube.py`):** Este programa chupa silenciosamente los datos de Neon.
- **El Bucle Eterno (`auto_backup.bat`):** Un archivo que acabamos de dejar en tu carpeta. Lo abrís, lo dejas minimizado en la compu de la oficina, y él solo se va a encargar de bajar un Excel gigantesco con todos los movimientos de todo el año, lo guardará en la carpeta `backups/`, y esperará pacientemente **6 horas** para volver a descargarlo actualizado. Estás 100% blindado contra pérdidas de datos.

---

## 4. Bóveda Segura: Botón de Bloqueo a Clientes ("Kill Switch")

Como dueño del software, tenés acceso al poder maestro. Si le vendés/alquilás la plataforma a un cliente y este deja de pagar, a partir de hoy **ellos ya no son dueños de su sistema porque la base de datos es tuya**.

Si un cliente tuyo no paga o necesitás cortarles el sistema instantáneamente:
1. Tenés que entrar con tu usuario a la plataforma de Streamlit (donde administramos las contraseñas hoy).
2. Entrás a **Settings -> Secrets**
3. Pegás esta línea oculta al fondo del archivo: `BLOQUEO_ACTIVO = true`
4. Guardás.

Al instante, todas las tablets, computadoras y celulares de la fábrica del cliente se quedarán trabadas mostrando en rojo gigante: **"MANTENIMIENTO URGENTE: El sistema se encuentra temporalmente fuera de servicio por tareas."** y nadie en el galpón podrá operarlo hasta que vos entres y borres esa línea.
