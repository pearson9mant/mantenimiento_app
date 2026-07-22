import re
import unicodedata


AREAS_OT = [
    "Electricidad",
    "Fontanería",
    "Climatización",
    "Cerrajería",
    "Pintura",
    "Carpintería",
    "Albañilería",
    "Cristalería",
    "Legionella",
    "Preventivo",
    "Jardinería",
    "Limpieza",
    "Seguridad",
    "Informática",
    "Audiovisuales",
    "Mobiliario",
    "Equipamiento",
    "ACS",
    "Otros",
]


PALABRAS_POR_AREA = {
    "Fontanería": [
        "fuga",
        "perdida de agua",
        "pierde agua",
        "gotea",
        "goteo",
        "grifo",
        "lavabo",
        "lavamanos",
        "fregadero",
        "pica",
        "wc",
        "water",
        "inodoro",
        "urinario",
        "cisterna",
        "fluxor",
        "presto",
        "desague",
        "atasco",
        "atascado",
        "sifon",
        "tuberia",
        "tubo de agua",
        "llave de paso",
        "valvula de agua",
        "latiguillo",
        "manguito",
        "sumidero",
        "bajante",
        "arqueta",
        "ducha",
        "alcachofa",
        "manguera",
        "contador de agua",
        "presion de agua",
        "no sale agua",
        "agua caliente",
        "agua fria",
    ],

    "Electricidad": [
        "enchufe",
        "interruptor",
        "conmutador",
        "pulsador",
        "luz",
        "luces",
        "lampara",
        "bombilla",
        "fluorescente",
        "downlight",
        "led",
        "luminaria",
        "no enciende",
        "sin corriente",
        "corriente electrica",
        "electricidad",
        "electrico",
        "electrica",
        "cable",
        "cableado",
        "cuadro electrico",
        "magnetotermico",
        "diferencial",
        "automatico",
        "fusible",
        "contactor",
        "rele",
        "sensor de presencia",
        "temporizador",
        "emergencia",
        "luz de emergencia",
        "toma de corriente",
        "cortocircuito",
        "salta el diferencial",
    ],

    "Climatización": [
        "aire acondicionado",
        "split",
        "climatizacion",
        "climatizador",
        "calefaccion",
        "radiador",
        "termostato",
        "ventilacion",
        "ventilador",
        "extractor",
        "fancoil",
        "fan coil",
        "bomba de calor",
        "unidad interior",
        "unidad exterior",
        "conducto de aire",
        "rejilla de aire",
        "no enfria",
        "no calienta",
        "hace frio",
        "hace calor",
        "temperatura aula",
        "caldera",
    ],

    "Cerrajería": [
        "cerradura",
        "bombin",
        "llave",
        "pestillo",
        "cerrojo",
        "maneta",
        "picaporte",
        "candado",
        "puerta no cierra",
        "puerta no abre",
        "no cierra la puerta",
        "no abre la puerta",
        "puerta bloqueada",
        "cierre de puerta",
        "muelle de puerta",
        "retenedor",
        "barra antipánico",
        "barra antipanic",
        "bisagra de puerta",
    ],

    "Pintura": [
        "pintar",
        "pintura",
        "repintar",
        "desconchado",
        "desconchada",
        "pared manchada",
        "pared sucia",
        "techo manchado",
        "humedad en pared",
        "grafiti",
        "graffiti",
        "barnizar",
        "barniz",
        "esmalte",
        "color de pared",
    ],

    "Carpintería": [
        "carpinteria",
        "madera",
        "puerta de madera",
        "marco de madera",
        "rodapie",
        "zócalo",
        "zocalo",
        "tablero",
        "estante de madera",
        "armario de madera",
        "cajon",
        "cajón",
        "persiana",
        "lama de persiana",
    ],

    "Albañilería": [
        "albanileria",
        "albañileria",
        "rachola",
        "azulejo",
        "baldosa",
        "gres",
        "mortero",
        "cemento",
        "yeso",
        "pladur",
        "grieta",
        "fisura",
        "agujero en pared",
        "pared rota",
        "techo roto",
        "suelo roto",
        "escalon",
        "escalón",
        "alicatado",
        "rejuntar",
        "junta de baldosa",
        "zanja",
        "obra",
    ],

    "Cristalería": [
        "cristal",
        "vidrio",
        "ventana rota",
        "cristal roto",
        "espejo",
        "mampara",
        "metacrilato",
        "policarbonato",
    ],

    "Jardinería": [
        "jardin",
        "jardineria",
        "cesped",
        "césped",
        "planta",
        "arbol",
        "árbol",
        "arbusto",
        "poda",
        "podar",
        "riego",
        "aspersor",
        "gotero",
        "jardinera",
        "hojas",
        "rama",
        "tierra",
    ],

    "Limpieza": [
        "limpieza",
        "limpiar",
        "suciedad",
        "sucio",
        "basura",
        "papelera",
        "desinfeccion",
        "desinfección",
        "mal olor",
        "derrame",
        "recogida de residuos",
    ],

    "Seguridad": [
        "extintor",
        "alarma",
        "alarma de incendios",
        "detector de humo",
        "detector de incendios",
        "central de incendios",
        "pulsador de alarma",
        "boca de incendio",
        "bie",
        "evacuacion",
        "evacuación",
        "señal de emergencia",
        "camara de seguridad",
        "cámara de seguridad",
        "control de acceso",
        "interfono",
        "videoportero",
    ],

    "Informática": [
        "ordenador",
        "pc",
        "portatil",
        "portátil",
        "monitor",
        "pantalla ordenador",
        "impresora",
        "teclado",
        "raton",
        "ratón",
        "wifi",
        "internet",
        "red",
        "router",
        "switch de red",
        "punto de red",
        "rj45",
        "telefono ip",
        "software",
    ],

    "Audiovisuales": [
        "proyector",
        "pantalla de proyeccion",
        "pantalla de proyección",
        "altavoz",
        "microfono",
        "micrófono",
        "mesa de sonido",
        "equipo de sonido",
        "amplificador",
        "television",
        "televisión",
        "hdmi",
        "audio",
        "video",
        "vídeo",
        "pizarra digital",
    ],

    "Mobiliario": [
        "mesa",
        "silla",
        "pupitre",
        "armario",
        "estanteria",
        "estantería",
        "mueble",
        "cajonera",
        "banco",
        "taburete",
        "perchero",
        "taquilla",
        "rueda de silla",
    ],

    "Equipamiento": [
        "electrodomestico",
        "electrodoméstico",
        "lavadora",
        "secadora",
        "lavavajillas",
        "horno",
        "microondas",
        "nevera",
        "frigorifico",
        "frigorífico",
        "congelador",
        "campana extractora",
        "maquina",
        "máquina",
        "motor",
        "bomba",
    ],

    "ACS": [
        "acs",
        "agua caliente sanitaria",
        "acumulador",
        "deposito de agua caliente",
        "depósito de agua caliente",
        "retorno de acs",
        "impulsion de acs",
        "impulsión de acs",
        "recirculacion",
        "recirculación",
        "mezcladora",
        "valvula mezcladora",
        "válvula mezcladora",
    ],

    "Legionella": [
        "legionella",
        "cloro residual",
        "choque termico",
        "choque térmico",
        "control de temperatura acs",
        "muestra de agua",
        "analitica de agua",
        "analítica de agua",
        "punto terminal",
    ],

    "Preventivo": [
        "preventivo",
        "mantenimiento preventivo",
        "revision periodica",
        "revisión periódica",
        "inspeccion periodica",
        "inspección periódica",
    ],
}


