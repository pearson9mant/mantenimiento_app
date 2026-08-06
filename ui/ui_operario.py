import streamlit as st
from datetime import date
from pathlib import Path
from ui.ui_trabajar_ot import pantalla_trabajar_ot

from modules.ordenes import (
    obtener_ordenes_operario,
    obtener_historico,
    actualizar_estado,
    actualizar_observaciones_estado,
    finalizar_orden,
    obtener_fotos_ot,
    guardar_foto_ot,
    crear_correctiva_desde_ot
)

from modules.corazon_sistema import latido_corazon

from modules.inventario import (
    obtener_material_por_codigo,
    registrar_movimiento_inventario
)

from modules.preventivo import (
    obtener_checklist_preventivo,
    actualizar_checklist_preventivo,
    checklist_preventivo_completo,
    crear_checklist_preventivo,
)

from ui.ui_ot_controles import (
    mostrar_ejecucion_legionella_operario,
    mostrar_checklist_preventivo_operario,
    mostrar_checklist_correctivo_legionella_operario,
)

from ui.ui_legionella import obtener_checklist_correctivo_legionella


def rol_actual():
    return str(st.session_state.get("rol", "")).strip().lower()


def usuario_actual():
    return str(st.session_state.get("usuario", "")).strip()


def nombre_operario_actual():
    return str(
        st.session_state.get("operario_activo")
        or st.session_state.get("nombre")
        or usuario_actual()
    ).strip()


def es_admin():
    return rol_actual() == "admin"


def es_gerencia():
    return rol_actual() == "gerencia"


def es_operario():
    return rol_actual() == "operario"


def normalizar_txt(valor):
    return str(valor or "").strip().lower()


def normalizar_operario_nombre(nombre):
    texto = normalizar_txt(nombre)
    limpio = (
        texto.replace(".", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    if limpio in [
        "jaalmeda",
        "jalmeda",
        "juanantonio",
        "juanantonioalmeda",
        "jalmedac",
        "jalmedaabatolibaedu"
    ]:
        return "j.a. almeda"

    if limpio in [
        "luislozano",
        "llozano",
        "luis"
    ]:
        return "luis lozano"

    if limpio in [
        "abelvasquez",
        "abel",
        "avasquez"
    ]:
        return "abel vasquez"

    return texto


def puede_ver_legionella_operario(operario):
    operario_txt = normalizar_txt(operario)
    operario_txt = operario_txt.replace(".", "")
    operario_txt = operario_txt.replace(" ", "")
    operario_txt = operario_txt.replace("-", "")
    operario_txt = operario_txt.replace("_", "")

    return (
        "almeda" in operario_txt
        or operario_txt in ["ja", "jalmeda", "jaalmeda", "juanantonio"]
    )


def obtener_operario_fila(fila):
    try:
        return fila[10]
    except Exception:
        return ""


def es_ot_preventiva(origen, descripcion):
    origen_txt = str(origen or "").strip().upper()
    desc_txt = str(descripcion or "").strip().upper()
    return origen_txt == "PREVENTIVO" or desc_txt.startswith("[PREVENTIVO]")


def es_ot_legionella(area, origen, descripcion):
    area_txt = normalizar_txt(area)
    origen_txt = normalizar_txt(origen)
    desc_txt = normalizar_txt(descripcion)

    return (
        area_txt == "legionella"
        or origen_txt == "legionella"
        or desc_txt.startswith("control legionella")
        or desc_txt.startswith("correctivo legionella")
        or "correctivo legionella" in desc_txt
    )


def limpiar_tarea_preventiva(descripcion):
    texto = str(descripcion or "").strip()
    return texto.replace("[PREVENTIVO]", "").strip()


def normalizar_estado_operario(estado):
    estado = str(estado or "").strip().lower()

    if estado in ["finalizada", "finalizado", "cerrada", "cerrado"]:
        return "Hechas"

    if estado in ["en curso", "en proceso"]:
        return "En proceso"

    if estado in ["abierta", "pendiente", "pendiente material", "esperando material"]:
        return "Faltan"

    return "Faltan"


def fecha_es_hoy(valor):
    hoy = date.today().strftime("%Y-%m-%d")
    texto = str(valor or "").strip()
    return texto[:10] == hoy


def calcular_kpis_operario(ordenes, historico=None, operario_sel=""):
    historico = historico or []

    total = len(ordenes)

    en_proceso = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() == "En curso"
    ])

    faltan = len([
        o for o in ordenes
        if len(o) > 3 and str(o[3] or "").strip() in ["Abierta", "Pendiente material"]
    ])

    hechas_hoy = 0
    operario_objetivo = normalizar_operario_nombre(operario_sel)

    for h in historico:
        try:
            fecha_cierre_hist = h[14]
            operario_hist = h[10]
        except Exception:
            continue

        if normalizar_operario_nombre(operario_hist) != operario_objetivo:
            continue

        if fecha_es_hoy(fecha_cierre_hist):
            hechas_hoy += 1

    base_rendimiento = hechas_hoy + en_proceso + faltan
    rendimiento = round((hechas_hoy / base_rendimiento) * 100, 1) if base_rendimiento else 0

    return {
        "total": total,
        "hechas": hechas_hoy,
        "en_proceso": en_proceso,
        "faltan": faltan,
        "rendimiento": rendimiento,
    }


def mostrar_cabecera_resumen_operario(operario_sel, ordenes_activas):
    """
    Cabecera ligera del operario.

    Solo utiliza las órdenes activas que ya se han cargado para el listado.
    No consulta el histórico, fotos, materiales ni checklists, evitando
    añadir carga innecesaria a la pantalla principal.
    """
    ordenes_activas = ordenes_activas or []

    total_activas = len(ordenes_activas)

    en_curso = len([
        o for o in ordenes_activas
        if len(o) > 3
        and str(o[3] or "").strip() == "En curso"
    ])

    pendientes = len([
        o for o in ordenes_activas
        if len(o) > 3
        and str(o[3] or "").strip()
        in ["Abierta", "Pendiente material"]
    ])

    urgentes = len([
        o for o in ordenes_activas
        if len(o) > 9
        and str(o[9] or "").strip() == "Urgente"
    ])

    nombre = str(operario_sel or "").strip()

    st.markdown(
        f"### 👷 Buenos días, {nombre}"
    )

    st.caption(
        "Resumen de tu jornada de trabajo."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "📋 Activas",
        total_activas
    )

    col2.metric(
        "🟠 En curso",
        en_curso
    )

    col3.metric(
        "⏳ Pendientes",
        pendientes
    )

    col4.metric(
        "🚨 Urgentes",
        urgentes
    )

    st.markdown("---")


