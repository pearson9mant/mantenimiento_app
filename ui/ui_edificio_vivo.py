import html
import re
import unicodedata
from urllib.parse import urlencode

import streamlit as st


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

    if texto in {
        "pearson 22",
        "pearson22",
        "p22",
        "pearson numero 22",
    } or "pearson 22" in texto:
        return "Pearson 22"

    if texto in {
        "pearson 9",
        "pearson9",
        "p9",
        "pearson numero 9",
    } or "pearson 9" in texto:
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

    if altas > 0:
        return "atencion"

    if ejecutables >= 3:
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


def _query_planta(centro, edificio, planta):
    return "?" + urlencode(
        {
            "cv_accion": "planta",
            "cv_centro": centro,
            "cv_edificio": edificio,
            "cv_planta": planta,
        }
    )


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

        .cv-campus-grid{
            display:flex;
            flex-direction:row;
            flex-wrap:nowrap;
            align-items:flex-end;
            justify-content:center;
            gap:16px;
            width:min(100%,760px);
            margin:0 auto;
            overflow:hidden;
        }

        .cv-building{
            flex:0 1 330px;
            width:330px;
            min-width:0;
            max-width:330px;
            filter:drop-shadow(
                0 3px 4px rgba(15,23,42,.08)
            );
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

        .cv-floors{
            border-left:4px solid #ded1ad;
            border-right:4px solid #ded1ad;
            background:#efe7d2;
        }

        a.cv-floor{
            height:27px;
            display:grid;
            grid-template-columns:17px 1fr auto 9px;
            align-items:center;
            gap:2px;
            padding:0 4px;
            border-bottom:1px solid rgba(80,70,50,.24);
            color:#102033 !important;
            font-size:10px;
            line-height:1;
            font-weight:900;
            text-decoration:none !important;
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.30);
        }

        a.cv-floor:hover{
            filter:brightness(.97) saturate(1.05);
        }

        .cv-floor.correcta{
            background:linear-gradient(
                90deg,
                #d9f7c9,
                #bfeaa7
            );
        }

        .cv-floor.seguimiento{
            background:linear-gradient(
                90deg,
                #fff1ad,
                #ffd763
            );
        }

        .cv-floor.atencion{
            background:linear-gradient(
                90deg,
                #ffd2aa,
                #ff9b54
            );
        }

        .cv-floor.critica{
            background:linear-gradient(
                90deg,
                #ffc2c2,
                #ff7f7f
            );
        }

        .cv-floor.curso{
            background:linear-gradient(
                90deg,
                #c7dcff,
                #79aaff
            );
        }

        .cv-floor.bloqueada{
            background:linear-gradient(
                90deg,
                #e7e5e4,
                #cbd5e1
            );
        }

        .cv-floor-icon{
            font-size:10px;
            text-align:center;
        }

        .cv-floor-name{
            overflow:hidden;
            white-space:nowrap;
            text-overflow:ellipsis;
        }

        .cv-floor-count{
            min-width:19px;
            height:19px;
            display:flex;
            align-items:center;
            justify-content:center;
            padding:0 4px;
            border-radius:999px;
            background:rgba(255,255,255,.80);
            color:#0f172a;
            font-size:8px;
            font-weight:950;
        }

        .cv-floor-arrow{
            font-size:7px;
            text-align:right;
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

        @media(max-width:760px){
            .block-container{
                padding-left:.16rem !important;
                padding-right:.16rem !important;
            }

            .cv-campus-title{
                width:100%;
                font-size:12px;
                margin-bottom:3px;
            }

            .cv-campus-grid{
                display:flex !important;
                flex-direction:row !important;
                flex-wrap:nowrap !important;
                align-items:flex-end !important;
                justify-content:center !important;
                gap:4px !important;
                width:100% !important;
                overflow:hidden !important;
            }

            .cv-building{
                flex:1 1 0 !important;
                width:auto !important;
                min-width:0 !important;
                max-width:none !important;
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

            .cv-floors{
                border-left-width:2px;
                border-right-width:2px;
            }

            a.cv-floor{
                height:25px;
                grid-template-columns:12px 1fr auto 6px;
                gap:1px;
                padding:0 2px;
                font-size:7px;
            }

            .cv-floor-icon{
                font-size:8px;
            }

            .cv-floor-count{
                min-width:15px;
                height:15px;
                padding:0 2px;
                font-size:6px;
            }

            .cv-floor-arrow{
                font-size:5px;
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


def _html_edificio(
    centro,
    edificio,
    plantas,
    resumen,
):
    plantas_html = ""

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
            },
        )

        estado = _estado_planta(datos)
        icono = _icono_estado(estado)
        etiqueta = etiqueta_planta(planta)
        contador = _contador_planta(datos)

        ejecutables = int(
            datos.get("ejecutables") or 0
        )

        flecha = "▶" if ejecutables > 0 else ""

        query = _query_planta(
            centro,
            edificio,
            planta,
        )

        plantas_html += (
            f'<a class="cv-floor {estado}" '
            f'href="{html.escape(query)}" '
            f'target="_self">'
            f'<span class="cv-floor-icon">{icono}</span>'
            f'<span class="cv-floor-name">'
            f'{html.escape(etiqueta)}'
            f'</span>'
            f'<span class="cv-floor-count">'
            f'{html.escape(contador)}'
            f'</span>'
            f'<span class="cv-floor-arrow">{flecha}</span>'
            f'</a>'
        )

    return (
        '<div class="cv-building">'
        '<div class="cv-roof"></div>'
        f'<div class="cv-building-name">'
        f'{html.escape(edificio.upper())}'
        f'</div>'
        f'<div class="cv-floors">{plantas_html}</div>'
        '<div class="cv-ground">'
        '<div class="cv-door"></div>'
        '</div>'
        '<div class="cv-base"></div>'
        '</div>'
    )


def pintar_campus_operario(
    centro,
    resumen,
):
    edificios = EDIFICIOS.get(centro, {})

    if not edificios:
        st.warning(
            f"No existe estructura configurada para {centro}."
        )
        return

    edificios_html = "".join(
        _html_edificio(
            centro,
            edificio,
            plantas,
            resumen,
        )
        for edificio, plantas in edificios.items()
    )

    st.markdown(
        (
            f'<div class="cv-campus-title">'
            f'{html.escape(centro)}'
            f'</div>'
            f'<div class="cv-campus-grid">'
            f'{edificios_html}'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )
