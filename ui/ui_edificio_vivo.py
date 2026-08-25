import html
import re
import unicodedata

import streamlit as st

from modules.espacios import obtener_plantas_config


# =========================================================
# ESTRUCTURA DEL COLEGIO
# =========================================================

EDIFICIOS = {
    "Pearson 22": {
        "Infantil / Primaria": [
            "Terrado",
            "Planta 5",
            "Planta 4",
            "Planta 3",
            "Planta 2",
            "Planta 1",
        ],
        "Llar": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
    },
    "Pearson 9": {
        # Estructura física real de los tres edificios principales.
        # El Anexo Servicios se pinta aparte porque no pertenece a A/B/C.
        "Edificio A": [
            "Planta 2",
            "Planta 1",
        ],
        "Edificio B": [
            "Planta 2",
            "Planta 1",
        ],
        "Edificio C": [
            "Planta 2",
            "Planta 1",
        ],
    },
}


# Zonas físicas del anexo de Pearson 9, en el orden real del plano.
ZONAS_ANEXO_P9 = [
    "Taller",
    "Vestuarios chicas",
    "Sala calderas",
    "Vestuarios chicos",
]

ALIASES_ZONAS_ANEXO_P9 = {
    "Taller": [
        "taller",
    ],
    "Vestuarios chicas": [
        "vestuarios chicas",
        "vestuario chicas",
        "duchas femeninas",
        "duchas femenina",
        "duchas chicas",
    ],
    "Sala calderas": [
        "sala calderas",
        "sala de calderas",
        "sala tecnica",
        "sala técnica",
    ],
    "Vestuarios chicos": [
        "vestuarios chicos",
        "vestuario chicos",
        "duchas masculinas",
        "duchas masculina",
        "duchas chicos",
    ],
}


# =========================================================
# NORMALIZACIÓN
# =========================================================

def _norm(texto):
    texto = str(texto or "").strip().lower()

    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

    for caracter in [
        "/",
        "\\",
        "-",
        "_",
        ".",
        ",",
        ";",
        ":",
    ]:
        texto = texto.replace(caracter, " ")

    return " ".join(texto.split())


def normalizar_centro(valor):
    texto = _norm(valor)

    if (
        texto in {
            "pearson 22",
            "pearson22",
            "p22",
            "pearson numero 22",
        }
        or "pearson 22" in texto
    ):
        return "Pearson 22"

    if (
        texto in {
            "pearson 9",
            "pearson9",
            "p9",
            "pearson numero 9",
        }
        or "pearson 9" in texto
    ):
        return "Pearson 9"

    return str(valor or "").strip()


def normalizar_edificio(valor, centro=""):
    texto = _norm(valor)

    # Pearson 9 tiene un anexo de servicios independiente de A/B/C.
    # Nunca debe confundirse con la Llar de Pearson 22.
    if centro == "Pearson 9":
        if any(
            alias in texto
            for alias in [
                "anexo",
                "anexo servicios",
                "taller",
                "vestuario",
                "vestuarios",
                "sala calderas",
                "sala de calderas",
                "sala tecnica",
            ]
        ):
            return "Anexo Servicios"

    if any(
        alias in texto
        for alias in [
            "llar",
            "guarderia",
            "anexo",
        ]
    ):
        return "Llar"

    if any(
        alias in texto
        for alias in [
            "infantil primaria",
            "infantil",
            "primaria",
            "edificio infantil",
            "edificio primaria",
            "edif infantil",
            "edif primaria",
        ]
    ):
        return "Infantil / Primaria"

    if any(
        alias in texto
        for alias in [
            "edificio a",
            "edif a",
            "bloque a",
            "pabellon a",
            "modulo a",
        ]
    ):
        return "Edificio A"

    if any(
        alias in texto
        for alias in [
            "edificio b",
            "edif b",
            "bloque b",
            "pabellon b",
            "modulo b",
        ]
    ):
        return "Edificio B"

    if any(
        alias in texto
        for alias in [
            "edificio c",
            "edif c",
            "bloque c",
            "pabellon c",
            "modulo c",
        ]
    ):
        return "Edificio C"

    if centro == "Pearson 22":
        return "Infantil / Primaria"

    if centro == "Pearson 9":
        return "Edificio A"

    return str(valor or "").strip()


