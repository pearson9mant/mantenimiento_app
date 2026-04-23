from pathlib import Path
from datetime import datetime
import traceback

from database.db import inicializar_db
from modules.outlook import importar_incidencias_outlook


def escribir_log(mensaje: str) -> None:
    base_dir = Path(__file__).resolve().parent
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "importacion_outlook.log"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensaje}\n")


def main() -> None:
    try:
        inicializar_db()
        nuevos, estado = importar_incidencias_outlook()

        if estado == "OK":
            escribir_log(f"Importación correcta. Nuevas incidencias: {nuevos}")
        else:
            escribir_log(f"Importación con aviso/error: {estado}")

    except Exception as e:
        escribir_log(f"ERROR inesperado: {e}")
        escribir_log(traceback.format_exc())


if __name__ == "__main__":
    main()