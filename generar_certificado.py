"""
generar_certificado.py
Ejecutar UNA SOLA VEZ para crear el certificado SSL local.
Requiere: pip install cryptography
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path
import datetime
import socket
import ipaddress

print("=" * 55)
print("  Generador de certificado SSL local")
print("=" * 55)

# ── Detectar IP automáticamente ───────────────────────────────
hostname = socket.gethostname()
ip_local = socket.gethostbyname(hostname)
print(f"\n  IP detectada: {ip_local}")
print(f"  Hostname:     {hostname}\n")

# ── Generar clave privada ─────────────────────────────────────
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# ── Crear certificado autofirmado ─────────────────────────────
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, ip_local),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Contacto SA"),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))  # 10 años
    .add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv4Address(ip_local)),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256(), default_backend())
)

# ── Guardar archivos ──────────────────────────────────────────
ssl_dir = Path(__file__).parent / ".streamlit"
ssl_dir.mkdir(exist_ok=True)

cert_path = ssl_dir / "cert.pem"
key_path  = ssl_dir / "key.pem"

cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
key_path.write_bytes(
    key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
)

# ── Escribir config.toml de Streamlit ────────────────────────
config_path = ssl_dir / "config.toml"
config_path.write_text(f"""
[server]
address = "0.0.0.0"
port = 8501
sslCertFile = ".streamlit/cert.pem"
sslKeyFile  = ".streamlit/key.pem"

[browser]
gatherUsageStats = false
""")

print("  Archivos creados:")
print(f"    ✅ .streamlit/cert.pem")
print(f"    ✅ .streamlit/key.pem")
print(f"    ✅ .streamlit/config.toml")
print()
print("  Ahora ejecutá:  iniciar_https.bat")
print()
print(f"  En el celular entrá a:")
print(f"  👉  https://{ip_local}:8501")
print()
print("  El navegador va a mostrar una advertencia de seguridad.")
print("  Es normal porque el certificado es autofirmado.")
print("  Tocá 'Avanzado' → 'Continuar de todos modos'.")
print("  Solo tenés que hacerlo UNA VEZ.")
print("=" * 55)