def normalizar_planta(valor):
    texto = _norm(valor)

    if not texto:
        return ""

    if any(
        palabra in texto
        for palabra in [
            "terrado",
            "cubierta",
            "azotea",
            "tejado",
        ]
    ):
        return "Terrado"

    patrones = [
        r"\bplanta\s*([0-9])\b",
        r"\bpiso\s*([0-9])\b",
        r"\bnivel\s*([0-9])\b",
        r"\bp\s*([0-9])\b",
    ]

    for patron in patrones:
        coincidencia = re.search(patron, texto)

        if coincidencia:
            return f"Planta {int(coincidencia.group(1))}"

    return ""


def etiqueta_planta(planta):
    if planta == "Terrado":
        return "T"

    return str(planta).replace("Planta ", "P")



def _mapa_visibilidad_plantas():
    """
    Devuelve un mapa {(centro, edificio, planta): bool} a partir de
    Configuración > Espacios > Plantas.

    Si una planta no tiene configuración explícita, se considera visible
    para mantener compatibilidad con estructuras antiguas.
    """
    mapa = {}

    try:
        filas = obtener_plantas_config()
    except Exception:
        filas = []

    for fila in filas or []:
        try:
            _id, centro, edificio, planta, visible = fila
        except Exception:
            continue

        centro_n = normalizar_centro(centro)
        edificio_n = normalizar_edificio(edificio, centro_n)
        planta_n = normalizar_planta(planta)

        if not centro_n or not edificio_n or not planta_n:
            continue

        try:
            visible_bool = bool(int(visible))
        except Exception:
            visible_bool = bool(visible)

        mapa[
            (
                centro_n,
                edificio_n,
                planta_n,
            )
        ] = visible_bool

    return mapa


def _plantas_visibles_edificio(
    centro,
    edificio,
    plantas,
    mapa_visibilidad,
):
    """
    Filtra únicamente las plantas marcadas como visibles.
    """
    centro_n = normalizar_centro(centro)
    edificio_n = normalizar_edificio(edificio, centro_n)

    resultado = []

    for planta in plantas:
        planta_n = normalizar_planta(planta)

        clave = (
            centro_n,
            edificio_n,
            planta_n,
        )

        visible = mapa_visibilidad.get(
            clave,
            True,
        )

        if visible:
            resultado.append(planta)

    return resultado


# =========================================================
# ESTADO VISUAL
# =========================================================

def _estado_planta(datos):
    total = int(datos.get("total") or 0)
    ejecutables = int(datos.get("ejecutables") or 0)
    bloqueadas = int(datos.get("bloqueadas") or 0)
    urgentes = int(datos.get("urgentes") or 0)
    altas = int(datos.get("altas") or 0)
    en_curso = int(datos.get("en_curso") or 0)

    if en_curso > 0:
        return "curso"

    if urgentes > 0:
        return "critica"

    if altas > 0 or ejecutables >= 3:
        return "atencion"

    if ejecutables > 0:
        return "seguimiento"

    if bloqueadas > 0 or total > 0:
        return "bloqueada"

    return "correcta"


def _icono_estado(estado):
    return {
        "correcta": "🟢",
        "seguimiento": "🟡",
        "atencion": "🟠",
        "critica": "🔴",
        "curso": "🔵",
        "bloqueada": "📦",
    }.get(estado, "🟢")


def _texto_contador(datos):
    total = int(datos.get("total") or 0)
    ejecutables = int(datos.get("ejecutables") or 0)

    if total == 0:
        return "✓"

    cantidad = ejecutables if ejecutables > 0 else total
    return f"({cantidad})"


# =========================================================
# APERTURA DE PLANTA SIN RECARGAR LA URL
# =========================================================

def _abrir_planta(
    centro,
    edificio,
    planta,
    ordenes,
    ordenes_ejecutables,
):
    st.session_state["colegio_vivo_vista"] = "planta"

    st.session_state["colegio_vivo_centro"] = centro
    st.session_state["colegio_vivo_edificio"] = edificio
    st.session_state["colegio_vivo_planta"] = planta

    # Se conserva para resaltar la última planta utilizada al volver al mapa.
    st.session_state["colegio_vivo_ultima_centro"] = centro
    st.session_state["colegio_vivo_ultimo_edificio"] = edificio
    st.session_state["colegio_vivo_ultima_planta"] = planta

    st.session_state["colegio_vivo_ordenes_planta"] = list(
        ordenes or []
    )

    st.session_state["colegio_vivo_ejecutables_planta"] = list(
        ordenes_ejecutables or []
    )


