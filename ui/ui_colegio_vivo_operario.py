import html

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from modules.colegio_vivo import obtener_colegio_vivo
from modules.corazon_sistema import (
    buscar_antecedente_similar_corazon,
    construir_prioridades_globales,
    latido_corazon,
)

from ui.ui_edificio_vivo import (
    css_edificio_vivo,
    normalizar_centro,
    normalizar_edificio,
    normalizar_planta,
    pintar_campus_operario,
    volver_colegio_vivo,
)


ORDEN_PRIORIDAD = {
    "urgente": 0,
    "alta": 1,
    "media": 2,
    "baja": 3,
}


MAPA_OPERARIO_CENTRO = {
    "J.A. Almeda": "Pearson 22",
    "Luis Lozano": "Pearson 9",
    "Abel Vasquez": "Pearson 22",
}


def _todas_las_ordenes(colegio):
    ordenes = []

    for centro_datos in colegio:
        nombre_centro = centro_datos.get(
            "centro",
            "",
        )

        for edificio_datos in centro_datos.get(
            "edificios",
            [],
        ):
            nombre_edificio = edificio_datos.get(
                "nombre",
                "",
            )

            for planta_datos in edificio_datos.get(
                "plantas",
                [],
            ):
                nombre_planta = planta_datos.get(
                    "nombre",
                    "",
                )

                ordenes_planta = planta_datos.get(
                    "ordenes_ejecutables",
                    [],
                )

                for ot in ordenes_planta:
                    fila = dict(ot)

                    fila["_centro_vivo"] = nombre_centro
                    fila["_edificio_vivo"] = nombre_edificio
                    fila["_planta_vivo"] = nombre_planta

                    ordenes.append(fila)

    return ordenes


def _ordenar_misiones(ordenes):
    def clave(ot):
        prioridad = str(
            ot.get("prioridad") or ""
        ).strip().lower()

        en_curso = bool(
            ot.get("_en_curso", False)
        )

        fecha = str(
            ot.get("fecha_creacion")
            or ot.get("fecha")
            or ""
        ).strip()

        identificador = ot.get("id") or 0

        return (
            0 if en_curso else 1,
            ORDEN_PRIORIDAD.get(prioridad, 9),
            fecha,
            identificador,
        )

    return sorted(
        ordenes,
        key=clave,
    )



def _buscar_ot_colegio_por_mision(ordenes, mision):
    if not mision:
        return None

    id_mision = mision.get("id")
    numero_mision = str(
        mision.get("numero_ot")
        or ""
    ).strip()

    for ot in ordenes or []:
        try:
            if (
                id_mision is not None
                and int(ot.get("id")) == int(id_mision)
            ):
                resultado = dict(ot)
                resultado.update({
                    "score_corazon": mision.get("score_corazon"),
                    "motivos_corazon": mision.get("motivos_corazon", []),
                })
                return resultado
        except (TypeError, ValueError):
            pass

        if (
            numero_mision
            and str(ot.get("numero_ot") or "").strip() == numero_mision
        ):
            resultado = dict(ot)
            resultado.update({
                "score_corazon": mision.get("score_corazon"),
                "motivos_corazon": mision.get("motivos_corazon", []),
            })
            return resultado

    return None


def _obtener_mision_corazon_colegio(
    operario,
    centro,
    ordenes,
):
    """
    El Corazón decide la misión real.
    Si por cualquier motivo no responde, conserva el criterio anterior
    como respaldo para no romper la pantalla.
    """
    ubicacion_preferida = st.session_state.get(
        "corazon_ubicacion_preferida"
    )

    try:
        latido = latido_corazon(
            operario=operario,
            centro=centro or None,
            ubicacion_preferida=ubicacion_preferida,
        )

        mision_corazon = latido.get("mision") or {}

        encontrada = _buscar_ot_colegio_por_mision(
            ordenes,
            mision_corazon,
        )

        if encontrada:
            encontrada["_estado_corazon"] = latido.get(
                "estado_corazon",
                ""
            )
            encontrada["_ot_en_curso_corazon"] = latido.get(
                "ot_en_curso"
            )
            return encontrada

    except Exception:
        pass

    ordenadas = _ordenar_misiones(
        ordenes
    )

    return ordenadas[0] if ordenadas else None



