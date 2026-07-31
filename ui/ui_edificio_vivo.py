import html
import re
import unicodedata

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
    texto = str(texto or "").lower().strip()

    texto = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

    for caracter in ["/", "-", "_", ".", ",", ";", ":"]:
        texto = texto.replace(caracter, " ")

    return " ".join(texto.split())


def normalizar_centro(valor):
    texto = _norm(valor)

    if texto in {
        "pearson 22",
        "pearson22",
        "p22",
        "pearson nº 22",
        "pearson numero 22",
    }:
        return "Pearson 22"

    if texto in {
        "pearson 9",
        "pearson9",
        "p9",
        "pearson nº 9",
        "pearson numero 9",
    }:
        return "Pearson 9"

    if "22" in texto:
        return "Pearson 22"

    if re.search(r"\b9\b", texto):
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
            "edif infantil",
            "edificio infantil",
            "principal",
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

    equivalencias = {
        "baja": 0,
        "pb": 0,
        "principal": 0,
        "cero": 0,
        "primera": 1,
        "primero": 1,
        "segunda": 2,
        "segundo": 2,
        "tercera": 3,
        "tercero": 3,
        "cuarta": 4,
        "cuarto": 4,
        "quinta": 5,
        "quinto": 5,
    }

    for numero in range(10):
        patrones = [
            rf"\bp\s*{numero}\b",
            rf"\bplanta\s*{numero}\b",
            rf"\bpiso\s*{numero}\b",
            rf"\bnivel\s*{numero}\b",
        ]

        if any(re.search(patron, texto) for patron in patrones):
            return f"Planta {numero}"

        if texto == str(numero):
            return f"Planta {numero}"

    palabras = texto.split()

    for palabra, numero in equivalencias.items():
        if palabra in palabras:
            return f"Planta {numero}"

    return ""


