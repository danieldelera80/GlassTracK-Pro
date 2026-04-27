function sendValue(value) {
    Streamlit.setComponentValue(value);
}

function onRender(event) {
    if (!window.rendered) {
        var container = document.getElementById('qr-reader');
        var status    = document.getElementById('qr-reader-results');

        document.body.style.margin  = '0';
        document.body.style.padding = '0';

        // Video element
        var video = document.createElement('video');
        video.setAttribute('autoplay', '');
        video.setAttribute('playsinline', '');
        video.style.width         = '100%';
        video.style.display       = 'block';
        video.style.borderRadius  = '8px';
        video.style.backgroundColor = '#111';
        container.appendChild(video);

        // Canvas oculto para captura
        var canvas = document.createElement('canvas');
        canvas.style.display = 'none';
        container.appendChild(canvas);

        // Boton de captura
        var btn = document.createElement('button');
        btn.innerText = String.fromCodePoint(0x1F4F8) + ' Capturar foto';
        btn.style.cssText = 'display:block;width:100%;margin-top:8px;padding:14px;font-size:16px;font-weight:600;background:#1976d2;color:#fff;border:none;border-radius:8px;cursor:pointer;';
        container.appendChild(btn);

        // Status text
        status.style.cssText = 'font-size:13px;color:#aaa;text-align:center;padding:6px 0 2px;min-height:22px;';
        status.innerText = 'Iniciando camara...';

        // Ajustar altura del iframe
        function ajustarAltura() {
            var totalH = video.offsetHeight + btn.offsetHeight + status.offsetHeight + 20;
            Streamlit.setFrameHeight(Math.max(totalH, 80));
        }

        // Iniciar camara trasera
        var constraints = { video: { facingMode: { ideal: 'environment' } } };
        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(stream) {
                video.srcObject = stream;
                video.onloadedmetadata = function() {
                    video.play();
                    // Fijar altura proporcional al aspecto real de la camara
                    var w = container.clientWidth || window.innerWidth;
                    var aspect = (video.videoHeight || 1) / (video.videoWidth || 1);
                    var h = Math.round(w * Math.min(aspect, 1.4)); // cap 1.4x para no ocupar toda la pantalla
                    video.style.height = h + 'px';
                    status.innerText = 'Enfoca el codigo de barras y captura.';
                    setTimeout(ajustarAltura, 50);
                };
            })
            .catch(function(err) {
                status.innerText = 'Error de camara: ' + err.message;
            });

        // Captura
        btn.addEventListener('click', function() {
            if (!video.videoWidth) {
                status.innerText = 'Espera que la camara cargue.';
                return;
            }
            canvas.width  = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            var dataUrl = canvas.toDataURL('image/jpeg', 0.92);
            status.innerText = String.fromCodePoint(0x23F3) + ' Procesando...';
            btn.disabled  = true;
            btn.style.background = '#555';
            sendValue(dataUrl);
        });

        window.rendered = true;
    }
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
Streamlit.setFrameHeight(0);