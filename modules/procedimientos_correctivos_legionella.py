import unicodedata


TIPO_TEMPERATURA = "temperatura"
TIPO_PURGA = "purga"
TIPO_CLORO = "cloro"
TIPO_AFS_TEMPERATURA = "afs_temperatura"
TIPO_BOMBA = "bomba_recirculacion"
TIPO_VISUAL = "visual_limpieza"
TIPO_GENERICO = "generico"


def normalizar_texto(texto):
    texto = str(texto or "").strip().lower()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def extraer_tarea_correctivo(descripcion):
    """
    Ejemplo:
    CORRECTIVO LEGIONELLA - Purga - Purga no realizada - Acumulador 800 L
    -> Purga
    """
    texto = str(descripcion or "").strip()
    partes = [parte.strip() for parte in texto.split(" - ")]

    if (
        len(partes) >= 2
        and partes[0].upper().startswith("CORRECTIVO LEGIONELLA")
    ):
        return partes[1]

    return ""


def identificar_tipo_correctivo(descripcion):
    tarea = normalizar_texto(extraer_tarea_correctivo(descripcion))
    descripcion_normalizada = normalizar_texto(descripcion)
    texto = f"{tarea} {descripcion_normalizada}"

    # El orden importa: Purga debe detectarse antes de palabras genéricas
    # como acumulador, que también pueden aparecer en la ubicación.
    if "purga" in tarea or "purga no realizada" in texto:
        return TIPO_PURGA

    if "cloro" in texto:
        return TIPO_CLORO

    if (
        "control afs" in tarea
        or "temperatura afs" in texto
        or "temperatura afch" in texto
        or "agua fria" in texto
    ):
        return TIPO_AFS_TEMPERATURA

    if "bomba" in texto or "recircul" in texto:
        return TIPO_BOMBA

    if any(
        palabra in texto
        for palabra in (
            "revision visual",
            "limpieza",
            "desinfeccion",
            "incrustacion",
            "corrosion",
        )
    ):
        return TIPO_VISUAL

    if any(
        palabra in texto
        for palabra in (
            "temperatura",
            "sala acs",
            "acumulador",
            "retorno",
            "impulsion",
            "acs terminal",
        )
    ):
        return TIPO_TEMPERATURA

    return TIPO_GENERICO


def validar_correctivo_especializado(tipo_correctivo, datos):
    """
    Valida los procedimientos nuevos.

    El correctivo de temperatura se mantiene en el sistema histórico y
    se valida desde su tabla actual para conservar compatibilidad.
    """
    datos = datos or {}

    if tipo_correctivo == TIPO_PURGA:
        return bool(
            datos.get("realizada")
            and datos.get("salida_continua")
            and datos.get("cierre")
            and datos.get("sin_fugas")
            and datos.get("resultado") == "Correcto"
        )

    if tipo_correctivo == TIPO_CLORO:
        return bool(
            datos.get("confirmar")
            and datos.get("repetir")
            and str(datos.get("causa") or "").strip()
        )

    if tipo_correctivo == TIPO_AFS_TEMPERATURA:
        return bool(
            datos.get("confirmar")
            and datos.get("repetir")
            and str(datos.get("causa") or "").strip()
        )

    if tipo_correctivo == TIPO_BOMBA:
        return bool(
            datos.get("bomba")
            and datos.get("circulacion")
            and datos.get("resultado") == "Funcionando"
            and str(datos.get("causa") or "").strip()
        )

    if tipo_correctivo == TIPO_VISUAL:
        return bool(
            datos.get("defecto")
            and datos.get("revisar")
            and datos.get("limpiar")
            and datos.get("sin_fugas")
            and datos.get("resultado") == "Correcto"
        )

    if tipo_correctivo == TIPO_GENERICO:
        return bool(
            datos.get("identificado")
            and datos.get("actuacion")
            and datos.get("verificacion")
            and datos.get("resultado") == "Correcto"
            and str(datos.get("causa") or "").strip()
        )

    return False