def normalizar_texto_area(valor):
    """
    Convierte el texto a minúsculas, elimina tildes y unifica espacios.
    """

    texto = str(valor or "").strip().lower()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9\s\-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def normalizar_nombre_area(area):
    """
    Devuelve el nombre oficial del área cuando reconoce una variante.
    """

    area_normalizada = normalizar_texto_area(area)

    equivalencias = {
        "electricidad": "Electricidad",
        "electrico": "Electricidad",
        "electrica": "Electricidad",

        "fontaneria": "Fontanería",
        "agua": "Fontanería",

        "climatizacion": "Climatización",
        "clima": "Climatización",

        "cerrajeria": "Cerrajería",

        "pintura": "Pintura",

        "carpinteria": "Carpintería",

        "albanileria": "Albañilería",
        "obra": "Albañilería",

        "cristaleria": "Cristalería",

        "legionella": "Legionella",

        "preventivo": "Preventivo",
        "preventiva": "Preventivo",

        "jardineria": "Jardinería",

        "limpieza": "Limpieza",

        "seguridad": "Seguridad",

        "informatica": "Informática",

        "audiovisuales": "Audiovisuales",
        "audiovisual": "Audiovisuales",

        "mobiliario": "Mobiliario",

        "equipamiento": "Equipamiento",

        "acs": "ACS",

        "otros": "Otros",
        "otro": "Otros",
    }

    return equivalencias.get(area_normalizada, str(area or "").strip())


def sugerir_area_ot(
    descripcion="",
    area_actual="",
    origen="",
    tipo_orden=""
):
    """
    Devuelve el área más adecuada para una OT.

    Reglas:
    - Respeta un área explícita distinta de Otros.
    - Legionella y Preventivo se priorizan por origen.
    - Las órdenes externas conservan su área cuando está indicada.
    - Solo clasifica automáticamente cuando el área está vacía o es Otros.
    """

    area_limpia = normalizar_nombre_area(area_actual)
    origen_txt = normalizar_texto_area(origen)
    tipo_txt = normalizar_texto_area(tipo_orden)

    # -----------------------------------------
    # ÁREAS ESPECIALES SEGÚN EL ORIGEN
    # -----------------------------------------
    if origen_txt in ["legionella", "leg"]:
        return "Legionella"

    if origen_txt in ["preventivo", "prev"]:
        return "Preventivo"

    # -----------------------------------------
    # RESPETAR UN ÁREA YA INDICADA
    # -----------------------------------------
    if area_limpia and area_limpia != "Otros":
        return area_limpia

    texto = normalizar_texto_area(descripcion)

    if not texto:
        return area_limpia or "Otros"

    # -----------------------------------------
    # BUSCAR COINCIDENCIAS
    # -----------------------------------------
    puntuaciones = {}

    for area, palabras in PALABRAS_POR_AREA.items():
        puntuacion = 0

        for palabra in palabras:
            palabra_normalizada = normalizar_texto_area(palabra)

            if not palabra_normalizada:
                continue

            if palabra_normalizada in texto:
                # Las frases completas pesan más que una palabra suelta.
                if " " in palabra_normalizada:
                    puntuacion += 3
                else:
                    puntuacion += 1

        if puntuacion > 0:
            puntuaciones[area] = puntuacion

    if not puntuaciones:
        return "Otros"

    # Devuelve el área con mayor puntuación.
    return max(
        puntuaciones,
        key=puntuaciones.get
    )