def css_edificio_vivo():
    st.markdown(
        """
        <style>
        .cv-campus-title{
            font-size:17px;
            font-weight:950;
            color:#0f172a;
            text-align:center;
            margin:3px 0 6px;
            text-transform:uppercase;
            letter-spacing:.4px;
        }

        .cv-building-wrap{
            width:100%;
            filter:drop-shadow(0 6px 7px rgba(15,23,42,.10));
        }

        .cv-roof{
            height:38px;
            position:relative;
            margin:0 7px -1px;
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
            top:12px;
            transform:translateX(-50%);
            width:13px;
            height:13px;
            border:2px solid #f4e6bd;
            border-radius:50%;
            background:#27496f;
        }

        .cv-building-name{
            min-height:34px;
            display:flex;
            align-items:center;
            justify-content:center;
            background:linear-gradient(180deg,#173a6e,#0e284d);
            color:#fff;
            text-align:center;
            font-size:11px;
            line-height:1.05;
            font-weight:950;
            padding:5px 3px;
            border-left:5px solid #d9caa7;
            border-right:5px solid #d9caa7;
            border-top:3px solid #e8dab5;
            border-bottom:3px solid #caba93;
        }

        .cv-ground{
            height:35px;
            position:relative;
            background:linear-gradient(#d4c29b,#bd9f72);
            border:6px solid #ded1ad;
            border-top:3px solid #b89e72;
        }

        .cv-door{
            position:absolute;
            left:50%;
            bottom:0;
            transform:translateX(-50%);
            width:23px;
            height:28px;
            background:linear-gradient(
                90deg,
                #16345b 48%,
                #0c2442 50%
            );
            border:3px solid #10233c;
            border-bottom:0;
            border-radius:3px 3px 0 0;
        }

        .cv-base{
            height:8px;
            background:#354154;
            border-radius:0 0 4px 4px;
            border-bottom:3px solid #1f2937;
        }

        div[data-testid="stButton"] button[kind="secondary"]{
            min-height:36px !important;
            height:36px !important;
            padding:2px 5px !important;
            margin:0 !important;
            border-radius:0 !important;
            font-size:11px !important;
            font-weight:900 !important;
            white-space:nowrap !important;
            border:1px solid rgba(80,70,50,.24) !important;
            box-shadow:
                inset 0 0 0 1px rgba(255,255,255,.35)
                !important;
        }

        div[data-testid="stButton"]{
            margin-bottom:0 !important;
        }

        .cv-floor-correcta button{
            background:linear-gradient(
                90deg,
                #d9f7c9,
                #bfeaa7
            ) !important;
        }

        .cv-floor-seguimiento button{
            background:linear-gradient(
                90deg,
                #fff1ad,
                #ffd763
            ) !important;
        }

        .cv-floor-atencion button{
            background:linear-gradient(
                90deg,
                #ffd2aa,
                #ff9b54
            ) !important;
        }

        .cv-floor-critica button{
            background:linear-gradient(
                90deg,
                #ffc2c2,
                #ff7f7f
            ) !important;
        }

        @media(max-width:760px){
            .block-container{
                padding-left:.45rem !important;
                padding-right:.45rem !important;
            }

            div[data-testid="stHorizontalBlock"]{
                gap:.28rem !important;
            }

            .cv-roof{
                height:30px;
                margin:0 4px -1px;
            }

            .cv-roof:after{
                top:9px;
                width:10px;
                height:10px;
            }

            .cv-building-name{
                min-height:30px;
                font-size:9px;
                padding:4px 1px;
                border-left-width:3px;
                border-right-width:3px;
            }

            div[data-testid="stButton"]
            button[kind="secondary"]{
                min-height:34px !important;
                height:34px !important;
                padding:1px 2px !important;
                font-size:9px !important;
            }

            .cv-ground{
                height:27px;
                border-width:4px;
            }

            .cv-door{
                width:18px;
                height:22px;
            }

            .cv-base{
                height:6px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def clase_estado_planta(total, urgentes, altas):
    if urgentes > 0:
        return "critica"

    if altas > 0:
        return "atencion"

    if total > 0:
        return "seguimiento"

    return "correcta"


def icono_estado_planta(clase):
    return {
        "correcta": "🟢",
        "seguimiento": "🟡",
        "atencion": "🟠",
        "critica": "🔴",
    }.get(clase, "🟢")


def etiqueta_planta(planta):
    if planta == "Terrado":
        return "T"

    return planta.replace("Planta ", "P")


def pintar_edificio_operario(
    centro,
    edificio,
    plantas,
    resumen,
):
    st.markdown(
        '<div class="cv-building-wrap">'
        '<div class="cv-roof"></div>'
        f'<div class="cv-building-name">'
        f'{html.escape(edificio.upper())}'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    for planta in plantas:
        datos = resumen.get(
            (centro, edificio, planta),
            {},
        )

        total = int(datos.get("total") or 0)
        urgentes = int(datos.get("urgentes") or 0)
        altas = int(datos.get("altas") or 0)

        clase = clase_estado_planta(
            total,
            urgentes,
            altas,
        )

        icono = icono_estado_planta(clase)
        etiqueta = etiqueta_planta(planta)
        contador = "✓" if total == 0 else str(total)

        contenedor = st.container()

        with contenedor:
            if st.button(
                f"{icono} {etiqueta}  {contador}",
                key=(
                    f"cv_planta_"
                    f"{centro}_"
                    f"{edificio}_"
                    f"{planta}"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "colegio_vivo_centro"
                ] = centro

                st.session_state[
                    "colegio_vivo_edificio"
                ] = edificio

                st.session_state[
                    "colegio_vivo_planta"
                ] = planta

                st.session_state[
                    "colegio_vivo_ordenes_planta"
                ] = datos.get("ordenes", [])

                st.rerun()

        st.markdown(
            f"""
            <script>
            </script>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="cv-ground">'
        '<div class="cv-door"></div>'
        '</div>'
        '<div class="cv-base"></div>',
        unsafe_allow_html=True,
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

    st.markdown(
        f'<div class="cv-campus-title">'
        f'{html.escape(centro)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    columnas = st.columns(
        len(edificios),
        gap="small",
    )

    for columna, (edificio, plantas) in zip(
        columnas,
        edificios.items(),
    ):
        with columna:
            pintar_edificio_operario(
                centro,
                edificio,
                plantas,
                resumen,
            )
