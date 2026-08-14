try:
    import pythoncom
    import win32com.client
    OUTLOOK_DISPONIBLE = True
except Exception:
    OUTLOOK_DISPONIBLE = False

import config

from database.db import conectar, _sql
from modules.ordenes import obtener_siguiente_numero_ot, crear_orden


ASIGNACION_OPERARIO_POR_CENTRO = getattr(
    config,
    "ASIGNACION_OPERARIO_POR_CENTRO",
    {
        "Pearson 9": "Luis Lozano",
        "Pearson 22": "J.A. Almeda",
    }
)


def extraer_datos_correo(cuerpo):
    datos = {
        "centro": "",
        "edificio": "",
        "espacio": "",
        "incidencia": "",
        "prioridad": "",
        "solicitante": "",
        "fecha": "",
    }

    lineas = str(cuerpo).splitlines()

    for linea in lineas:
        linea = linea.strip()

        if linea.startswith("Fecha:"):
            datos["fecha"] = linea.replace(
                "Fecha:",
                ""
            ).strip()

        elif linea.startswith("Centro:"):
            datos["centro"] = linea.replace(
                "Centro:",
                ""
            ).strip()

        elif linea.startswith("Edificio:"):
            datos["edificio"] = linea.replace(
                "Edificio:",
                ""
            ).strip()

        elif linea.startswith("Aula/Espacio:"):
            datos["espacio"] = linea.replace(
                "Aula/Espacio:",
                ""
            ).strip()

        elif linea.startswith("Incidencia:"):
            datos["incidencia"] = linea.replace(
                "Incidencia:",
                ""
            ).strip()

        elif linea.startswith("Prioridad:"):
            datos["prioridad"] = linea.replace(
                "Prioridad:",
                ""
            ).strip()

        elif linea.startswith("Solicitante:"):
            datos["solicitante"] = linea.replace(
                "Solicitante:",
                ""
            ).strip()

    return datos


def clasificar_area(texto):
    texto = str(
        texto or ""
    ).lower()

    reglas = {
        "Iluminación": [
            "luz",
            "fluorescente",
            "bombilla",
            "led",
            "apagado",
            "apagar",
            "enciende",
            "encender",
        ],
        "Electricidad": [
            "enchufe",
            "interruptor",
            "cuadro",
            "corriente",
            "eléctrico",
            "electricidad",
        ],
        "Fontanería": [
            "grifo",
            "agua",
            "fuga",
            "wc",
            "cisterna",
            "lavabo",
            "inodoro",
            "desagüe",
        ],
        "Climatización": [
            "aire",
            "calefacción",
            "frío",
            "calor",
            "split",
            "clima",
        ],
        "Mantenimiento general": [
            "silla",
            "mesa",
            "armario",
            "puerta",
            "persiana",
            "cerradura",
            "rotura",
            "roto",
        ],
        "Informática": [
            "ordenador",
            "pantalla",
            "proyector",
            "wifi",
            "internet",
            "teclado",
            "ratón",
        ],
    }

    for area, palabras in reglas.items():
        for palabra in palabras:
            if palabra in texto:
                return area

    return "Mantenimiento general"


def clasificar_prioridad(texto, prioridad_actual):
    prioridad_actual = str(
        prioridad_actual or ""
    ).strip()

    if prioridad_actual:
        return prioridad_actual

    texto = str(
        texto or ""
    ).lower()

    if any(
        palabra in texto
        for palabra in [
            "urgente",
            "peligro",
            "riesgo",
            "no funciona",
            "inundable",
        ]
    ):
        return "Alta"

    if any(
        palabra in texto
        for palabra in [
            "roto",
            "rota",
            "avería",
            "no va",
            "pierde",
            "falla",
        ]
    ):
        return "Media"

    return "Baja"