def _misma_ot(ot_a, ot_b):
    if not ot_a or not ot_b:
        return False

    try:
        if (
            ot_a.get("id") is not None
            and ot_b.get("id") is not None
            and int(ot_a.get("id")) == int(ot_b.get("id"))
        ):
            return True
    except (TypeError, ValueError):
        pass

    numero_a = str(
        ot_a.get("numero_ot")
        or ""
    ).strip()

    numero_b = str(
        ot_b.get("numero_ot")
        or ""
    ).strip()

    return bool(
        numero_a
        and numero_b
        and numero_a == numero_b
    )


def _buscar_ot_por_numero(ordenes, numero_ot):
    numero_objetivo = str(
        numero_ot
        or ""
    ).strip()

    if not numero_objetivo:
        return None

    for ot in ordenes or []:
        if (
            str(ot.get("numero_ot") or "").strip()
            == numero_objetivo
        ):
            return ot

    return None


def _obtener_siguiente_ot_cercana(
    mision,
    ordenes,
):
    """
    Corazón local:
    elige la mejor OT real de la misma planta usando el mismo
    motor de prioridades que decide MI MISIÓN.

    No modifica la misión principal ni ningún estado.
    """
    if not mision:
        return None

    centro_m, edificio_m, planta_m = (
        _ubicacion_mision(mision)
    )

    candidatas = []

    for ot in ordenes or []:
        if _misma_ot(ot, mision):
            continue

        if ot.get("_ejecutable") is False:
            continue

        centro_o, edificio_o, planta_o = (
            _ubicacion_mision(ot)
        )

        if (
            centro_o == centro_m
            and edificio_o == edificio_m
            and planta_o == planta_m
        ):
            candidatas.append(dict(ot))

    if not candidatas:
        return None

    try:
        df_candidatas = pd.DataFrame(
            candidatas
        )

        prioridades = construir_prioridades_globales(
            centro=centro_m or None,
            operario=str(
                st.session_state.get("operario_activo")
                or st.session_state.get("usuario")
                or ""
            ).strip() or None,
            limite=1,
            df_ordenes_abiertas=df_candidatas,
            ubicacion_preferida={
                "centro": centro_m,
                "edificio": edificio_m,
                "planta": planta_m,
            },
        )

        if prioridades:
            siguiente = _buscar_ot_por_numero(
                candidatas,
                prioridades[0].get("numero_ot"),
            )

            if siguiente:
                siguiente = dict(siguiente)
                siguiente["score_corazon"] = (
                    prioridades[0].get("score")
                )
                siguiente["motivos_corazon"] = (
                    prioridades[0].get("motivos", [])
                )
                return siguiente

    except Exception:
        # Respaldo conservador: si el motor local falla,
        # conserva la selección anterior sin romper la pantalla.
        pass

    ordenadas = _ordenar_misiones(
        candidatas
    )

    return ordenadas[0] if ordenadas else None