def volver_colegio_vivo():
    st.session_state["colegio_vivo_vista"] = "mapa"

    st.session_state.pop(
        "colegio_vivo_centro",
        None,
    )
    st.session_state.pop(
        "colegio_vivo_edificio",
        None,
    )
    st.session_state.pop(
        "colegio_vivo_planta",
        None,
    )
    st.session_state.pop(
        "colegio_vivo_ordenes_planta",
        None,
    )
    st.session_state.pop(
        "colegio_vivo_ejecutables_planta",
        None,
    )


# =========================================================
# ANEXO SERVICIOS · PEARSON 9
# =========================================================

def _zona_anexo_desde_espacio(espacio):
    """
    Relaciona el espacio real de una OT con una de las cuatro zonas
    del Anexo Servicios de P9. No modifica la base de datos.
    """
    texto = _norm(espacio)

    if not texto:
        return ""

    for zona, aliases in ALIASES_ZONAS_ANEXO_P9.items():
        for alias in aliases:
            alias_n = _norm(alias)

            if texto == alias_n or alias_n in texto:
                return zona

    return ""


def _clave_ot_visual(ot):
    if not isinstance(ot, dict):
        try:
            ot = dict(ot)
        except Exception:
            return str(ot)

    return str(
        ot.get("id")
        or ot.get("numero_ot")
        or ot.get("numero")
        or repr(ot)
    )


def _ordenes_unicas_anexo(lista):
    resultado = []
    vistas = set()

    for ot in lista or []:
        try:
            ot_dict = dict(ot)
        except Exception:
            continue

        clave = _clave_ot_visual(ot_dict)

        if clave in vistas:
            continue

        vistas.add(clave)
        resultado.append(ot_dict)

    return resultado


def _datos_zona_anexo_p9(resumen, zona):
    """
    Reconstruye el estado de cada zona del anexo a partir de las OT
    que ya llegan al Colegio Vivo. Esto permite aprovechar órdenes
    antiguas sin reescribirlas ni moverlas en la base de datos.
    """
    ordenes = []
    ejecutables = []
    bloqueadas = []

    for clave, datos in (resumen or {}).items():
        try:
            centro_clave = normalizar_centro(clave[0])
        except Exception:
            continue

        if centro_clave != "Pearson 9":
            continue

        for nombre_lista, destino in [
            ("ordenes", ordenes),
            ("ordenes_ejecutables", ejecutables),
            ("ordenes_bloqueadas", bloqueadas),
        ]:
            for ot in datos.get(nombre_lista, []) or []:
                try:
                    ot_dict = dict(ot)
                except Exception:
                    continue

                espacio_ot = (
                    ot_dict.get("espacio")
                    or ot_dict.get("aula")
                    or ot_dict.get("ubicacion")
                    or ""
                )

                if _zona_anexo_desde_espacio(espacio_ot) == zona:
                    destino.append(ot_dict)

    ordenes = _ordenes_unicas_anexo(ordenes)
    ejecutables = _ordenes_unicas_anexo(ejecutables)
    bloqueadas = _ordenes_unicas_anexo(bloqueadas)

    # Compatibilidad con resúmenes antiguos que no separaban
    # ejecutables y bloqueadas.
    if ordenes and not ejecutables and not bloqueadas:
        estados_bloqueados = {
            "pendiente material",
            "pendiente proveedor",
            "pendiente presupuesto",
            "avisado",
        }
        estados_cierre = {
            "finalizada",
            "finalizado",
            "cerrada",
            "cerrado",
            "cancelada",
            "cancelado",
        }

        for ot in ordenes:
            estado = _norm(ot.get("estado"))

            if estado in estados_cierre:
                continue

            if estado in estados_bloqueados:
                bloqueadas.append(ot)
            else:
                ejecutables.append(ot)

        ejecutables = _ordenes_unicas_anexo(ejecutables)
        bloqueadas = _ordenes_unicas_anexo(bloqueadas)

    urgentes = sum(
        1
        for ot in ordenes
        if "urgente" in _norm(ot.get("prioridad"))
    )

    altas = sum(
        1
        for ot in ordenes
        if "alta" in _norm(ot.get("prioridad"))
    )

    en_curso = sum(
        1
        for ot in ordenes
        if _norm(ot.get("estado")) == "en curso"
    )

    return {
        "total": len(ordenes),
        "ejecutables": len(ejecutables),
        "bloqueadas": len(bloqueadas),
        "en_curso": en_curso,
        "urgentes": urgentes,
        "altas": altas,
        "ordenes": ordenes,
        "ordenes_ejecutables": ejecutables,
        "ordenes_bloqueadas": bloqueadas,
    }