def importar_incidencias_outlook():
    """
    Importa los correos nuevos de la carpeta Outlook.

    En Render normalmente Outlook no está disponible, por lo que
    la función sale de forma segura sin romper la aplicación.
    """
    if not OUTLOOK_DISPONIBLE:
        return 0, "OUTLOOK_NO_DISPONIBLE"

    try:
        pythoncom.CoInitialize()

        outlook = win32com.client.Dispatch(
            "Outlook.Application"
        )

        namespace = outlook.GetNamespace(
            "MAPI"
        )

    except Exception as e:
        return 0, f"No se pudo conectar con Outlook: {e}"

    carpeta_objetivo = None

    def buscar_carpeta(folder, nombre):
        try:
            for sub in folder.Folders:
                if (
                    str(sub.Name or "")
                    .strip()
                    .lower()
                    == nombre
                ):
                    return sub

                resultado = buscar_carpeta(
                    sub,
                    nombre
                )

                if resultado:
                    return resultado

        except Exception:
            return None

        return None

    try:
        for cuenta in namespace.Folders:
            carpeta_objetivo = buscar_carpeta(
                cuenta,
                "incidencias pearson 22"
            )

            if carpeta_objetivo:
                break

    except Exception as e:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

        return 0, f"No se pudieron revisar las carpetas de Outlook: {e}"

    if not carpeta_objetivo:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

        return (
            0,
            "No se encontró la carpeta 'Incidencias Pearson 22'"
        )

    try:
        mensajes = carpeta_objetivo.Items
        mensajes.Sort(
            "[ReceivedTime]",
            True
        )

    except Exception as e:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

        return 0, f"No se pudieron leer los mensajes: {e}"

    conn = conectar()
    cursor = conn.cursor()

    nuevos = 0

    try:
        for msg in mensajes:
            try:
                id_outlook = str(
                    msg.EntryID
                )

                asunto = str(
                    msg.Subject or ""
                ).strip()

                cuerpo = str(
                    msg.Body or ""
                )

                remitente = str(
                    msg.SenderName or ""
                ).strip()

                fecha = str(
                    msg.ReceivedTime
                )

                datos = extraer_datos_correo(
                    cuerpo
                )

                # Comprobación explícita compatible con
                # PostgreSQL y SQLite.
                cursor.execute(
                    _sql("""
                        SELECT id
                        FROM incidencias_outlook
                        WHERE id_outlook = ?
                        LIMIT 1
                    """),
                    (id_outlook,)
                )

                if cursor.fetchone():
                    continue

                cursor.execute(
                    _sql("""
                        INSERT INTO incidencias_outlook
                        (
                            id_outlook,
                            asunto,
                            cuerpo,
                            remitente,
                            fecha,
                            centro,
                            edificio,
                            espacio,
                            prioridad,
                            solicitante
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """),
                    (
                        id_outlook,
                        datos["incidencia"] or asunto,
                        cuerpo,
                        remitente,
                        fecha,
                        datos["centro"],
                        datos["edificio"],
                        datos["espacio"],
                        datos["prioridad"],
                        datos["solicitante"],
                    )
                )

                nuevos += 1

            except Exception:
                # Un correo defectuoso no debe impedir importar
                # el resto de mensajes.
                continue

        conn.commit()
        return nuevos, "OK"

    except Exception as e:
        conn.rollback()
        return 0, f"Error importando incidencias Outlook: {e}"

    finally:
        conn.close()

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def obtener_incidencias_outlook():
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                id,
                fecha,
                asunto,
                remitente,
                centro,
                edificio,
                espacio,
                prioridad,
                solicitante,
                procesado
            FROM incidencias_outlook
            ORDER BY fecha DESC, id DESC
        """)

        return cursor.fetchall()

    finally:
        conn.close()


def crear_ot_desde_incidencia_outlook(
    id_incidencia
):
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            _sql("""
                SELECT
                    id,
                    asunto,
                    centro,
                    edificio,
                    espacio,
                    prioridad,
                    procesado
                FROM incidencias_outlook
                WHERE id = ?
            """),
            (id_incidencia,)
        )

        fila = cursor.fetchone()

        if not fila:
            return False, "No se encontró la incidencia."

        (
            _,
            asunto,
            centro,
            edificio,
            espacio,
            prioridad,
            procesado,
        ) = fila

        if int(
            procesado or 0
        ) == 1:
            return (
                False,
                "Esta incidencia ya fue procesada."
            )

        def normalizar(texto):
            return str(
                texto or ""
            ).strip().lower()

        centro_norm = normalizar(
            centro
        )

        mapa_operarios = {
            normalizar(clave): valor
            for clave, valor
            in ASIGNACION_OPERARIO_POR_CENTRO.items()
        }

        operario = mapa_operarios.get(
            centro_norm,
            ""
        )

        area = clasificar_area(
            asunto
        )

        prioridad_final = clasificar_prioridad(
            asunto,
            prioridad
        )

        numero_ot = obtener_siguiente_numero_ot(
            centro,
            "INC"
        )

        crear_orden((
            numero_ot,
            asunto,
            "Abierta",
            centro or "",
            edificio or "",
            espacio or "",
            area,
            prioridad_final,
            operario,
            "OUTLOOK",
        ))

        cursor.execute(
            _sql("""
                UPDATE incidencias_outlook
                SET procesado = 1
                WHERE id = ?
            """),
            (id_incidencia,)
        )

        conn.commit()

        return (
            True,
            f"OT {numero_ot} creada correctamente. "
            f"Área: {area}. "
            f"Operario: {operario or 'sin asignar'}."
        )

    except Exception as e:
        conn.rollback()
        return False, f"No se pudo crear la OT: {e}"

    finally:
        conn.close()


def importar_y_crear_ots_automaticamente():
    """
    Ejecuta el flujo completo:
    Outlook -> incidencias_outlook -> OT.

    En entornos sin Outlook (como Render) devuelve éxito controlado.
    """
    if not OUTLOOK_DISPONIBLE:
        return (
            True,
            "Outlook no disponible en este entorno."
        )

    nuevos, mensaje = importar_incidencias_outlook()

    if mensaje == "OUTLOOK_NO_DISPONIBLE":
        return (
            True,
            "Outlook no disponible en este entorno."
        )

    if mensaje != "OK":
        return (
            False,
            f"Error al importar Outlook: {mensaje}"
        )

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM incidencias_outlook
            WHERE procesado = 0
            ORDER BY fecha DESC, id DESC
        """)

        pendientes = cursor.fetchall()

    finally:
        conn.close()

    creadas = 0
    errores = []

    for fila in pendientes:
        id_incidencia = fila[0]

        ok, resultado = crear_ot_desde_incidencia_outlook(
            id_incidencia
        )

        if ok:
            creadas += 1
        else:
            errores.append(
                resultado
            )

    texto = (
        f"Importadas: {nuevos}. "
        f"OTs creadas: {creadas}."
    )

    if errores:
        texto += (
            " Errores: "
            + " | ".join(
                errores
            )
        )

    return True, texto