def descomponer_orden_operario(fila):
    observaciones_estado = ""

    if len(fila) >= 26:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
            tipo_solicitante,
            tipo_orden,
            empresa_externa,
            contacto_empresa,
            telefono_empresa,
            email_empresa,
            fecha_programada,
            fecha_realizacion,
            coste_estimado,
            coste_final,
            observaciones_estado,
        ) = fila[:26]

    elif len(fila) >= 16:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
            tipo_solicitante,
        ) = fila[:16]

    elif len(fila) == 15:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen,
            solicitante,
            fecha_origen,
            foto,
        ) = fila
        tipo_solicitante = "Operarios"

    else:
        (
            id_orden,
            num_ot,
            desc,
            est,
            fecha,
            centro,
            edificio,
            espacio,
            area,
            prioridad,
            operario,
            origen
        ) = fila[:12]
        solicitante = ""
        fecha_origen = ""
        foto = ""
        tipo_solicitante = "Operarios"

    return (
        id_orden,
        num_ot,
        desc,
        est,
        fecha,
        centro,
        edificio,
        espacio,
        area,
        prioridad,
        operario,
        origen,
        solicitante,
        fecha_origen,
        foto,
        tipo_solicitante,
        observaciones_estado,
    )


def puede_finalizar_preventivo(num_ot, origen, desc):
    if es_ot_preventiva(origen, desc):
        return checklist_preventivo_completo(num_ot)
    return True


def puede_finalizar_legionella(id_orden, area, origen, desc, num_ot=None):
    desc_txt = str(desc or "").upper()

    if "CORRECTIVO LEGIONELLA" in desc_txt:
        checklist = obtener_checklist_correctivo_legionella(num_ot)

        if not checklist:
            return False

        causa = str(checklist.get("causa_detectada") or "").strip()

        return (
            causa != ""
            and bool(checklist.get("nueva_medicion", 0))
            and float(checklist.get("temperatura_final", 0) or 0) >= 50
        )

    if es_ot_legionella(area, origen, desc):
        return st.session_state.get(f"legionella_guardada_{id_orden}", False)

    return True


def mostrar_crear_correctiva_desde_revision(
    id_orden,
    num_ot,
    centro,
    edificio,
    espacio,
    area,
    prioridad,
    operario,
    origen_base
):
    st.markdown("### 🛠️ Crear correctivas si hay defectos")

    st.info(
        "Escribe un defecto por línea. "
        "Se creará una OT correctiva independiente por cada línea."
    )

    defectos_texto = st.text_area(
        "Defectos encontrados",
        placeholder=(
            "Ejemplo:\n"
            "P0/ACS01 - Grifo cocina pierde agua\n"
            "P0/ACS02 - Grifo cocina sin caudal\n"
            "Luz emergencia pasillo sin batería"
        ),
        key=f"defectos_correctivas_{id_orden}",
        height=150
    )

    crear_correctivas = st.checkbox(
        "Crear OT correctivas automáticas",
        key=f"crear_correctivas_auto_{id_orden}"
    )

    if st.button(
        "➕ Crear correctivas",
        key=f"btn_crear_correctivas_{id_orden}",
        use_container_width=True
    ):
        if not crear_correctivas:
            st.warning("Marca la casilla para crear las OT correctivas.")
            return False

        defectos = [
            d.strip()
            for d in str(defectos_texto or "").splitlines()
            if d.strip()
        ]

        if not defectos:
            st.warning("Escribe al menos un defecto.")
            return False

        creadas = 0
        errores = []

        for defecto in defectos:
            ok, mensaje = crear_correctiva_desde_ot(
                centro=centro,
                edificio=edificio,
                espacio=espacio,
                area=area,
                prioridad=prioridad,
                operario=operario,
                descripcion_defecto=defecto,
                numero_ot_origen=num_ot,
                origen=origen_base,
                solicitante="Operarios",
            )

            if ok:
                creadas += 1
            else:
                errores.append(mensaje)

        if creadas > 0:
            st.success(f"Se han creado {creadas} OT correctivas independientes.")
            st.session_state[f"correctiva_creada_{id_orden}"] = True

        if errores:
            for error in errores:
                st.warning(error)

        st.rerun()

    if st.session_state.get(f"correctiva_creada_{id_orden}", False):
        st.success("Ya se han creado correctivas desde esta revisión.")

    return st.session_state.get(f"correctiva_creada_{id_orden}", False)


def filtrar_seguridad_operario(ordenes, operario_sel):
    if not ordenes:
        return []

    operario_objetivo = normalizar_operario_nombre(operario_sel)

    return [
        o for o in ordenes
        if len(o) > 10
        and normalizar_operario_nombre(o[10]) == operario_objetivo
    ]


def cargar_ordenes_activas_operario(operario_sel):
    """
    Consulta únicamente las órdenes del operario y devuelve las activas.
    No carga fotos, materiales, checklists ni controles asociados.
    """
    ordenes_operario = obtener_ordenes_operario(operario_sel)

    ordenes_operario = filtrar_seguridad_operario(
        ordenes_operario,
        operario_sel
    )

    return [
        o for o in ordenes_operario
        if len(o) > 3
        and str(o[3] or "").strip()
        in [
            "Abierta",
            "En curso",
            "En pausa",
            "En ejecución",
            "Pendiente material",
            "Pendiente proveedor",
            "Pendiente presupuesto",
            "Avisado",
        ]
    ]