def _pintar_anexo_servicios_p9(resumen):
    """
    Dibuja el anexo en el orden físico real:
    Taller → Vestuarios chicas → Sala calderas → Vestuarios chicos.
    """
    st.markdown(
        '<div class="cv-annex-wrap">'
        '<div class="cv-annex-title">ANEXO SERVICIOS · PLANTA ÚNICA</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Contenedor con key propia para poder hacer el anexo responsive
    # sin alterar los tres edificios principales.
    with st.container(key="cv_anexo_p9_mobile"):
        columnas = st.columns(
            len(ZONAS_ANEXO_P9),
            gap="small",
        )

        iconos_zona = {
            "Taller": "🔧",
            "Vestuarios chicas": "🚿",
            "Sala calderas": "🔥",
            "Vestuarios chicos": "🚿",
        }

        for columna, zona in zip(
            columnas,
            ZONAS_ANEXO_P9,
        ):
            datos = _datos_zona_anexo_p9(
                resumen,
                zona,
            )

            estado = _estado_planta(datos)
            icono_estado = _icono_estado(estado)
            contador = _texto_contador(datos)
            icono_zona = iconos_zona.get(zona, "📍")

            zona_activa = (
                st.session_state.get("colegio_vivo_ultima_centro") == "Pearson 9"
                and st.session_state.get("colegio_vivo_ultimo_edificio") == "Anexo Servicios"
                and st.session_state.get("colegio_vivo_ultima_planta") == zona
            )

            with columna:
                st.button(
                    f"{icono_estado} {icono_zona} {zona} {contador}",
                    key=f"cv_anexo_p9_{zona}",
                    type="primary" if zona_activa else "secondary",
                    use_container_width=True,
                    on_click=_abrir_planta,
                    args=(
                        "Pearson 9",
                        "Anexo Servicios",
                        zona,
                        datos.get("ordenes", []),
                        datos.get("ordenes_ejecutables", []),
                    ),
                )


# =========================================================
# ZONAS EXTERNAS / ANEXAS · PEARSON 22
# =========================================================

ZONAS_EXTERNAS_P22_PREFERIDAS = [
    ("Acceso Pearson 22", "🚪"),
    ("Acceso Patio Fútbol", "⚽"),
    ("Parking", "🚗"),
]


def _es_planta_fisica_p22(planta):
    """
    Indica si una entrada de plantas_config pertenece al dibujo físico
    ya existente del edificio.

    Todo lo que NO sea una planta física puede mostrarse como zona
    externa/anexa sin deformar el edificio.
    """
    planta_n = normalizar_planta(planta)

    return bool(
        planta_n
        and planta_n in {
            "Terrado",
            "Planta 0",
            "Planta 1",
            "Planta 2",
            "Planta 3",
            "Planta 4",
            "Planta 5",
        }
    )


def _zonas_externas_configuradas_p22():
    """
    Lee Configuración > Espacios > Plantas y devuelve las zonas visibles
    de Pearson 22 que no corresponden a plantas físicas.

    Se priorizan los nombres:
    - Acceso Pearson 22
    - Acceso Patio Fútbol
    - Parking

    Pero cualquier futura zona visible no física también podrá aparecer.
    """
    try:
        filas = obtener_plantas_config()
    except Exception:
        filas = []

    zonas = []
    vistas = set()

    for fila in filas or []:
        try:
            _id, centro, edificio, planta, visible = fila
        except Exception:
            continue

        centro_n = normalizar_centro(centro)

        if centro_n != "Pearson 22":
            continue

        try:
            visible_bool = bool(int(visible))
        except Exception:
            visible_bool = bool(visible)

        if not visible_bool:
            continue

        planta_txt = str(planta or "").strip()

        if not planta_txt:
            continue

        if _es_planta_fisica_p22(planta_txt):
            continue

        clave = _norm(planta_txt)

        if not clave or clave in vistas:
            continue

        vistas.add(clave)
        zonas.append(
            {
                "nombre": planta_txt,
                "edificio": normalizar_edificio(
                    edificio,
                    centro_n,
                ),
            }
        )

    # Orden estable: primero las zonas acordadas, después cualquier otra.
    prioridad = {
        _norm(nombre): indice
        for indice, (nombre, _icono) in enumerate(
            ZONAS_EXTERNAS_P22_PREFERIDAS
        )
    }

    zonas.sort(
        key=lambda item: (
            prioridad.get(
                _norm(item["nombre"]),
                999,
            ),
            _norm(item["nombre"]),
        )
    )

    return zonas


def _icono_zona_externa_p22(nombre):
    nombre_n = _norm(nombre)

    for nombre_pref, icono in ZONAS_EXTERNAS_P22_PREFERIDAS:
        if _norm(nombre_pref) == nombre_n:
            return icono

    if "parking" in nombre_n or "aparcamiento" in nombre_n:
        return "🚗"

    if "futbol" in nombre_n:
        return "⚽"

    if "acceso" in nombre_n or "entrada" in nombre_n:
        return "🚪"

    if "patio" in nombre_n or "exterior" in nombre_n:
        return "🌳"

    return "📍"


def _datos_zona_externa_p22(
    resumen,
    zona,
    edificio_config="",
):
    """
    Recupera las OT de una zona externa usando los datos que ya recibe
    Colegio Vivo.

    No modifica la base de datos ni mueve órdenes.
    """
    zona_n = _norm(zona)

    ordenes = []
    ejecutables = []
    bloqueadas = []

    def _coincide_zona_ot(ot_dict):
        valores = [
            ot_dict.get("planta"),
            ot_dict.get("espacio"),
            ot_dict.get("aula"),
            ot_dict.get("ubicacion"),
        ]

        for valor in valores:
            valor_n = _norm(valor)

            if not valor_n:
                continue

            if valor_n == zona_n:
                return True

            # Compatibilidad con ubicaciones descriptivas más antiguas.
            if zona_n and zona_n in valor_n:
                return True

        return False

    for clave, datos in (resumen or {}).items():
        try:
            centro_clave = normalizar_centro(
                clave[0]
            )
        except Exception:
            continue

        if centro_clave != "Pearson 22":
            continue

        for nombre_lista, destino in [
            ("ordenes", ordenes),
            ("ordenes_ejecutables", ejecutables),
            ("ordenes_bloqueadas", bloqueadas),
        ]:
            for ot in datos.get(
                nombre_lista,
                [],
            ) or []:
                try:
                    ot_dict = dict(ot)
                except Exception:
                    continue

                if not _coincide_zona_ot(
                    ot_dict
                ):
                    continue

                destino.append(
                    ot_dict
                )

    def _unicas(lista):
        resultado = []
        vistas = set()

        for ot in lista:
            clave_ot = _clave_ot_visual(
                ot
            )

            if clave_ot in vistas:
                continue

            vistas.add(
                clave_ot
            )
            resultado.append(
                ot
            )

        return resultado

    ordenes = _unicas(ordenes)
    ejecutables = _unicas(ejecutables)
    bloqueadas = _unicas(bloqueadas)

    # Compatibilidad con resúmenes que no separan aún los estados.
    if ordenes and not ejecutables and not bloqueadas:
        estados_bloqueados = {
            "pendiente material",
            "pendiente proveedor",
            "pendiente presupuesto",
            "avisado",
        }

        estados_cierre = {
            "finalizada",
            "finalizado",
            "cerrada",
            "cerrado",
            "cancelada",
            "cancelado",
        }

        for ot in ordenes:
            estado = _norm(
                ot.get("estado")
            )

            if estado in estados_cierre:
                continue

            if estado in estados_bloqueados:
                bloqueadas.append(
                    ot
                )
            else:
                ejecutables.append(
                    ot
                )

        ejecutables = _unicas(
            ejecutables
        )
        bloqueadas = _unicas(
            bloqueadas
        )

    urgentes = sum(
        1
        for ot in ordenes
        if "urgente" in _norm(
            ot.get("prioridad")
        )
    )

    altas = sum(
        1
        for ot in ordenes
        if "alta" in _norm(
            ot.get("prioridad")
        )
    )

    en_curso = sum(
        1
        for ot in ordenes
        if _norm(
            ot.get("estado")
        ) == "en curso"
    )

    return {
        "total": len(ordenes),
        "ejecutables": len(ejecutables),
        "bloqueadas": len(bloqueadas),
        "en_curso": en_curso,
        "urgentes": urgentes,
        "altas": altas,
        "ordenes": ordenes,
        "ordenes_ejecutables": ejecutables,
        "ordenes_bloqueadas": bloqueadas,
    }


def _pintar_zonas_externas_p22(
    resumen,
):
    """
    Dibuja las zonas externas debajo de los edificios.

    El dibujo físico de los edificios no se modifica.
    Si no hay zonas externas configuradas, no muestra nada.
    """
    zonas = _zonas_externas_configuradas_p22()

    if not zonas:
        return

    st.markdown(
        '<div class="cv-annex-wrap">'
        '<div class="cv-annex-title">ZONAS EXTERIORES / ANEXAS</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(
        key="cv_zonas_externas_p22"
    ):
        columnas = st.columns(
            len(zonas),
            gap="small",
        )

        for columna, zona_info in zip(
            columnas,
            zonas,
        ):
            zona = zona_info["nombre"]
            edificio_config = zona_info.get(
                "edificio",
                "",
            )

            datos = _datos_zona_externa_p22(
                resumen,
                zona,
                edificio_config=edificio_config,
            )

            estado = _estado_planta(
                datos
            )
            icono_estado = _icono_estado(
                estado
            )
            contador = _texto_contador(
                datos
            )
            icono_zona = _icono_zona_externa_p22(
                zona
            )

            zona_activa = (
                st.session_state.get(
                    "colegio_vivo_ultima_centro"
                ) == "Pearson 22"
                and st.session_state.get(
                    "colegio_vivo_ultimo_edificio"
                ) == "Zonas exteriores"
                and st.session_state.get(
                    "colegio_vivo_ultima_planta"
                ) == zona
            )

            with columna:
                st.button(
                    f"{icono_estado} {icono_zona} "
                    f"{zona} {contador}",
                    key=(
                        "cv_zona_externa_p22_"
                        f"{zona}"
                    ),
                    type=(
                        "primary"
                        if zona_activa
                        else "secondary"
                    ),
                    use_container_width=True,
                    on_click=_abrir_planta,
                    args=(
                        "Pearson 22",
                        "Zonas exteriores",
                        zona,
                        datos.get(
                            "ordenes",
                            [],
                        ),
                        datos.get(
                            "ordenes_ejecutables",
                            [],
                        ),
                    ),
                )


# =========================================================
# CSS
# =========================================================

def css_edificio_vivo():
    st.markdown(
        """
        <style>
        .cv-campus-title{
            width:min(100%,1180px);
            margin:2px auto 4px;
            text-align:center;
            color:#0f172a;
            font-size:22px;
            line-height:1;
            font-weight:950;
            letter-spacing:.4px;
            text-transform:uppercase;
        }

        .cv-roof{
            height:42px;
            position:relative;
            margin:0 5px -1px;
            background:#172b47;
            clip-path:polygon(
                50% 0,
                100% 78%,
                100% 100%,
                0 100%,
                0 78%
            );
        }

        .cv-roof:after{
            content:"";
            position:absolute;
            left:50%;
            top:13px;
            transform:translateX(-50%);
            width:13px;
            height:13px;
            border:3px solid #f4e6bd;
            border-radius:50%;
            background:#27496f;
        }

        .cv-building-name{
            height:46px;
            display:flex;
            align-items:center;
            justify-content:center;
            overflow:hidden;
            padding:0 2px;
            background:linear-gradient(
                180deg,
                #173a6e,
                #0e284d
            );
            color:#fff;
            font-size:16px;
            line-height:1;
            font-weight:950;
            white-space:nowrap;
            text-align:center;
            border-left:4px solid #d9caa7;
            border-right:4px solid #d9caa7;
            border-top:3px solid #e8dab5;
            border-bottom:3px solid #caba93;
        }

        .cv-ground{
            height:42px;
            position:relative;
            background:linear-gradient(
                #d4c29b,
                #bd9f72
            );
            border:4px solid #ded1ad;
            border-top:3px solid #b89e72;
        }

        .cv-door{
            position:absolute;
            left:50%;
            bottom:0;
            transform:translateX(-50%);
            width:23px;
            height:33px;
            background:linear-gradient(
                90deg,
                #16345b 48%,
                #0c2442 50%
            );
            border:2px solid #10233c;
            border-bottom:0;
            border-radius:2px 2px 0 0;
        }

        .cv-base{
            height:7px;
            background:#354154;
            border-bottom:2px solid #1f2937;
            border-radius:0 0 3px 3px;
        }

        .cv-annex-wrap{
            width:min(100%,1180px);
            margin:12px auto 4px;
        }

        .cv-annex-title{
            background:linear-gradient(
                180deg,
                #173a6e,
                #0e284d
            );
            color:#fff;
            border:3px solid #d9caa7;
            padding:8px 12px;
            text-align:center;
            font-size:14px;
            font-weight:950;
            letter-spacing:.3px;
        }

        /*
        Los botones de planta son nativos de Streamlit.
        Se aplica un diseño compacto solamente dentro del mapa.
        */
        div[data-testid="stHorizontalBlock"]
        div[data-testid="stButton"] > button{
            min-height:58px !important;
            height:58px !important;
            padding:0 18px !important;
            margin:0 !important;
            border-radius:0 !important;
            border:1px solid rgba(80,70,50,.24) !important;
            color:#102033 !important;
            font-size:16px !important;
            line-height:1 !important;
            font-weight:900 !important;
            text-align:center !important;
            justify-content:space-between !important;
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.30)
                !important;
        }

        /* Planta utilizada más recientemente */
        div[data-testid="stHorizontalBlock"]
        div[data-testid="stButton"] > button[kind="primary"]{
            background:linear-gradient(
                135deg,
                #173a6e,
                #2459a7
            ) !important;
            color:#ffffff !important;
            border:3px solid #f0d58a !important;
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.28),
                0 4px 12px rgba(15,39,71,.20)
                !important;
        }

        @keyframes cvAbrirPlanta{
            from{
                opacity:0;
                transform:translateY(8px) scale(.992);
            }
            to{
                opacity:1;
                transform:translateY(0) scale(1);
            }
        }

        .cv-planta-detalle{
            width:min(100%,900px);
            margin:4px auto;
            padding:8px 10px;
            border:1px solid #dbe3ef;
            border-radius:11px;
            background:#fff;
            animation:cvAbrirPlanta .22s ease-out both;
        }

        .cv-planta-detalle-titulo{
            color:#0f2747;
            font-size:14px;
            font-weight:950;
        }

        @media(max-width:760px){
            /*
            Los edificios A/B/C continúan en una sola fila.
            Solo el Anexo Servicios pasa a 2 x 2 en móvil.
            */
            div[data-testid="stHorizontalBlock"]{
                flex-wrap:nowrap !important;
                gap:4px !important;
            }

            div[data-testid="stHorizontalBlock"] > div{
                min-width:0 !important;
                flex:1 1 0 !important;
            }

            .st-key-cv_zonas_externas_p22
            div[data-testid="stHorizontalBlock"]{
                flex-wrap:wrap !important;
                gap:4px !important;
                width:100% !important;
            }

            .st-key-cv_zonas_externas_p22
            div[data-testid="stHorizontalBlock"] > div{
                flex:1 1 calc(50% - 4px) !important;
                min-width:calc(50% - 4px) !important;
                max-width:calc(50% - 4px) !important;
            }

            .st-key-cv_zonas_externas_p22
            div[data-testid="stButton"] > button{
                min-height:54px !important;
                height:54px !important;
                padding:4px 7px !important;
                font-size:11px !important;
                line-height:1.15 !important;
                white-space:normal !important;
                justify-content:center !important;
                text-align:center !important;
                overflow:hidden !important;
            }

            .st-key-cv_anexo_p9_mobile
            div[data-testid="stHorizontalBlock"]{
                flex-wrap:wrap !important;
                gap:4px !important;
                width:100% !important;
            }

            .st-key-cv_anexo_p9_mobile
            div[data-testid="stHorizontalBlock"] > div{
                flex:1 1 calc(50% - 4px) !important;
                min-width:calc(50% - 4px) !important;
                max-width:calc(50% - 4px) !important;
            }

            .st-key-cv_anexo_p9_mobile
            div[data-testid="stButton"] > button{
                min-height:54px !important;
                height:54px !important;
                padding:4px 7px !important;
                font-size:11px !important;
                line-height:1.15 !important;
                white-space:normal !important;
                justify-content:center !important;
                text-align:center !important;
                overflow:hidden !important;
            }

            .cv-annex-wrap{
                margin-top:8px;
            }

            .cv-annex-title{
                font-size:12px;
                padding:7px 8px;
            }

            .cv-campus-title{
                width:100%;
                font-size:15px;
                margin-bottom:5px;
            }

            .cv-roof{
                height:28px;
                margin:0 3px -1px;
            }

            .cv-roof:after{
                top:8px;
                width:8px;
                height:8px;
                border-width:2px;
            }

            .cv-building-name{
                height:31px;
                padding:0 1px;
                font-size:9px;
                border-left-width:2px;
                border-right-width:2px;
                border-top-width:2px;
                border-bottom-width:2px;
            }

            div[data-testid="stHorizontalBlock"]
            div[data-testid="stButton"] > button{
                min-height:43px !important;
                height:43px !important;
                padding:0 5px !important;
                font-size:10px !important;
            }

            .cv-ground{
                height:25px;
                border-width:2px;
                border-top-width:2px;
            }

            .cv-door{
                width:15px;
                height:20px;
                border-width:1px;
            }

            .cv-base{
                height:4px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DIBUJO NATIVO
# =========================================================

def _pintar_edificio(
    centro,
    edificio,
    plantas,
    resumen,
):
    st.markdown(
        (
            '<div class="cv-roof"></div>'
            '<div class="cv-building-name">'
            f'{html.escape(edificio.upper())}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    for planta in plantas:
        datos = resumen.get(
            (centro, edificio, planta),
            {
                "total": 0,
                "ejecutables": 0,
                "bloqueadas": 0,
                "en_curso": 0,
                "urgentes": 0,
                "altas": 0,
                "ordenes": [],
                "ordenes_ejecutables": [],
            },
        )

        estado = _estado_planta(datos)
        icono = _icono_estado(estado)
        etiqueta = etiqueta_planta(planta)
        contador = _texto_contador(datos)


        planta_activa = (
            st.session_state.get("colegio_vivo_ultima_centro") == centro
            and st.session_state.get("colegio_vivo_ultimo_edificio") == edificio
            and st.session_state.get("colegio_vivo_ultima_planta") == planta
        )

        st.button(
            f"{icono} {etiqueta}     {contador}",
            key=(
                f"cv_planta_"
                f"{centro}_"
                f"{edificio}_"
                f"{planta}"
            ),
            type="primary" if planta_activa else "secondary",
            use_container_width=True,
            on_click=_abrir_planta,
            args=(
                centro,
                edificio,
                planta,
                datos.get("ordenes", []),
                datos.get(
                    "ordenes_ejecutables",
                    [],
                ),
            ),
        )

    st.markdown(
        (
            '<div class="cv-ground">'
            '<div class="cv-door"></div>'
            '</div>'
            '<div class="cv-base"></div>'
        ),
        unsafe_allow_html=True,
    )


def pintar_campus_operario(
    centro,
    resumen,
):
    edificios = EDIFICIOS.get(
        centro,
        {},
    )

    if not edificios:
        st.warning(
            f"No existe estructura configurada para {centro}."
        )
        return

    mapa_visibilidad = _mapa_visibilidad_plantas()

    edificios_visibles = {}

    for edificio, plantas in edificios.items():
        plantas_visibles = _plantas_visibles_edificio(
            centro=centro,
            edificio=edificio,
            plantas=plantas,
            mapa_visibilidad=mapa_visibilidad,
        )

        if plantas_visibles:
            edificios_visibles[edificio] = plantas_visibles

    if not edificios_visibles:
        st.info(
            f"No hay plantas visibles configuradas para {centro}."
        )
        return

    st.markdown(
        (
            '<div class="cv-campus-title">'
            f'{html.escape(centro)}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    columnas = st.columns(
        len(edificios_visibles),
        gap="small",
    )

    for columna, (
        edificio,
        plantas,
    ) in zip(
        columnas,
        edificios_visibles.items(),
    ):
        with columna:
            _pintar_edificio(
                centro,
                edificio,
                plantas,
                resumen,
            )

    # Pearson 22: zonas externas configurables.
    # Se pintan aparte para no modificar el dibujo físico existente.
    if centro == "Pearson 22":
        _pintar_zonas_externas_p22(
            resumen,
        )

    # Pearson 9 tiene además un anexo real, independiente de A/B/C,
    # formado por cuatro espacios consecutivos en una sola planta.
    if centro == "Pearson 9":
        _pintar_anexo_servicios_p9(
            resumen,
        )
