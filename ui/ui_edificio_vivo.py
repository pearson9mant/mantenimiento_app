import html
import re
import unicodedata

import streamlit as st


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
        "Edificio A": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
        "Edificio B": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
        "Edificio C": [
            "Terrado",
            "Planta 2",
            "Planta 1",
            "Planta 0",
        ],
    },
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


def _contador_planta(datos):
    total = int(datos.get("total") or 0)
    ejecutables = int(datos.get("ejecutables") or 0)
    bloqueadas = int(datos.get("bloqueadas") or 0)

    if total == 0:
        return "✓"

    if ejecutables > 0 and bloqueadas > 0:
        return f"{ejecutables}+{bloqueadas}"

    if ejecutables > 0:
        return str(ejecutables)

    if bloqueadas > 0:
        return str(bloqueadas)

    return str(total)


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
# CSS
# =========================================================

def css_edificio_vivo():
    st.markdown(
        """
        <style>
        .cv-campus-title{
            width:min(100%,760px);
            margin:2px auto 4px;
            text-align:center;
            color:#0f172a;
            font-size:15px;
            line-height:1;
            font-weight:950;
            letter-spacing:.4px;
            text-transform:uppercase;
        }

        .cv-roof{
            height:22px;
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
            top:6px;
            transform:translateX(-50%);
            width:8px;
            height:8px;
            border:2px solid #f4e6bd;
            border-radius:50%;
            background:#27496f;
        }

        .cv-building-name{
            height:24px;
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
            font-size:9px;
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
            height:20px;
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
            width:14px;
            height:16px;
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
            height:5px;
            background:#354154;
            border-bottom:2px solid #1f2937;
            border-radius:0 0 3px 3px;
        }

        /*
        Los botones de planta son nativos de Streamlit.
        Se aplica un diseño compacto solamente dentro del mapa.
        */
        div[data-testid="stHorizontalBlock"]
        div[data-testid="stButton"] > button{
            min-height:27px !important;
            height:27px !important;
            padding:0 5px !important;
            margin:0 !important;
            border-radius:0 !important;
            border:1px solid rgba(80,70,50,.24) !important;
            color:#102033 !important;
            font-size:10px !important;
            line-height:1 !important;
            font-weight:900 !important;
            text-align:center !important;
            justify-content:center !important;
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.30)
                !important;
        }

        .cv-floor-correcta + div
        button{
            background:linear-gradient(
                90deg,
                #d9f7c9,
                #bfeaa7
            ) !important;
        }

        .cv-floor-seguimiento + div
        button{
            background:linear-gradient(
                90deg,
                #fff1ad,
                #ffd763
            ) !important;
        }

        .cv-floor-atencion + div
        button{
            background:linear-gradient(
                90deg,
                #ffd2aa,
                #ff9b54
            ) !important;
        }

        .cv-floor-critica + div
        button{
            background:linear-gradient(
                90deg,
                #ffc2c2,
                #ff7f7f
            ) !important;
        }

        .cv-floor-curso + div
        button{
            background:linear-gradient(
                90deg,
                #c7dcff,
                #79aaff
            ) !important;
        }

        .cv-floor-bloqueada + div
        button{
            background:linear-gradient(
                90deg,
                #e7e5e4,
                #cbd5e1
            ) !important;
        }

        .cv-planta-detalle{
            width:min(100%,900px);
            margin:4px auto;
            padding:8px 10px;
            border:1px solid #dbe3ef;
            border-radius:11px;
            background:#fff;
        }

        .cv-planta-detalle-titulo{
            color:#0f2747;
            font-size:14px;
            font-weight:950;
        }

        @media(max-width:760px){
            div[data-testid="stHorizontalBlock"]{
                flex-wrap:nowrap !important;
                gap:4px !important;
            }

            div[data-testid="stHorizontalBlock"] > div{
                min-width:0 !important;
                flex:1 1 0 !important;
            }

            .cv-campus-title{
                width:100%;
                font-size:12px;
                margin-bottom:3px;
            }

            .cv-roof{
                height:18px;
                margin:0 2px -1px;
            }

            .cv-roof:after{
                top:5px;
                width:6px;
                height:6px;
                border-width:1px;
            }

            .cv-building-name{
                height:21px;
                padding:0 1px;
                font-size:7px;
                border-left-width:2px;
                border-right-width:2px;
                border-top-width:2px;
                border-bottom-width:2px;
            }

            div[data-testid="stHorizontalBlock"]
            div[data-testid="stButton"] > button{
                min-height:25px !important;
                height:25px !important;
                padding:0 2px !important;
                font-size:7px !important;
            }

            .cv-ground{
                height:17px;
                border-width:2px;
                border-top-width:2px;
            }

            .cv-door{
                width:11px;
                height:13px;
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
        contador = _contador_planta(datos)

        ejecutables = int(
            datos.get("ejecutables") or 0
        )

        flecha = " ▶" if ejecutables > 0 else ""

        # Marcador para el color del botón siguiente.
        st.markdown(
            f'<span class="cv-floor-{estado}"></span>',
            unsafe_allow_html=True,
        )

        st.button(
            f"{icono} {etiqueta}   {contador}{flecha}",
            key=(
                f"cv_planta_"
                f"{centro}_"
                f"{edificio}_"
                f"{planta}"
            ),
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

    st.markdown(
        (
            '<div class="cv-campus-title">'
            f'{html.escape(centro)}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    columnas = st.columns(
        len(edificios),
        gap="small",
    )

    for columna, (
        edificio,
        plantas,
    ) in zip(
        columnas,
        edificios.items(),
    ):
        with columna:
            _pintar_edificio(
                centro,
                edificio,
                plantas,
                resumen,
            )