def buscar_ot_operario_por_id(ordenes, id_ot):
    """Localiza una única OT por su ID dentro de las órdenes permitidas."""
    if id_ot is None:
        return None

    for fila in ordenes or []:
        try:
            if int(fila[0]) == int(id_ot):
                return fila
        except (TypeError, ValueError, IndexError):
            continue

    return None


def filtrar_ordenes_activas_operario(ordenes_activas, filtro):
    """Aplica los filtros del listado sin cargar el detalle de las OT."""
    if filtro == "Preventivo":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "PREVENTIVO"
        ]

    if filtro == "Legionella":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "LEGIONELLA"
        ]

    if filtro == "☀️ Verano":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper() == "VERANO"
        ]

    if filtro == "Incidencias":
        return [
            o for o in ordenes_activas
            if len(o) > 11
            and str(o[11] or "").strip().upper()
            in [
                "APP",
                "OUTLOOK",
                "PROFESORES"
            ]
        ]

    return ordenes_activas


def mostrar_resumen_ot_operario(fila):
    """
    Muestra una fila ligera de la OT.
    No llama a mostrar_tarjeta_ot ni prepara controles internos.
    """
    try:
        id_ot = fila[0]
        numero_ot = fila[1]
        descripcion = fila[2]
        estado = fila[3]
        centro_ot = fila[5]
        edificio_ot = fila[6]
        espacio_ot = fila[7]
        prioridad_ot = fila[9]
        origen_ot = fila[11] if len(fila) > 11 else ""
    except (TypeError, IndexError):
        return

    estado_txt = str(estado or "").strip()
    prioridad_txt = str(prioridad_ot or "").strip()
    origen_txt = str(origen_ot or "").strip()

    icono_estado = {
        "Abierta": "🔴",
        "En curso": "🟠",
        "En pausa": "⏸️",
        "En ejecución": "🟠",
        "Pendiente material": "📦",
        "Pendiente proveedor": "🏢",
        "Pendiente presupuesto": "💶",
        "Avisado": "📨",
    }.get(estado_txt, "⚪")

    icono_prioridad = {
        "Urgente": "🚨",
        "Alta": "🔴",
        "Media": "🟠",
        "Baja": "🟢",
    }.get(prioridad_txt, "⚪")

    descripcion_corta = (
        str(descripcion or "")
        .replace("\n", " ")
        .strip()
    )

    if len(descripcion_corta) > 120:
        descripcion_corta = descripcion_corta[:120].rstrip() + "..."

    with st.container(border=True):
        st.markdown(
            f"### {icono_estado} {numero_ot or '-'}"
        )

        st.markdown(
            f"{icono_prioridad} **{prioridad_txt or '-'}** · "
            f"{estado_txt or '-'}"
        )

        st.caption(
            f"🏢 {centro_ot or '-'} · "
            f"{edificio_ot or '-'} · "
            f"{espacio_ot or '-'}"
        )

        if origen_txt:
            st.caption(f"Origen: {origen_txt}")

        st.markdown(descripcion_corta or "Sin descripción.")

        if st.button(
            "🔎 Abrir y trabajar esta OT",
            key=f"abrir_ot_operario_{id_ot}",
            use_container_width=True
        ):
            try:
                st.session_state["operario_ot_abierta_id"] = int(id_ot)
            except (TypeError, ValueError):
                st.error("No se ha podido abrir esta orden.")
            else:
                st.rerun()



def _nombre_corto_operario(operario):
    nombre = str(operario or "").strip()

    normalizado = normalizar_operario_nombre(nombre)

    if normalizado == "j.a. almeda":
        return "Juan Antonio"

    if normalizado == "luis lozano":
        return "Luis"

    if normalizado == "abel vasquez":
        return "Abel"

    if not nombre:
        return "Operario"

    return nombre.split()[0]


def _fecha_orden_atrasada(valor):
    """
    Considera atrasada una OT con fecha anterior a hoy.
    Admite fechas YYYY-MM-DD y otros valores convertibles a texto.
    """
    texto = str(valor or "").strip()

    if not texto:
        return False

    try:
        fecha_orden = date.fromisoformat(texto[:10])
    except Exception:
        return False

    return fecha_orden < date.today()


def _datos_resumen_orden(fila):
    try:
        return {
            "id": fila[0],
            "numero": fila[1],
            "descripcion": fila[2],
            "estado": fila[3],
            "fecha": fila[4],
            "centro": fila[5],
            "edificio": fila[6],
            "espacio": fila[7],
            "area": fila[8],
            "prioridad": fila[9],
            "operario": fila[10],
            "origen": fila[11] if len(fila) > 11 else "",
        }
    except Exception:
        return None


def _prioridad_peso(prioridad):
    prioridad_txt = normalizar_txt(prioridad)

    pesos = {
        "urgente": 100,
        "alta": 40,
        "media": 15,
        "normal": 10,
        "baja": 5,
    }

    return pesos.get(prioridad_txt, 8)


def _resumir_edificios_operario(ordenes_activas):
    """
    Agrupa en memoria las OT ya cargadas.
    No realiza nuevas consultas.
    """
    resumen = {}

    for fila in ordenes_activas or []:
        datos = _datos_resumen_orden(fila)

        if not datos:
            continue

        edificio = str(
            datos.get("edificio") or "Sin edificio"
        ).strip()

        if edificio not in resumen:
            resumen[edificio] = {
                "ordenes": [],
                "total": 0,
                "urgentes": 0,
                "altas": 0,
                "atrasadas": 0,
                "en_curso": 0,
                "puntuacion": 0,
            }

        bloque = resumen[edificio]
        bloque["ordenes"].append(fila)
        bloque["total"] += 1

        prioridad = normalizar_txt(
            datos.get("prioridad")
        )

        estado = normalizar_txt(
            datos.get("estado")
        )

        if prioridad == "urgente":
            bloque["urgentes"] += 1

        if prioridad == "alta":
            bloque["altas"] += 1

        if estado in ["en curso", "en proceso"]:
            bloque["en_curso"] += 1

        atrasada = _fecha_orden_atrasada(
            datos.get("fecha")
        )

        if atrasada:
            bloque["atrasadas"] += 1

        bloque["puntuacion"] += _prioridad_peso(
            datos.get("prioridad")
        )

        if atrasada:
            bloque["puntuacion"] += 20

        if estado in ["en curso", "en proceso"]:
            bloque["puntuacion"] += 6

    return resumen


