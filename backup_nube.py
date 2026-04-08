import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import os

def get_db_url():
    try:
        with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("url"):
                    # Extraer el valor entre comillas
                    valor = line.split("=", 1)[1].strip()
                    valor = valor.strip('"').strip("'")
                    return valor
    except Exception as e:
        print(f"Error leyendo secrets.toml: {e}")
    return None

def main():
    print("\n------------------------------------------------")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Conectando a Neon (Nube)...")
    url = get_db_url()
    if not url:
        print("❌ No se encontro la URL de la base de datos en secrets.toml")
        return
        
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            query = "SELECT * FROM registros ORDER BY fecha_hora DESC"
            df = pd.read_sql(text(query), conn)
            
        # Crear la carpeta de backups si no existe
        os.makedirs("backups", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filepath = f"backups/prod_{timestamp}.csv"
        
        # Exportar a Excel compatible (CSV con separador ; y BOM de texto para Excel)
        df.to_csv(filepath, index=False, sep=";", encoding="utf-8-sig")
        print(f"✅ EXITO: Backup generado en '{filepath}'")
        print(f"   Descargados {len(df)} registros historicos.")
    except Exception as e:
        print(f"❌ ERROR durante la descarga: {e}")
    print("------------------------------------------------\n")

if __name__ == "__main__":
    main()