def _mostrar_siguiente_ot_corazon(
    mision,
    ordenes,
):
    siguiente = _obtener_siguiente_ot_cercana(
        mision,
        ordenes,
    )

    if not siguiente:
        return

    numero_ot = str(
        siguiente.get("numero_ot")
        or siguiente.get("id")
        or "OT"
    ).strip()

    aula = _texto_aula(
        siguiente
    )

    descripcion = _texto_averia(
        siguiente
    )

    prioridad = str(
        siguiente.get("prioridad")
        or "Media"
    ).strip()

    st.markdown(
        '<div class="cv-next">'
        '<div class="cv-next-title">'
        '🔜 DESPUÉS, SI NO ENTRA NADA MÁS IMPORTANTE'
        '</div>'
        '<div class="cv-next-ref">'
        f'{html.escape(numero_ot)} · '
        f'{html.escape(aula)} · '
        f'{html.escape(prioridad)}'
        '</div>'
        '<div class="cv-next-description">'
        f'{html.escape(descripcion)}'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _texto_averia(ot):
    return str(
        ot.get("descripcion")
        or ot.get("titulo")
        or ot.get("incidencia")
        or "Orden de trabajo"
    ).strip()


def _centro_del_operario(
    operario,
    colegio,
):
    centro_configurado = MAPA_OPERARIO_CENTRO.get(
        operario
    )

    if centro_configurado:
        return centro_configurado

    if colegio:
        return normalizar_centro(
            colegio[0].get("centro", "")
        )

    return ""


def _planta_respaldo(
    centro,
    edificio,
):
    """
    Una OT sin planta real permanece sin ubicar.
    Nunca se asigna automáticamente a P0 o P1.
    """
    return "Sin planta"


def _crear_resumen_edificios(colegio):
    resumen = {}

    for centro_datos in colegio:
        centro = normalizar_centro(
            centro_datos.get("centro", "")
        )

        for edificio_datos in centro_datos.get(
            "edificios",
            [],
        ):
            edificio = normalizar_edificio(
                edificio_datos.get("nombre", ""),
                centro,
            )

            for planta_datos in edificio_datos.get(
                "plantas",
                [],
            ):
                planta = normalizar_planta(
                    planta_datos.get("nombre", "")
                )

                if not planta:
                    planta = _planta_respaldo(
                        centro,
                        edificio,
                    )

                if not planta:
                    continue

                clave = (
                    centro,
                    edificio,
                    planta,
                )

                if clave not in resumen:
                    resumen[clave] = {
                        "total": 0,
                        "ejecutables": 0,
                        "bloqueadas": 0,
                        "en_curso": 0,
                        "sin_ubicar": 0,
                        "urgentes": 0,
                        "altas": 0,
                        "ordenes": [],
                        "ordenes_ejecutables": [],
                        "ordenes_bloqueadas": [],
                    }

                destino = resumen[clave]

                for campo in [
                    "total",
                    "ejecutables",
                    "bloqueadas",
                    "en_curso",
                    "sin_ubicar",
                    "urgentes",
                    "altas",
                ]:
                    destino[campo] += int(
                        planta_datos.get(campo) or 0
                    )

                destino["ordenes"].extend(
                    planta_datos.get(
                        "ordenes",
                        [],
                    )
                )

                destino["ordenes_ejecutables"].extend(
                    planta_datos.get(
                        "ordenes_ejecutables",
                        [],
                    )
                )

                destino["ordenes_bloqueadas"].extend(
                    planta_datos.get(
                        "ordenes_bloqueadas",
                        [],
                    )
                )

    return resumen


def _guardar_ot_recomendada(ot):
    """
    Abre una OT utilizando la única clave que entiende ui_operario.py.
    """
    id_ot = ot.get("id")

    if id_ot is None:
        return False

    try:
        id_ot = int(id_ot)
    except (TypeError, ValueError):
        return False

    st.session_state["operario_ot_abierta_id"] = id_ot

    for clave in [
        "colegio_vivo_ot",
        "colegio_vivo_ot_id",
        "ot_seleccionada",
        "ot_seleccionada_id",
        "orden_abierta",
        "orden_abierta_id",
    ]:
        st.session_state.pop(clave, None)

    return True


def _ubicacion_mision(ot):
    centro = normalizar_centro(
        ot.get("_centro_normalizado")
        or ot.get("_centro_vivo")
        or ot.get("centro")
        or ""
    )

    edificio = normalizar_edificio(
        ot.get("_edificio_normalizado")
        or ot.get("_edificio_vivo")
        or ot.get("edificio")
        or "",
        centro,
    )

    planta = normalizar_planta(
        ot.get("_planta_normalizada")
        or ot.get("_planta_vivo")
        or ot.get("planta")
        or ot.get("espacio")
        or ""
    )

    if not planta:
        planta = _planta_respaldo(
            centro,
            edificio,
        )

    return centro, edificio, planta


def _texto_aula(ot):
    aula = str(
        ot.get("espacio")
        or ot.get("aula")
        or ot.get("ubicacion")
        or ""
    ).strip()

    return aula or "Espacio pendiente"


def _abrir_ot_para_trabajar(ot, origen="mision"):
    """
    Abre directamente la OT seleccionada sin pasar por el listado general.
    También recuerda la ubicación para que el Corazón pueda continuar
    cerca al terminar, salvo que aparezca algo más importante.
    """
    if not _guardar_ot_recomendada(ot):
        return

    st.session_state["colegio_vivo_origen_ot"] = origen

    centro, edificio, planta = _ubicacion_mision(
        ot
    )

    st.session_state["corazon_ubicacion_preferida"] = {
        "centro": centro,
        "edificio": edificio,
        "planta": planta,
    }

    if origen != "planta":
        st.session_state["colegio_vivo_vista"] = "mapa"

    st.session_state["seccion_actual"] = "Órdenes"


def _volver_edificio_desde_planta():
    """
    Vuelve al edificio sin lanzar un rerun manual adicional.
    """
    volver_colegio_vivo()


def _mostrar_planta_seleccionada():
    """
    Vista de planta estable y nativa de Streamlit.

    No usa HTML personalizado en las tarjetas de OT para evitar
    inconsistencias del DOM en navegadores móviles.
    """
    if st.session_state.get("colegio_vivo_vista") != "planta":
        return False

    centro = st.session_state.get("colegio_vivo_centro", "")
    edificio = st.session_state.get("colegio_vivo_edificio", "")
    planta = st.session_state.get("colegio_vivo_planta", "")
    ordenes = st.session_state.get("colegio_vivo_ordenes_planta", [])

    st.button(
        "← VOLVER AL EDIFICIO",
        key="cv_volver_edificio",
        use_container_width=True,
        on_click=_volver_edificio_desde_planta,
    )

    st.markdown(
        f"### 📍 {centro} · {edificio} · {planta}"
    )
    st.caption(
        f"{len(ordenes)} OT activas"
    )

    if not ordenes:
        st.success(
            "✅ No hay órdenes activas en esta planta."
        )
        return True

    for ot in ordenes:
        numero_ot = str(
            ot.get("numero_ot")
            or ot.get("id")
            or "OT"
        ).strip()

        aula = _texto_aula(ot)

        descripcion = _texto_averia(ot)

        estado = str(
            ot.get("estado")
            or "Abierta"
        ).strip()

        prioridad = str(
            ot.get("prioridad")
            or "Media"
        ).strip()

        es_ejecutable = bool(
            ot.get("_ejecutable", False)
        )

        with st.container(border=True):
            st.markdown(
                f"**{numero_ot} · {aula}**"
            )

            st.markdown(
                descripcion or "Sin descripción."
            )

            st.caption(
                f"{prioridad} · {estado}"
            )

            if es_ejecutable or estado.strip().lower() == "pendiente material":
                st.button(
                    f"▶ EMPEZAR {numero_ot}",
                    key=f"cv_empezar_planta_{ot.get('id')}",
                    use_container_width=True,
                    on_click=_abrir_ot_para_trabajar,
                    args=(ot, "planta"),
                )

    return True




def _mostrar_ot_en_curso_interrumpida(mision):
    """
    Mantiene visible la OT que sigue En curso cuando el Corazón
    propone atender antes otra actuación crítica.
    No modifica ningún estado.
    """
    if not mision:
        return

    if mision.get("_estado_corazon") != "interrumpir":
        return

    ot_en_curso = mision.get("_ot_en_curso_corazon") or {}

    if not ot_en_curso:
        return

    numero_ot = str(
        ot_en_curso.get("numero_ot")
        or ot_en_curso.get("id")
        or "OT"
    ).strip()

    espacio = _texto_aula(
        ot_en_curso
    )

    descripcion = _texto_averia(
        ot_en_curso
    )

    with st.container(border=True):
        st.markdown(
            f"⏸️ **SIGUE EN CURSO · {numero_ot} · {espacio}**"
        )
        st.markdown(
            descripcion
        )
        st.caption(
            "Esta OT sigue En curso. El Corazón propone atender antes "
            "la incidencia crítica y volver después a este trabajo."
        )


def _mostrar_recuerdo_corazon(mision):
    """
    Muestra un único antecedente fiable antes de empezar la misión.
    Si no hay coincidencia suficiente, no ocupa espacio.
    """
    try:
        antecedente = buscar_antecedente_similar_corazon(mision)
    except Exception:
        antecedente = None

    if not antecedente:
        return

    numero_ot = str(
        antecedente.get("numero_ot")
        or "OT anterior"
    ).strip()

    fecha = str(
        antecedente.get("fecha")
        or ""
    ).strip()

    if fecha:
        fecha = fecha[:10]

    descripcion = str(
        antecedente.get("descripcion")
        or ""
    ).strip()

    solucion = str(
        antecedente.get("solucion")
        or ""
    ).strip()

    with st.container(border=True):
        st.markdown("🧠 **EL CORAZÓN RECUERDA**")
        st.caption(
            "Ya resolvimos una avería parecida en este mismo espacio."
        )

        referencia = f"**{numero_ot}**"
        if fecha:
            referencia += f" · {fecha}"

        st.markdown(referencia)

        if descripcion:
            st.markdown(descripcion)

        if solucion:
            st.success(
                f"🔧 Solución registrada: {solucion}"
            )


def _css_pantalla_operario():
    st.markdown(
        """
        <style>
        .block-container{
            padding-top:.08rem !important;
            padding-left:.30rem !important;
            padding-right:.30rem !important;
            padding-bottom:.30rem !important;
            max-width:1500px !important;
        }

        .cv-mission{
            background:linear-gradient(
                135deg,
                #0f2747,
                #164f91
            );
            color:#fff;
            border-radius:15px;
            padding:17px 20px 15px;
            margin:0 auto 3px;
            width:min(100%,1180px);
            box-shadow:
                0 4px 12px rgba(15,39,71,.16);
        }

        .cv-mission-top{
            font-size:16px;
            line-height:1;
            font-weight:950;
            margin-bottom:9px;
        }

        .cv-mission-place{
            font-size:22px;
            line-height:1.15;
            font-weight:950;
        }

        .cv-mission-description{
            margin-top:10px;
            overflow:hidden;
            color:rgba(255,255,255,.94);
            font-size:15px;
            line-height:1.35;
            white-space:normal;
            display:-webkit-box;
            -webkit-line-clamp:2;
            -webkit-box-orient:vertical;
        }

        .cv-next{
            width:min(100%,1180px);
            margin:4px auto 3px;
            padding:8px 11px;
            border:1px solid #dbe4ee;
            border-radius:10px;
            background:#f8fafc;
            color:#334155;
        }

        .cv-next-title{
            font-size:11px;
            line-height:1.2;
            font-weight:950;
            color:#0f2747;
        }

        .cv-next-ref{
            margin-top:3px;
            font-size:12px;
            line-height:1.2;
            font-weight:900;
        }

        .cv-next-description{
            margin-top:2px;
            font-size:11px;
            line-height:1.25;
            overflow:hidden;
            display:-webkit-box;
            -webkit-line-clamp:1;
            -webkit-box-orient:vertical;
        }

        .cv-school-title{
            width:min(100%,1180px);
            margin:5px auto 1px;
            color:#0f2747;
            font-size:20px;
            line-height:1;
            font-weight:950;
        }

        .cv-no-work{
            width:min(100%,1180px);
            margin:0 auto 3px;
            padding:7px 9px;
            border:1px solid #bbf7d0;
            border-radius:10px;
            background:#f0fdf4;
            color:#166534;
            font-size:11px;
            font-weight:900;
        }

        div[data-testid="stButton"]
        button[kind="primary"]{
            display:block !important;
            width:min(100%,1180px) !important;
            min-height:50px !important;
            height:50px !important;
            margin:0 auto !important;
            padding:1px 8px !important;
            border-radius:8px !important;
            font-size:17px !important;
            font-weight:950 !important;
        }

        div[data-testid="stButton"]{
            margin-bottom:0 !important;
        }

        div[data-testid="stVerticalBlock"]{
            gap:.10rem !important;
        }

        @media(max-width:760px){
            .block-container{
                padding-left:.14rem !important;
                padding-right:.14rem !important;
            }

            .cv-mission{
                width:100%;
                padding:11px 12px 10px;
                border-radius:11px;
            }

            .cv-mission-top{
                font-size:11px;
            }

            .cv-mission-place{
                font-size:14px;
            }

            .cv-mission-description{
                font-size:10px;
            }

            .cv-next{
                width:100%;
                margin-top:3px;
                padding:6px 8px;
                border-radius:8px;
            }

            .cv-next-title{font-size:9px;}
            .cv-next-ref{font-size:10px;}
            .cv-next-description{font-size:9px;}

            .cv-school-title{
                width:100%;
                font-size:11px;
            }

            div[data-testid="stButton"]
            button[kind="primary"]{
                width:100% !important;
                min-height:37px !important;
                height:37px !important;
                font-size:12px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
def _mostrar_ots_sin_planta(ordenes):
    """
    Muestra las OT antiguas que todavía no tienen planta real.

    No modifica la OT ni inventa una planta.
    El operario puede seguir trabajándolas normalmente.
    """

    pendientes = [
        ot
        for ot in ordenes or []
        if ot.get("_sin_ubicar", False)
    ]

    if not pendientes:
        return

    pendientes = _ordenar_misiones(
        pendientes
    )

    st.warning(
        f"📍 {len(pendientes)} OT "
        f"{'pendiente' if len(pendientes) == 1 else 'pendientes'} "
        "de ubicar en una planta"
    )

    with st.expander(
        "Ver OT sin planta",
        expanded=False
    ):
        for ot in pendientes:
            numero_ot = str(
                ot.get("numero_ot")
                or ot.get("id")
                or "OT"
            ).strip()

            espacio = _texto_aula(
                ot
            )

            descripcion = _texto_averia(
                ot
            )

            prioridad = str(
                ot.get("prioridad")
                or "Media"
            ).strip()

            estado = str(
                ot.get("estado")
                or "Abierta"
            ).strip()

            with st.container(
                border=True
            ):
                st.markdown(
                    f"**{numero_ot} · {espacio}**"
                )

                st.markdown(
                    descripcion
                )

                st.caption(
                    f"{prioridad} · {estado} · 📍 Sin planta"
                )

                if ot.get("_ejecutable", False):
                    st.button(
                        f"▶ EMPEZAR {numero_ot}",
                        key=f"cv_sin_planta_{ot.get('id')}",
                        use_container_width=True,
                        on_click=_abrir_ot_para_trabajar,
                        args=(ot, "sin_planta"),
                    )

def pantalla_colegio_vivo_operario():

    # =====================================================
    # LATIDO AUTOMÁTICO · COLEGIO VIVO
    # Refresca únicamente esta pantalla cada 30 segundos.
    # Permite detectar nuevas OT/QR sin tocar ningún botón.
    # =====================================================
    st_autorefresh(
        interval=30_000,
        limit=None,
        key="latido_colegio_vivo_operario"
    )

    _css_pantalla_operario()
    css_edificio_vivo()

    if _mostrar_planta_seleccionada():
        return


    operario = str(
        st.session_state.get("operario_activo")
        or st.session_state.get("usuario")
        or ""
    ).strip()

    colegio = obtener_colegio_vivo(operario)

    centro_operario = _centro_del_operario(
        operario,
        colegio,
    )

    resumen = _crear_resumen_edificios(
        colegio
    )

    ordenes = _todas_las_ordenes(
        colegio
    )

    mision = _obtener_mision_corazon_colegio(
        operario=operario,
        centro=centro_operario,
        ordenes=ordenes,
    )

    # =====================================================
    # MI MISIÓN
    # =====================================================
    if mision:

        centro, edificio, planta = _ubicacion_mision(
            mision
        )

        aula = _texto_aula(
            mision
        )

        prioridad = str(
            mision.get("prioridad")
            or "Media"
        ).strip()

        descripcion = _texto_averia(
            mision
        )

        html_mision = (
            '<div class="cv-mission">'
            f'<div class="cv-mission-top">'
            f'❤️ MI MISIÓN · '
            f'{html.escape(prioridad.upper())}'
            f'</div>'
            f'<div class="cv-mission-place">'
            f'{html.escape(centro)} · '
            f'{html.escape(edificio)} · '
            f'{html.escape(planta)} · '
            f'{html.escape(aula)}'
            f'</div>'
            f'<div class="cv-mission-description">'
            f'{html.escape(descripcion)}'
            f'</div>'
            '</div>'
        )

        st.markdown(
            html_mision,
            unsafe_allow_html=True,
        )

        _mostrar_ot_en_curso_interrumpida(
            mision
        )

        _mostrar_recuerdo_corazon(
            mision
        )

        texto_boton = (
            "▶ CONTINUAR AHORA"
            if mision.get("_en_curso", False)
            else "▶ EMPEZAR AHORA"
        )

        st.button(
            texto_boton,
            key=(
                f"cv_empezar_"
                f"{mision.get('id', 'primera')}"
            ),
            type="primary",
            use_container_width=True,
            on_click=_abrir_ot_para_trabajar,
            args=(mision, "mision"),
        )

    else:
        st.markdown(
            '<div class="cv-no-work">'
            '✅ No tienes órdenes ejecutables.'
            '</div>',
            unsafe_allow_html=True,
        )

    # =====================================================
    # COLEGIO VIVO
    # =====================================================
    st.markdown(
        '<div class="cv-school-title">'
        '🏫 COLEGIO VIVO'
        '</div>',
        unsafe_allow_html=True,
    )

    _mostrar_ots_sin_planta(
        ordenes
    )

    if not centro_operario:
        st.info(
            "No hay un centro asignado a este operario."
        )
        return

    pintar_campus_operario(
        centro=centro_operario,
        resumen=resumen,
    )