def _edificio_recomendado(resumen_edificios):
    if not resumen_edificios:
        return None

    return max(
        resumen_edificios,
        key=lambda edificio: (
            resumen_edificios[edificio]["urgentes"],
            resumen_edificios[edificio]["atrasadas"],
            resumen_edificios[edificio]["puntuacion"],
            resumen_edificios[edificio]["total"],
        )
    )


def _texto_recomendacion_edificio(
    nombre_operario,
    edificio,
    datos
):
    urgentes = int(datos.get("urgentes", 0) or 0)
    atrasadas = int(datos.get("atrasadas", 0) or 0)
    total = int(datos.get("total", 0) or 0)

    if urgentes > 0:
        return (
            f"**Hoy empezaría por {edificio}.** "
            f"Es donde tienes {urgentes} "
            f"{'urgencia' if urgentes == 1 else 'urgencias'} y puedes "
            f"aprovechar para resolver {total} "
            f"{'actuación' if total == 1 else 'actuaciones'} "
            f"en el mismo edificio."
        )

    if atrasadas > 0:
        return (
            f"**Hoy empezaría por {edificio}.** "
            f"Es donde tienes más trabajo atrasado "
            f"({atrasadas} "
            f"{'actuación' if atrasadas == 1 else 'actuaciones'}) "
            f"y puedes aprovechar el desplazamiento para atender "
            f"{total} trabajos."
        )

    return (
        f"**Hoy empezaría por {edificio}.** "
        f"Es el edificio donde concentras más trabajo "
        f"({total} "
        f"{'actuación' if total == 1 else 'actuaciones'})."
    )


def _icono_prioridad_operario(prioridad):
    prioridad_txt = normalizar_txt(prioridad)

    return {
        "urgente": "🚨",
        "alta": "🔴",
        "media": "🟠",
        "normal": "🟡",
        "baja": "🟢",
    }.get(prioridad_txt, "⚪")


def _ordenar_ordenes_jornada(ordenes):
    def clave(fila):
        datos = _datos_resumen_orden(fila) or {}

        urgente = (
            1
            if normalizar_txt(datos.get("prioridad"))
            == "urgente"
            else 0
        )

        atrasada = (
            1
            if _fecha_orden_atrasada(datos.get("fecha"))
            else 0
        )

        peso = _prioridad_peso(
            datos.get("prioridad")
        )

        return (
            -urgente,
            -atrasada,
            -peso,
            str(datos.get("fecha") or ""),
        )

    return sorted(
        ordenes or [],
        key=clave
    )


def _mostrar_fila_jornada_operario(fila):
    datos = _datos_resumen_orden(fila)

    if not datos:
        return

    id_ot = datos["id"]
    numero = datos["numero"]
    descripcion = str(
        datos["descripcion"] or "Sin descripción."
    ).replace("\n", " ").strip()

    if len(descripcion) > 150:
        descripcion = (
            descripcion[:150].rstrip()
            + "..."
        )

    espacio = str(
        datos["espacio"] or "Sin espacio"
    ).strip()

    prioridad = str(
        datos["prioridad"] or "-"
    ).strip()

    area = str(
        datos["area"] or "-"
    ).strip()

    estado = str(
        datos["estado"] or "-"
    ).strip()

    icono = _icono_prioridad_operario(
        prioridad
    )

    atrasada = _fecha_orden_atrasada(
        datos["fecha"]
    )

    marca_atrasada = (
        " · ⏰ Atrasada"
        if atrasada
        else ""
    )

    col_info, col_abrir = st.columns(
        [18, 2],
        gap="small",
        vertical_alignment="center"
    )

    with col_info:
        st.markdown(
            f"{icono} **{espacio}** · "
            f"`{numero or '-'}` · "
            f"{prioridad} · {area}"
            f"{marca_atrasada}  \n"
            f"{descripcion}"
        )

        st.caption(
            f"Estado: {estado}"
        )

    with col_abrir:
        if st.button(
            "▶",
            key=f"jornada_abrir_ot_{id_ot}",
            help="Abrir y trabajar esta OT",
            use_container_width=True
        ):
            try:
                st.session_state[
                    "operario_ot_abierta_id"
                ] = int(id_ot)
            except (TypeError, ValueError):
                st.error(
                    "No se ha podido abrir esta orden."
                )
            else:
                st.rerun()


def _agrupar_ordenes_por_planta(ordenes):
    """
    La tabla de OT no dispone siempre de planta.
    Se utiliza el espacio como agrupación operativa cuando no existe
    una planta explícita en la fila.
    """
    grupos = {}

    for fila in ordenes or []:
        datos = _datos_resumen_orden(fila)

        if not datos:
            continue

        espacio = str(
            datos.get("espacio") or "Sin ubicación"
        ).strip()

        # Agrupación estable y compatible con la estructura actual.
        grupo = "Ubicaciones"

        grupos.setdefault(
            grupo,
            []
        ).append(fila)

    return grupos



def _buscar_fila_mision_en_ordenes(ordenes_activas, mision):
    """Relaciona la misión del Corazón con la fila ligera ya cargada."""
    if not mision:
        return None

    id_mision = mision.get("id")
    numero_mision = str(mision.get("numero_ot") or "").strip()

    for fila in ordenes_activas or []:
        try:
            if id_mision is not None and int(fila[0]) == int(id_mision):
                return fila
        except (TypeError, ValueError, IndexError):
            pass

        try:
            if numero_mision and str(fila[1] or "").strip() == numero_mision:
                return fila
        except (TypeError, IndexError):
            pass

    return None


def _abrir_ot_desde_corazon(id_ot):
    try:
        st.session_state["operario_ot_abierta_id"] = int(id_ot)
    except (TypeError, ValueError):
        st.error("No se ha podido abrir la misión seleccionada.")
        return False

    st.rerun()
    return True


