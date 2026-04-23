from __future__ import annotations

import os
import re
import html

from datetime import datetime
from typing import Any, Dict, List, Optional
from modules.ordenes import crear_orden, obtener_siguiente_numero_ot

try:
    import win32com.client  # type: ignore
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None


# =========================================================
# CONFIGURACIÓN
# =========================================================

OUTLOOK_FOLDER_NAME = "Incidencias Pearson 22"

ASIGNACION_OPERARIO_POR_CENTRO = {
    "Pearson 9": "Luis Lozano",
    "Pearson 22": "J.A. Almeda",
}

ESTADO_INICIAL = "Abierta"
AREA_DEFAULT = "Otros"
PRIORIDAD_DEFAULT = "Media"
ORIGEN_DEFAULT = "Outlook"


# =========================================================
# CONEXIÓN POSTGRESQL
# =========================================================

def conectar_db():
    if psycopg2 is None:
        raise ImportError(
            "No está instalado psycopg2. Instala con: pip install psycopg2-binary"
        )

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        conn = psycopg2.connect(
            database_url,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    else:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            dbname=os.getenv("PGDATABASE", "mantenimiento"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
            cursor_factory=psycopg2.extras.RealDictCursor,
        )

    return conn


# =========================================================
# NORMALIZACIÓN
# =========================================================

def limpiar_texto(valor: Any) -> str:
    if valor is None:
        return ""

    texto = str(valor)
    texto = html.unescape(texto)
    texto = texto.replace("\xa0", " ")
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n+", "\n", texto)

    return texto.strip()


def normalizar_clave(clave: str) -> str:
    clave = limpiar_texto(clave).lower()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for a, b in reemplazos.items():
        clave = clave.replace(a, b)
    return clave.strip()


def normalizar_prioridad(valor: str) -> str:
    v = limpiar_texto(valor).lower()
    if v in ("alta", "urgente", "muy alta"):
        return "Alta"
    if v in ("baja", "leve"):
        return "Baja"
    if v in ("media", "normal", ""):
        return "Media"
    return PRIORIDAD_DEFAULT


def normalizar_area(valor: str) -> str:
    v = limpiar_texto(valor)
    return v if v else AREA_DEFAULT


def normalizar_centro(valor: str) -> str:
    v = limpiar_texto(valor)
    lv = v.lower()
    if lv in ("pearson22", "pearson 22", "p22"):
        return "Pearson 22"
    if lv in ("pearson9", "pearson 9", "p9"):
        return "Pearson 9"
    return v


def operario_por_centro(centro: str) -> str:
    return ASIGNACION_OPERARIO_POR_CENTRO.get(centro, "")


# =========================================================
# PARSEO DEL CORREO
# =========================================================

def extraer_campos_desde_body(body: str) -> Dict[str, str]:
    """
    Extrae campos del cuerpo del correo de forma robusta.
    Espera formatos tipo:

    Centro: Pearson 22
    Edificio: Infantil
    Aula/Espacio: Patio pequeño
    Incidencia: Sacar malas hierbas
    Prioridad: Baja
    Solicitante: Noemí
    """
    body = limpiar_texto(body)
    campos: Dict[str, str] = {}

    lineas = [limpiar_texto(x) for x in body.split("\n") if limpiar_texto(x)]

    for linea in lineas:
        linea_norm = linea.lower()

        if linea_norm.startswith("centro:"):
            campos["centro"] = limpiar_texto(linea.split(":", 1)[1])

        elif linea_norm.startswith("edificio:"):
            campos["edificio"] = limpiar_texto(linea.split(":", 1)[1])

        elif (
            linea_norm.startswith("aula/espacio:")
            or linea_norm.startswith("espacio:")
            or linea_norm.startswith("aula:")
            or linea_norm.startswith("ubicacion:")
        ):
            campos["espacio"] = limpiar_texto(linea.split(":", 1)[1])

        elif (
            linea_norm.startswith("incidencia:")
            or linea_norm.startswith("descripcion:")
        ):
            campos["descripcion"] = limpiar_texto(linea.split(":", 1)[1])

        elif linea_norm.startswith("prioridad:"):
            campos["prioridad"] = limpiar_texto(linea.split(":", 1)[1])

        elif linea_norm.startswith("solicitante:"):
            campos["solicitante"] = limpiar_texto(linea.split(":", 1)[1])

        elif linea_norm.startswith("area:"):
            campos["area"] = limpiar_texto(linea.split(":", 1)[1])

    return campos


def completar_desde_asunto(campos: Dict[str, str], subject: str) -> Dict[str, str]:
    subject = limpiar_texto(subject)
    if not campos.get("descripcion") and subject:
        campos["descripcion"] = subject
    return campos


def construir_registro_email(message: Any) -> Dict[str, Any]:
    subject = limpiar_texto(getattr(message, "Subject", ""))

    body = ""
    try:
        body = limpiar_texto(getattr(message, "Body", ""))
    except Exception:
        body = ""

    if not body:
        try:
            body = limpiar_texto(getattr(message, "HTMLBody", ""))
        except Exception:
            body = ""

    sender = limpiar_texto(getattr(message, "SenderName", ""))
    sender_email = ""

    try:
        sender_email = limpiar_texto(getattr(message, "SenderEmailAddress", ""))
    except Exception:
        sender_email = ""

    try:
        received_time = getattr(message, "ReceivedTime", None)
        fecha_recepcion = (
            received_time.strftime("%Y-%m-%d %H:%M:%S")
            if received_time
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception:
        fecha_recepcion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        entry_id = limpiar_texto(getattr(message, "EntryID", ""))
    except Exception:
        entry_id = ""

    campos = extraer_campos_desde_body(body)
    campos = completar_desde_asunto(campos, subject)

    centro = normalizar_centro(campos.get("centro", ""))
    edificio = limpiar_texto(campos.get("edificio", ""))
    espacio = limpiar_texto(campos.get("espacio", ""))
    descripcion = limpiar_texto(campos.get("descripcion", ""))

    if not descripcion:
        descripcion = subject

    prioridad = normalizar_prioridad(campos.get("prioridad", ""))
    solicitante = limpiar_texto(campos.get("solicitante", sender))
    area = normalizar_area(campos.get("area", ""))
    operario = operario_por_centro(centro)

    return {
        "entry_id": entry_id,
        "fecha_recepcion": fecha_recepcion,
        "asunto": subject,
        "body": body,
        "sender_name": sender,
        "sender_email": sender_email,
        "centro": centro,
        "edificio": edificio,
        "espacio": espacio,
        "descripcion": descripcion,
        "prioridad": prioridad,
        "solicitante": solicitante,
        "area": area,
        "operario": operario,
        "estado": ESTADO_INICIAL,
        "origen": ORIGEN_DEFAULT,
    }


# =========================================================
# TABLAS AUXILIARES
# =========================================================

def asegurar_tabla_importados(conn) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS correos_importados (
        id BIGSERIAL PRIMARY KEY,
        entry_id TEXT NOT NULL UNIQUE,
        fecha_importacion TIMESTAMP NOT NULL DEFAULT NOW(),
        asunto TEXT,
        remitente TEXT
    )
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


# =========================================================
# CONTROL DE DUPLICADOS
# =========================================================

def correo_ya_importado(conn, entry_id: str) -> bool:
    if not entry_id:
        return False

    sql = """
    SELECT 1
    FROM correos_importados
    WHERE entry_id = %s
    LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (entry_id,))
        row = cur.fetchone()
    return row is not None


def registrar_correo_importado(
    conn,
    entry_id: str,
    asunto: str,
    remitente: str,
) -> None:
    if not entry_id:
        return

    sql = """
    INSERT INTO correos_importados (
        entry_id,
        asunto,
        remitente
    )
    VALUES (%s, %s, %s)
    ON CONFLICT (entry_id) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.execute(sql, (entry_id, asunto, remitente))
    conn.commit()


# =========================================================
# NUMERACIÓN OT
# =========================================================

def extraer_numero(valor: Optional[str]) -> int:
    if not valor:
        return 0
    match = re.search(r"(\d+)$", valor)
    return int(match.group(1)) if match else 0


def obtener_siguiente_ot(conn) -> str:
    max_num = 0

    consultas = [
        "SELECT numero_ot FROM ordenes_trabajo",
        "SELECT numero_ot FROM historico_ordenes",
    ]

    with conn.cursor() as cur:
        for sql in consultas:
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                for row in rows:
                    numero_ot = row["numero_ot"] if isinstance(row, dict) else row[0]
                    max_num = max(max_num, extraer_numero(numero_ot))
            except Exception:
                conn.rollback()

    siguiente = max_num + 1
    return f"OT-{siguiente:05d}"


# =========================================================
# INSERCIÓN DE OT
# =========================================================

def insertar_ot_desde_correo(conn, datos: Dict[str, Any]) -> str:
    numero_ot = obtener_siguiente_numero_ot()

    crear_orden((
        numero_ot,
        datos.get("descripcion", ""),
        "Abierta",
        datos.get("centro", ""),
        datos.get("edificio", ""),
        datos.get("espacio", ""),
        datos.get("area", AREA_DEFAULT),
        datos.get("prioridad", PRIORIDAD_DEFAULT),
        datos.get("operario", ""),
        datos.get("origen", ORIGEN_DEFAULT),
    ))

    return numero_ot


# =========================================================
# OUTLOOK
# =========================================================

def obtener_bandeja_outlook():
    if win32com is None or pythoncom is None:
        raise ImportError(
            "No está instalado pywin32. Instala con: pip install pywin32"
        )

    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    return outlook.Folders


def buscar_carpeta_por_nombre(parent_folder, folder_name: str):
    for folder in parent_folder:
        try:
            if str(folder.Name).strip().lower() == folder_name.strip().lower():
                return folder

            subfolders = folder.Folders
            if subfolders.Count > 0:
                encontrada = buscar_carpeta_por_nombre(subfolders, folder_name)
                if encontrada is not None:
                    return encontrada
        except Exception:
            continue
    return None


def obtener_mensajes_outlook(folder_name: str = OUTLOOK_FOLDER_NAME) -> List[Any]:
    folders = obtener_bandeja_outlook()
    carpeta = buscar_carpeta_por_nombre(folders, folder_name)

    if carpeta is None:
        raise FileNotFoundError(
            f"No se encontró la carpeta de Outlook: '{folder_name}'"
        )

    items = carpeta.Items
    items.Sort("[ReceivedTime]", True)

    mensajes = []
    for item in items:
        try:
            clase = getattr(item, "Class", None)
            if clase == 43:  # MailItem
                mensajes.append(item)
        except Exception:
            continue

    return mensajes


# =========================================================
# IMPORTACIÓN PRINCIPAL
# =========================================================

def importar_correos_a_ot(
    folder_name: str = OUTLOOK_FOLDER_NAME,
    max_correos: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Importa correos Outlook y crea OTs directas.
    - No mueve correos
    - No borra correos
    - Evita duplicados con EntryID
    """
    if pythoncom is None:
        raise ImportError(
            "No está instalado pywin32 correctamente. Falta pythoncom."
        )

    conn = conectar_db()
    asegurar_tabla_importados(conn)

    pythoncom.CoInitialize()

    try:
        mensajes = obtener_mensajes_outlook(folder_name=folder_name)

        if max_correos is not None:
            mensajes = mensajes[:max_correos]

        creadas: List[Dict[str, str]] = []
        duplicadas = 0
        errores: List[str] = []

        for msg in mensajes:
            try:
                datos = construir_registro_email(msg)
                print("DEBUG EMAIL:", datos)

                entry_id = datos.get("entry_id", "")

                if entry_id and correo_ya_importado(conn, entry_id):
                    duplicadas += 1
                    continue

                if not datos.get("descripcion"):
                    datos["descripcion"] = datos.get("asunto", "Incidencia sin descripción")

                numero_ot = insertar_ot_desde_correo(conn, datos)

                registrar_correo_importado(
                    conn=conn,
                    entry_id=entry_id,
                    asunto=datos.get("asunto", ""),
                    remitente=datos.get("sender_name", ""),
                )

                creadas.append(
                    {
                        "numero_ot": numero_ot,
                        "centro": datos.get("centro", ""),
                        "edificio": datos.get("edificio", ""),
                        "espacio": datos.get("espacio", ""),
                        "descripcion": datos.get("descripcion", ""),
                        "operario": datos.get("operario", ""),
                    }
                )

            except Exception as e:
                conn.rollback()
                errores.append(str(e))

        return {
            "ok": True,
            "total_leidos": len(mensajes),
            "ots_creadas": len(creadas),
            "duplicadas": duplicadas,
            "errores": errores,
            "detalle": creadas,
        }

    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        conn.close()


# =========================================================
# PRUEBA MANUAL
# =========================================================

def main():
    resultado = importar_correos_a_ot()

    print("=== IMPORTACIÓN OUTLOOK -> OT (POSTGRESQL) ===")
    print(f"Leídos: {resultado['total_leidos']}")
    print(f"OT creadas: {resultado['ots_creadas']}")
    print(f"Duplicadas: {resultado['duplicadas']}")

    if resultado["detalle"]:
        print("\nOTs creadas:")
        for item in resultado["detalle"]:
            print(
                f"- {item['numero_ot']} | {item['centro']} | "
                f"{item['edificio']} | {item['espacio']} | "
                f"{item['descripcion']} | {item['operario']}"
            )

    if resultado["errores"]:
        print("\nErrores:")
        for err in resultado["errores"]:
            print(f"- {err}")


if __name__ == "__main__":
    main()