def _urgencia_nueva_mientras_trabaja(ordenes_activas, id_actual):
    """Detecta una urgencia abierta distinta de la misión en curso."""
    candidatas = []

    for fila in ordenes_activas or []:
        datos = _datos_resumen_orden(fila)
        if not datos:
            continue

        try:
            misma = int(datos.get("id")) == int(id_actual)
        except (TypeError, ValueError):
            misma = False

        if misma:
            continue

        if normalizar_txt(datos.get("estado")) not in ["abierta", "en pausa"]:
            continue

        if normalizar_txt(datos.get("prioridad")) != "urgente":
            continue

        candidatas.append(fila)

    if not candidatas:
        return None

    return _ordenar_ordenes_jornada(candidatas)[0]


def mostrar_mision_corazon_operario(operario_sel, ordenes_activas):
    """Muestra una única misión accionable antes de la ruta de jornada."""
    try:
        latido = latido_corazon(operario=operario_sel)
    except Exception as e:
        st.warning("El Corazón no ha podido calcular la misión actual.")
        st.caption(str(e))
        return

    estado_corazon = str(latido.get("estado_corazon") or "").strip()
    mision = latido.get("mision") or {}
    bloqueadas = int(latido.get("bloqueadas", 0) or 0)

    st.markdown("### ❤️ Misión actual")

    if not mision:
        if estado_corazon == "todo_bloqueado":
            st.info(
                f"Tienes {bloqueadas} órdenes activas esperando material, "
                "proveedor, aviso o presupuesto."
            )
        else:
            st.success(latido.get("mensaje") or "No hay una misión pendiente.")
        return

    fila_mision = _buscar_fila_mision_en_ordenes(ordenes_activas, mision)
    id_ot = mision.get("id")
    numero = str(mision.get("numero_ot") or "-").strip()
    descripcion = str(mision.get("descripcion") or "Sin descripción.").strip()
    centro = str(mision.get("centro") or "-").strip()
    edificio = str(mision.get("edificio") or "-").strip()
    planta = str(
        mision.get("planta_resuelta_corazon")
        or mision.get("planta")
        or "Sin planta"
    ).strip()
    espacio = str(mision.get("espacio") or "-").strip()
    prioridad = str(mision.get("prioridad") or "-").strip()
    area = str(mision.get("area") or "-").strip()
    score = mision.get("score_corazon")
    motivos = mision.get("motivos_corazon") or []

    icono = _icono_prioridad_operario(prioridad)
    trabajando = estado_corazon == "continuar"

    with st.container(border=True):
        titulo = "❤️ TRABAJANDO" if trabajando else "🎯 SIGUIENTE MISIÓN"
        st.markdown(f"#### {titulo}")
        st.markdown(f"### {icono} {numero}")
        st.markdown(descripcion)
        st.caption(
            f"🏢 {centro} · {edificio} · {planta} · {espacio}  |  "
            f"{prioridad} · {area}"
        )

        if score is not None and not trabajando:
            st.caption(f"Prioridad calculada por el Corazón: {score}/100")

        if motivos:
            with st.expander("Por qué recomienda esta misión", expanded=False):
                for motivo in motivos[:5]:
                    st.markdown(f"• {motivo}")

        if bloqueadas:
            st.caption(f"📦 {bloqueadas} órdenes quedan fuera de la ruta por estar bloqueadas.")

        if trabajando:
            urgencia = _urgencia_nueva_mientras_trabaja(
                ordenes_activas,
                id_actual=id_ot,
            )

            if urgencia is not None:
                datos_urgencia = _datos_resumen_orden(urgencia) or {}
                st.warning(
                    "🚨 Ha entrado otra OT urgente. Puedes atenderla ahora; "
                    "la misión actual pasará automáticamente a En pausa."
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button(
                        "🚨 Atender urgencia",
                        key=f"corazon_atender_urgencia_{datos_urgencia.get('id')}",
                        use_container_width=True,
                    ):
                        resultado = actualizar_estado(
                            datos_urgencia.get("id"),
                            "En curso",
                        )
                        if isinstance(resultado, dict) and not resultado.get("ok", False):
                            st.error("No se ha podido iniciar la urgencia.")
                        else:
                            _abrir_ot_desde_corazon(datos_urgencia.get("id"))

                with c2:
                    if st.button(
                        "▶ Continuar la actual",
                        key=f"corazon_continuar_actual_{id_ot}",
                        use_container_width=True,
                    ):
                        _abrir_ot_desde_corazon(id_ot)
            else:
                if st.button(
                    "▶ Continuar misión",
                    key=f"corazon_continuar_{id_ot}",
                    use_container_width=True,
                    type="primary",
                ):
                    _abrir_ot_desde_corazon(id_ot)

        else:
            c1, c2 = st.columns([2, 1])

            with c1:
                if st.button(
                    "▶ Empezar misión",
                    key=f"corazon_empezar_{id_ot}",
                    use_container_width=True,
                    type="primary",
                ):
                    resultado = actualizar_estado(id_ot, "En curso")

                    if isinstance(resultado, dict) and not resultado.get("ok", False):
                        st.error("No se ha podido iniciar la misión.")
                    else:
                        _abrir_ot_desde_corazon(id_ot)

            with c2:
                if st.button(
                    "🔎 Solo abrir",
                    key=f"corazon_abrir_{id_ot}",
                    use_container_width=True,
                ):
                    _abrir_ot_desde_corazon(id_ot)

    st.markdown("---")


def pantalla_mi_jornada_operario(
    operario_sel,
    ordenes_activas
):
    """
    Entrada inteligente del operario.

    Reutiliza exclusivamente las órdenes activas ya cargadas.
    No consulta fotos, materiales, histórico, checklists ni controles.
    """
    nombre_corto = _nombre_corto_operario(
        operario_sel
    )

    st.markdown(
        f"## 👷 Buenos días, {nombre_corto}"
    )

    mostrar_mision_corazon_operario(
        operario_sel,
        ordenes_activas,
    )

    if not ordenes_activas:
        st.success(
            "🟢 No tienes órdenes activas. "
            "Es un buen momento para revisar preventivos "
            "o apoyar otras tareas del centro."
        )
        return

    resumen = _resumir_edificios_operario(
        ordenes_activas
    )

    recomendado = _edificio_recomendado(
        resumen
    )

    if recomendado is None:
        st.info(
            "No se ha podido determinar un edificio recomendado."
        )
        return

    datos_recomendado = resumen[
        recomendado
    ]

    st.info(
        _texto_recomendacion_edificio(
            nombre_corto,
            recomendado,
            datos_recomendado
        )
    )

    urgentes_totales = sum(
        datos["urgentes"]
        for datos in resumen.values()
    )

    atrasadas_totales = sum(
        datos["atrasadas"]
        for datos in resumen.values()
    )

    c1, c2, c3 = st.columns(
        3,
        gap="small"
    )

    c1.metric(
        "🚨 Urgentes",
        urgentes_totales
    )

    c2.metric(
        "⏰ Atrasadas",
        atrasadas_totales
    )

    c3.metric(
        "📋 Activas",
        len(ordenes_activas)
    )

    edificios_ordenados = sorted(
        resumen.keys(),
        key=lambda edificio: (
            edificio != recomendado,
            -resumen[edificio]["urgentes"],
            -resumen[edificio]["atrasadas"],
            -resumen[edificio]["total"],
            edificio,
        )
    )

    etiquetas = [
        (
            f"🏫 {edificio} "
            f"({resumen[edificio]['total']})"
        )
        for edificio in edificios_ordenados
    ]

    indice_recomendado = edificios_ordenados.index(
        recomendado
    )

    etiqueta_edificio = st.radio(
        "Edificios",
        options=etiquetas,
        index=indice_recomendado,
        horizontal=True,
        label_visibility="collapsed",
        key="jornada_edificio_activo"
    )

    indice_edificio = etiquetas.index(
        etiqueta_edificio
    )

    edificio_activo = edificios_ordenados[
        indice_edificio
    ]

    datos_edificio = resumen[
        edificio_activo
    ]

    urgencias = datos_edificio["urgentes"]
    atrasadas = datos_edificio["atrasadas"]

    resumen_texto = (
        f"{datos_edificio['total']} actuaciones"
    )

    if urgencias:
        resumen_texto += (
            f" · {urgencias} urgentes"
        )

    if atrasadas:
        resumen_texto += (
            f" · {atrasadas} atrasadas"
        )

    st.caption(resumen_texto)

    ordenes_edificio = _ordenar_ordenes_jornada(
        datos_edificio["ordenes"]
    )

    # Se mantienen agrupadas en un bloque compacto.
    # Cuando las OT incorporen planta explícita, esta función
    # podrá agruparlas por planta sin cambiar el resto del flujo.
    grupos = _agrupar_ordenes_por_planta(
        ordenes_edificio
    )

    for nombre_grupo, ordenes_grupo in grupos.items():
        with st.expander(
            f"📍 {nombre_grupo} "
            f"({len(ordenes_grupo)})",
            expanded=True
        ):
            for fila in ordenes_grupo:
                _mostrar_fila_jornada_operario(
                    fila
                )


def pantalla_entrada_operario(
    operario_sel,
    ordenes_activas
):
    """
    Permite alternar entre la nueva jornada inteligente
    y el listado tradicional, que se conserva intacto.
    """
    vista = st.radio(
        "Vista del operario",
        [
            "🎯 Mi jornada",
            "📋 Todas mis órdenes",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="vista_principal_operario"
    )

    if vista == "🎯 Mi jornada":
        pantalla_mi_jornada_operario(
            operario_sel,
            ordenes_activas
        )
        return

    pantalla_listado_ordenes_operario(
        operario_sel,
        ordenes_activas
    )

def pantalla_listado_ordenes_operario(operario_sel, ordenes_activas):
    """Pantalla ligera: filtros, paginación y resúmenes de OT."""
    st.markdown("## 📋 Mis órdenes")

    filtro_origen_operario = st.radio(
        "",
        [
            "Todas",
            "Incidencias",
            "Preventivo",
            "Legionella",
            "☀️ Verano"
        ],
        horizontal=True,
        key="filtro_origen_operario"
    )

    ordenes_filtradas = filtrar_ordenes_activas_operario(
        ordenes_activas,
        filtro_origen_operario
    )

    if not ordenes_filtradas:
        st.success("No tienes órdenes pendientes en este filtro.")
        return

    elementos_por_pagina = 15
    total_ordenes = len(ordenes_filtradas)

    total_paginas = max(
        1,
        (total_ordenes + elementos_por_pagina - 1)
        // elementos_por_pagina
    )

    pagina_guardada = int(
        st.session_state.get("pagina_ordenes_operario", 1) or 1
    )

    if pagina_guardada > total_paginas:
        st.session_state["pagina_ordenes_operario"] = total_paginas

    if total_paginas > 1:
        pagina = st.number_input(
            "Página de órdenes",
            min_value=1,
            max_value=total_paginas,
            value=min(pagina_guardada, total_paginas),
            step=1,
            key="pagina_ordenes_operario"
        )
    else:
        pagina = 1

    inicio = (int(pagina) - 1) * elementos_por_pagina
    fin = inicio + elementos_por_pagina
    ordenes_pagina = ordenes_filtradas[inicio:fin]

    st.caption(
        f"Mostrando {inicio + 1}–"
        f"{min(fin, total_ordenes)} "
        f"de {total_ordenes} órdenes."
    )

    for fila in ordenes_pagina:
        mostrar_resumen_ot_operario(fila)


def pantalla_trabajar_ot_operario(operario_sel, ordenes_activas):
    """
    Pantalla de detalle: carga y construye una sola OT completa.
    Toda la lógica existente continúa dentro de mostrar_tarjeta_ot().
    """
    id_ot_abierta = st.session_state.get("operario_ot_abierta_id")

    fila_abierta = buscar_ot_operario_por_id(
        ordenes_activas,
        id_ot_abierta
    )

    if fila_abierta is None:
        st.session_state.pop("operario_ot_abierta_id", None)
        st.session_state.pop("colegio_vivo_origen_ot", None)
        st.warning(
            "La OT seleccionada ya no está disponible o ya ha sido finalizada."
        )

        if st.button(
            "⬅ Volver al listado de órdenes",
            key="volver_listado_ot_no_disponible",
            use_container_width=True
        ):
            st.rerun()

        return

    try:
        numero_ot = fila_abierta[1]
    except Exception:
        numero_ot = ""

    origen_colegio_vivo = st.session_state.get(
        "colegio_vivo_origen_ot"
    )

    if origen_colegio_vivo == "planta":
        texto_volver = "⬅ Volver a las OT de la planta"
        key_volver = "volver_ot_planta_colegio_vivo"
    elif origen_colegio_vivo == "mision":
        texto_volver = "⬅ Volver a Colegio Vivo"
        key_volver = "volver_ot_mision_colegio_vivo"
    else:
        texto_volver = "⬅ Volver al listado de órdenes"
        key_volver = "volver_listado_ordenes_operario"

    pantalla_trabajar_ot(
        fila=fila_abierta,
        operario_sel=operario_sel,
        modo="operario",
        clave_ot_abierta="operario_ot_abierta_id",
        texto_volver=texto_volver,
        key_boton_volver=key_volver,
        titulo=f"## 🛠️ Trabajar OT {numero_ot or ''}",
    )



def _redirigir_regreso_colegio_vivo():
    """
    Después de finalizar una OT, devuelve exactamente
    al punto desde el que se abrió (Misión o Planta).
    """

    origen = str(
        st.session_state.get("colegio_vivo_origen_ot") or ""
    ).strip().lower()

    if origen not in ("mision", "planta"):
        return False

    # Solo actuamos cuando una OT ha sido finalizada.
    if not st.session_state.pop("recalcular_corazon", False):
        return False

    # Ya no debe quedar ninguna OT abierta.
    st.session_state.pop("operario_ot_abierta_id", None)

    st.session_state["seccion_actual"] = "Colegio Vivo"

    if origen == "planta":
        st.session_state["colegio_vivo_vista"] = "planta"
    else:
        st.session_state["colegio_vivo_vista"] = "mapa"

    st.session_state.pop("colegio_vivo_origen_ot", None)

    st.rerun()
    return True


def pantalla_operario(modo="ordenes"):
    solo_historico = (
        str(modo or "").strip().lower()
        == "historico"
    )

    if not solo_historico:
        _redirigir_regreso_colegio_vivo()

    id_ot_abierta = st.session_state.get(
        "operario_ot_abierta_id"
    )

    ot_abierta = (
        id_ot_abierta is not None
    )

    # Al entrar en histórico nunca se conserva una OT abierta.
    if solo_historico:
        st.session_state.pop(
            "operario_ot_abierta_id",
            None,
        )

        st.session_state.pop(
            "colegio_vivo_origen_ot",
            None,
        )

        st.title("📁 Mi histórico")

    elif not ot_abierta:
        st.title("👷 Operario")

    # =====================================================
    # VOLVER A ADMINISTRACIÓN
    # =====================================================
    if st.session_state.get(
        "vista_operario",
        False,
    ):
        if st.button(
            "🔙 Volver a administración",
            key="volver_admin_pantalla_operario",
        ):
            st.session_state[
                "vista_operario"
            ] = False

            st.session_state.pop(
                "operario_ot_abierta_id",
                None,
            )

            st.rerun()

    # =====================================================
    # OPERARIO ACTUAL
    # =====================================================
    operario_sel = str(
        st.session_state.get(
            "operario_activo",
            "",
        )
        or ""
    ).strip()

    if es_operario():
        operario_sel = str(
            nombre_operario_actual()
            or ""
        ).strip()

        st.session_state[
            "operario_activo"
        ] = operario_sel

    if not operario_sel:
        st.warning(
            "No hay operario seleccionado."
        )
        return

    if not ot_abierta:
        st.info(
            f"Operario: {operario_sel}"
        )

    # =====================================================
    # CARGA ÚNICA DE ÓRDENES ACTIVAS
    # Se reutiliza para la cabecera, el listado y trabajar una OT.
    # =====================================================
    ordenes_activas = []

    if not solo_historico:
        try:
            ordenes_activas = cargar_ordenes_activas_operario(
                operario_sel
            )
        except Exception as e:
            st.error(
                "No se han podido cargar las órdenes del operario."
            )
            st.caption(str(e))
            return

        # La administración conserva la cabecera clásica.
        # El operario real utiliza la cabecera de Mi jornada.
        if not es_operario():
            mostrar_cabecera_resumen_operario(
                operario_sel,
                ordenes_activas
            )

    # =====================================================
    # MODO ÓRDENES
    # Listado ligero o una única OT abierta
    # =====================================================
    if not solo_historico:
    
        # Legionella se ofrece únicamente desde el listado.
        # Al trabajar una OT no se construyen otras pantallas.
        if (
            id_ot_abierta is None
            and puede_ver_legionella_operario(operario_sel)
        ):
            zona_operario = st.radio(
                "Zona de trabajo",
                [
                    "📋 Mis órdenes",
                    "💧 Control Legionella"
                ],
                horizontal=True,
                key="zona_operario_legionella"
            )
    
            if zona_operario == "💧 Control Legionella":
                try:
                    from ui.ui_legionella import pantalla_legionella
                    pantalla_legionella()
    
                except Exception as e:
                    st.error(
                        "No se ha podido abrir el módulo de Legionella."
                    )
                    st.exception(e)
    
                return
    
        if id_ot_abierta is not None:
            pantalla_trabajar_ot_operario(
                operario_sel,
                ordenes_activas
            )
            return

        # =================================================
        # ENTRADA SEGÚN QUIÉN ESTÁ VIENDO LA PANTALLA
        #
        # - Operario real: nueva jornada inteligente.
        # - Administración viendo a un operario: listado clásico.
        #
        # Así no se modifica la pantalla de gestión que ya funcionaba.
        # =================================================
        if es_operario():
            pantalla_entrada_operario(
                operario_sel,
                ordenes_activas
            )
        else:
            pantalla_listado_ordenes_operario(
                operario_sel,
                ordenes_activas
            )

        return

    # =====================================================
    # MODO HISTÓRICO
    # No consulta ni renderiza órdenes activas
    # =====================================================
    try:
        historico = obtener_historico()
    except Exception as e:
        st.error(
            "No se ha podido cargar el histórico."
        )
        st.caption(str(e))
        return

    operario_normalizado = normalizar_operario_nombre(
        operario_sel
    )

    historico_operario = [
        h for h in historico
        if len(h) > 10
        and normalizar_operario_nombre(h[10])
        == operario_normalizado
    ]

    if not historico_operario:
        st.info("No hay trabajos finalizados todavía.")
        return

    # Orden más reciente primero
    historico_operario = list(
        reversed(historico_operario)
    )

    # =====================================================
    # PAGINACIÓN DEL HISTÓRICO
    # =====================================================
    historicos_por_pagina = 15
    total_historicos = len(historico_operario)

    total_paginas_hist = max(
        1,
        (
            total_historicos
            + historicos_por_pagina
            - 1
        ) // historicos_por_pagina
    )

    if total_paginas_hist > 1:
        pagina_hist = st.number_input(
            "Página del histórico",
            min_value=1,
            max_value=total_paginas_hist,
            value=1,
            step=1,
            key="pagina_historico_operario"
        )
    else:
        pagina_hist = 1

    inicio_hist = (
        int(pagina_hist) - 1
    ) * historicos_por_pagina

    fin_hist = inicio_hist + historicos_por_pagina

    historico_pagina = historico_operario[
        inicio_hist:fin_hist
    ]

    st.caption(
        f"Mostrando {inicio_hist + 1}–"
        f"{min(fin_hist, total_historicos)} "
        f"de {total_historicos} trabajos finalizados."
    )

    # =====================================================
    # LISTADO DEL HISTÓRICO
    # =====================================================
    for h in historico_pagina:
        try:
            (
                id_hist,
                num_ot_hist,
                desc_hist,
                estado_hist,
                fecha_hist,
                centro_hist,
                edificio_hist,
                espacio_hist,
                area_hist,
                prioridad_hist,
                operario_hist,
                origen_hist,
                solicitante_hist,
                fecha_origen_hist,
                fecha_cierre_hist,
                observaciones_cierre_hist,
                foto_hist,
                *resto
            ) = h

        except Exception:
            continue

        titulo_hist = (
            f"✅ {num_ot_hist or '-'} | "
            f"{centro_hist or '-'} · "
            f"{espacio_hist or '-'}"
        )

        with st.expander(
            titulo_hist,
            expanded=False
        ):
            st.markdown(
                f"### ✅ {num_ot_hist or '-'}"
            )

            st.markdown(
                desc_hist or "Sin descripción."
            )

            st.caption(
                f"🏢 {centro_hist or '-'} · "
                f"{edificio_hist or '-'} · "
                f"{espacio_hist or '-'}"
            )

            st.caption(
                f"📅 Cierre: "
                f"{fecha_cierre_hist or fecha_hist or '-'}"
            )

            if observaciones_cierre_hist:
                st.info(
                    f"📝 {observaciones_cierre_hist}"
                )

            # ---------------------------------------------
            # LAS FOTOS NO SE CONSULTAN AUTOMÁTICAMENTE
            # Solo al pulsar el botón
            # ---------------------------------------------
            key_fotos = (
                f"mostrar_fotos_hist_"
                f"{id_hist}_{num_ot_hist}"
            )

            if not st.session_state.get(
                key_fotos,
                False
            ):
                if st.button(
                    "📷 Ver fotos",
                    key=(
                        f"btn_ver_fotos_hist_"
                        f"{id_hist}_{num_ot_hist}"
                    ),
                    use_container_width=True
                ):
                    st.session_state[key_fotos] = True
                    st.rerun()

            else:
                if st.button(
                    "🙈 Ocultar fotos",
                    key=(
                        f"btn_ocultar_fotos_hist_"
                        f"{id_hist}_{num_ot_hist}"
                    ),
                    use_container_width=True
                ):
                    st.session_state[key_fotos] = False
                    st.rerun()

                try:
                    fotos_db = obtener_fotos_ot(
                        num_ot_hist
                    )

                    if fotos_db:
                        cols_fotos = st.columns(3)

                        for i, (
                            nombre_foto,
                            foto_data
                        ) in enumerate(fotos_db):

                            with cols_fotos[i % 3]:
                                st.image(
                                    bytes(foto_data),
                                    caption=(
                                        nombre_foto
                                        or f"Foto {i + 1}"
                                    ),
                                    use_container_width=True
                                )

                    elif foto_hist:
                        fotos = [
                            ruta.strip()
                            for ruta in str(
                                foto_hist
                            ).split("|")
                            if ruta.strip()
                        ]

                        if fotos:
                            cols_fotos = st.columns(3)

                            for i, ruta_foto in enumerate(
                                fotos
                            ):
                                with cols_fotos[i % 3]:
                                    try:
                                        st.image(
                                            ruta_foto,
                                            caption=(
                                                f"Foto {i + 1}"
                                            ),
                                            use_container_width=True
                                        )

                                    except Exception:
                                        st.caption(
                                            "📷 Foto no disponible."
                                        )

                        else:
                            st.info(
                                "Esta OT no tiene fotos."
                            )

                    else:
                        st.info(
                            "Esta OT no tiene fotos."
                        )

                except Exception as e:
                    st.caption(
                        f"📷 No se pudieron cargar "
                        f"las fotos: {e}"
                    )

# =====================================================
# COMPATIBILIDAD CON APP.PY
# Mantiene el nombre anterior esperado por la aplicación
# =====================================================
def pantalla_operario_prueba(modo="ordenes"):
    return pantalla_operario(modo=modo)
