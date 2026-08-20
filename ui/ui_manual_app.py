import streamlit as st


def pantalla_manual_app():
    st.subheader("📘 Manual de funcionamiento · Mantenimiento PRO")

    st.info(
        "Guía de uso del Sistema Integral de Mantenimiento. "
        "El objetivo de la aplicación es registrar, priorizar, ejecutar "
        "y conservar la trazabilidad de todas las actuaciones de mantenimiento."
    )

    st.caption(
        "Principio general: registrar bien, trabajar una actuación cada vez "
        "y conservar siempre la trazabilidad."
    )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "❤️ Trabajo diario",
            "💧 Legionella",
            "🛠️ Órdenes",
            "📅 Preventivo",
            "📦 Inventario",
            "📱 QR",
            "🧭 Gerencia",
            "📄 Histórico e informes",
        ]
    )

    # =====================================================
    # ❤️ TRABAJO DIARIO
    # =====================================================
    with tab1:
        st.markdown("## ❤️ Trabajo diario del operario")

        st.write(
            """
            La pantalla principal del operario está diseñada para indicar
            **qué trabajo merece atención primero**.

            El sistema no sustituye el criterio técnico del operario.
            Lo ayuda a ordenar el trabajo y a reaccionar cuando aparece
            una incidencia más importante durante la jornada.
            """
        )

        st.markdown("### ❤️ Mi misión")

        st.write(
            """
            El **Corazón del sistema** analiza las órdenes activas
            y propone una misión.

            Entre otros factores tiene en cuenta:

            - prioridad de la orden;
            - incidencias urgentes;
            - agua, electricidad y climatización;
            - antigüedad;
            - estado de la orden;
            - órdenes bloqueadas;
            - concentración de trabajo;
            - nuevas incidencias que entren durante la jornada.
            """
        )

        st.info(
            "Una incidencia importante que entre durante la jornada puede "
            "cambiar la misión recomendada."
        )

        st.markdown("### 🔄 Actualización automática")

        st.write(
            """
            La pantalla **Colegio Vivo** se actualiza periódicamente.

            Esto permite que una nueva incidencia o QR pueda incorporarse
            al trabajo diario sin tener que cerrar y volver a abrir la aplicación.
            """
        )

        st.markdown("### ▶️ Empezar una OT")

        st.write(
            """
            Al comenzar una orden:

            1. Abre la OT propuesta.
            2. Comprueba ubicación y descripción.
            3. Pulsa **En curso**.
            4. Realiza el trabajo.
            5. Añade observaciones si son necesarias.
            6. Registra material si se ha utilizado.
            7. Añade fotografías cuando aporten evidencia.
            8. Finaliza la OT.
            """
        )

        st.markdown("### ⏸️ Una sola misión en curso")

        st.write(
            """
            El sistema está preparado para trabajar con **una sola OT principal
            en curso por operario**.

            Si se inicia una actuación más importante, la anterior puede quedar
            en pausa para poder continuarla posteriormente.
            """
        )

        st.warning(
            "No finalizar una OT si el trabajo realmente no está terminado."
        )

    # =====================================================
    # 💧 LEGIONELLA
    # =====================================================
    with tab2:
        st.markdown("## 💧 Legionella")

        st.error(
            "Legionella es uno de los módulos con mayor necesidad de "
            "trazabilidad. Punto, tarea, fecha, resultado y operario deben "
            "corresponder siempre con la actuación realmente realizada."
        )

        st.markdown("### 1️⃣ Puntos de control")

        st.write(
            """
            En **Legionella → Puntos** se mantiene el catálogo físico
            de la instalación.

            Cada punto identifica un elemento real del colegio.

            Ejemplos:

            - acumuladores ACS;
            - retorno ACS;
            - depósitos solares;
            - duchas;
            - grifos;
            - fuentes;
            - puntos de poco uso;
            - puntos AFS;
            - puntos terminales ACS.
            """
        )

        st.info(
            "Un punto físico puede tener varias tareas diferentes. "
            "Por ejemplo, un acumulador puede tener Control sala ACS, "
            "Purga, Choque térmico, Revisión o Puesta en servicio."
        )

        st.markdown("### 2️⃣ Planificación")

        st.write(
            """
            En **Legionella → Planificación** se define cuándo debe realizarse
            cada tarea.

            Cada planificación dispone de:

            - centro;
            - edificio;
            - planta;
            - punto;
            - tarea;
            - frecuencia;
            - próxima fecha;
            - operario;
            - generación automática de OT;
            - estado activo/inactivo.
            """
        )

        st.warning(
            "La fecha de planificación es el calendario maestro. "
            "No modificar fechas sin conocer el motivo."
        )

        st.markdown("### 3️⃣ Generación de OT")

        st.write(
            """
            Cuando una tarea planificada llega a su fecha y tiene activada
            la opción **Generar OT cuando toque**, el sistema puede crear
            automáticamente la orden correspondiente.

            La OT queda vinculada a:

            - el punto exacto de Legionella;
            - la planificación/tarea exacta que la ha generado.
            """
        )

        st.success(
            "Esto evita que dos controles diferentes del mismo punto "
            "se puedan confundir."
        )

        st.markdown("### 4️⃣ Ejecutar el control")

        st.write(
            """
            Al abrir una OT de Legionella se presenta automáticamente
            el procedimiento correspondiente.

            Ejemplos:

            **Control sala ACS**
            - temperatura acumulador;
            - temperatura impulsión;
            - temperatura retorno.

            **Control AFS**
            - temperatura;
            - cloro residual;
            - purga;
            - limpieza/desinfección de aireador;
            - revisión visual.

            **Purga**
            - confirmación de purga;
            - agua transparente;
            - temperatura o cloro según instalación.

            **Choque térmico**
            - aviso;
            - control de instalación;
            - temperatura;
            - tiempo;
            - terminales purgados.
            """
        )

        st.markdown("### 5️⃣ Guardar antes de finalizar")

        st.write(
            """
            Una OT de Legionella no debe finalizarse sin guardar primero
            el control correspondiente.

            El registro conserva:

            - fecha;
            - centro;
            - edificio;
            - planta;
            - punto;
            - tarea;
            - tipo de control;
            - valores;
            - unidad;
            - estado;
            - resultado;
            - operario;
            - observaciones.
            """
        )

        st.markdown("### 6️⃣ Resultado")

        st.write(
            """
            Según los valores registrados, el sistema puede clasificar
            el control como:

            - **OK**
            - **INCIDENCIA**
            - **RIESGO**

            Los resultados fuera de rango deben quedar registrados
            y gestionarse mediante la actuación correspondiente.
            """
        )

        st.markdown("### 7️⃣ Histórico")

        st.write(
            """
            El histórico permite comprobar la evolución de cada punto.

            Un resultado antiguo no debe desaparecer al realizar
            un control nuevo.

            Ejemplo:

            - 19/08 → RIESGO
            - 20/08 → OK

            Ambos deben mantenerse para conservar la trazabilidad.
            """
        )

        st.markdown("### 🔐 Regla de seguridad Legionella")

        st.error(
            "Antes de validar cualquier cambio comprobar siempre: "
            "FECHA → TAREA → PUNTO → OT → REGISTRO → SIGUIENTE FECHA."
        )

    # =====================================================
    # 🛠️ ÓRDENES
    # =====================================================
    with tab3:
        st.markdown("## 🛠️ Órdenes de trabajo")

        st.markdown("### Orígenes")

        st.write(
            """
            Las órdenes pueden proceder de diferentes módulos:

            - QR / APP;
            - profesores;
            - administración;
            - preventivo;
            - Legionella;
            - inventario;
            - empresa externa;
            - Plan Verano.
            """
        )

        st.markdown("### Estados")

        st.write(
            """
            Los estados principales son:

            - **Abierta** → pendiente de iniciar.
            - **En curso** → se está trabajando.
            - **En pausa** → trabajo detenido temporalmente.
            - **Pendiente material** → no se puede continuar por falta de material.
            - **Pendiente proveedor** → depende de una empresa externa.
            - **Pendiente presupuesto** → pendiente de aprobación o valoración.
            - **Avisado** → proveedor informado.
            - **Finalizada / Cerrado** → trabajo terminado.
            """
        )

        st.markdown("### Prioridad")

        st.write(
            """
            Las prioridades habituales son:

            - 🚨 Urgente
            - 🔴 Alta
            - 🟠 Media
            - 🟢 Baja

            La prioridad no depende únicamente del texto introducido.
            El Corazón puede utilizar además criterios operativos.
            """
        )

        st.markdown("### Fotografías")

        st.write(
            """
            Las fotografías se cargan únicamente cuando se solicitan,
            para mantener ligera la aplicación.

            En el cierre pueden añadirse fotografías del trabajo realizado.

            Límites actuales:

            - máximo 5 fotografías;
            - máximo 5 MB por fotografía.
            """
        )

        st.markdown("### Material")

        st.write(
            """
            Al finalizar una OT se puede registrar material utilizado.

            Si se confirma una salida de inventario:

            - se descuenta el stock;
            - queda vinculada a la OT;
            - queda registrado el operario.
            """
        )

    # =====================================================
    # 📅 PREVENTIVO
    # =====================================================
    with tab4:
        st.markdown("## 📅 Mantenimiento preventivo")

        st.write(
            """
            El preventivo permite realizar revisiones periódicas
            antes de que aparezca una avería.
            """
        )

        st.markdown("### Flujo")

        st.write(
            """
            1. Crear una tarea preventiva.
            2. Asignar centro, edificio, espacio y operario.
            3. Definir frecuencia o fecha.
            4. Generar la OT cuando corresponda.
            5. Abrir la OT.
            6. Completar el checklist.
            7. Registrar observaciones.
            8. Crear correctivas si se detectan averías.
            9. Finalizar.
            10. Conservar el resultado en histórico.
            """
        )

        st.markdown("### Checklist técnico")

        st.write(
            """
            Cada punto puede clasificarse como:

            - ✅ Correcto
            - 🛠️ Ajustado
            - 🟡 Revisar
            - 🔴 Avería

            Los estados Ajustado, Revisar y Avería requieren
            una explicación técnica.
            """
        )

        st.markdown("### Correctivas")

        st.write(
            """
            Si durante un preventivo aparece una avería,
            puede generarse una OT correctiva independiente.

            La correctiva conserva la referencia de la preventiva
            que permitió detectar el defecto.
            """
        )

    # =====================================================
    # 📦 INVENTARIO
    # =====================================================
    with tab5:
        st.markdown("## 📦 Inventario")

        st.write(
            """
            El inventario permite conocer qué material existe,
            dónde está y cuánto queda disponible.
            """
        )

        st.markdown("### Información de cada material")

        st.write(
            """
            Puede incluir:

            - código;
            - nombre;
            - categoría;
            - centro;
            - edificio;
            - ubicación;
            - stock;
            - stock mínimo;
            - unidad;
            - proveedor;
            - precio;
            - fotografía.
            """
        )

        st.markdown("### Movimientos")

        st.write(
            """
            Se registran:

            - entradas;
            - salidas;
            - ajustes;
            - consumos asociados a OT.
            """
        )

        st.markdown("### Pedidos de material")

        st.write(
            """
            Flujo habitual:

            **Operario → solicita material → preparación → entrega**

            Estados habituales:

            - Pendiente
            - Preparado
            - Entregado
            - Sin stock
            - Cancelado
            """
        )

        st.warning(
            "No realizar ajustes manuales de stock para ocultar diferencias. "
            "Debe mantenerse el histórico real de movimientos."
        )

    # =====================================================
    # 📱 QR
    # =====================================================
    with tab6:
        st.markdown("## 📱 Incidencias mediante QR")

        st.write(
            """
            Los QR permiten comunicar incidencias directamente
            desde el espacio donde se encuentra la avería.

            No es necesario instalar ninguna aplicación.
            """
        )

        st.markdown("### Flujo")

        st.write(
            """
            1. Escanear el QR con la cámara del móvil.
            2. Abrir el formulario.
            3. Describir el problema.
            4. Añadir fotografías si son necesarias.
            5. Enviar.
            6. La app crea una OT.
            7. El Corazón la incorpora al trabajo diario.
            """
        )

        st.markdown("### Clasificación automática")

        st.write(
            """
            La aplicación puede detectar determinadas incidencias
            relevantes a partir de la descripción.

            Ejemplos:

            - pierde agua;
            - fuga;
            - problemas eléctricos;
            - climatización;
            - situaciones urgentes.
            """
        )

        st.info(
            "Una incidencia importante puede aparecer automáticamente "
            "como nueva misión del operario."
        )

        st.markdown("### QR habilitados")

        st.write(
            """
            Desde Configuración se decide qué espacios tienen QR activo.

            Esto permite generar únicamente las placas que realmente
            se desean colocar.
            """
        )

    # =====================================================
    # 🧭 GERENCIA
    # =====================================================
    with tab7:
        st.markdown("## 🧭 Gerencia · Visión Global")

        st.write(
            """
            Gerencia está pensada para interpretar el mantenimiento,
            no para sustituir la pantalla de trabajo del operario.
            """
        )

        st.markdown("### Colegio Vivo")

        st.write(
            """
            Permite visualizar el estado del colegio por:

            - centro;
            - edificio;
            - planta;
            - espacio.

            Los colores ayudan a localizar zonas con actuaciones activas.
            """
        )

        st.markdown("### Diagnóstico de Gerencia")

        st.write(
            """
            El diagnóstico combina distintas señales:

            - carga activa;
            - actuaciones críticas;
            - órdenes bloqueadas;
            - reincidencias;
            - evolución mensual;
            - resolución;
            - preventivo.
            """
        )

        st.markdown("### Reincidencias")

        st.write(
            """
            Se considera reincidente un espacio que acumula varias
            incidencias dentro del periodo de análisis.

            El objetivo no es únicamente contar averías,
            sino detectar lugares que necesitan una revisión de causa raíz.
            """
        )

        st.markdown("### Importante")

        st.info(
            "Gerencia interpreta tendencias. "
            "La prioridad diaria del operario continúa correspondiendo "
            "al ❤️ Corazón."
        )

    # =====================================================
    # 📄 HISTÓRICO E INFORMES
    # =====================================================
    with tab8:
        st.markdown("## 📄 Histórico e informes")

        st.markdown("### Histórico de OT")

        st.write(
            """
            Cuando una OT se finaliza pasa al histórico.

            Se conserva, entre otros datos:

            - número de OT;
            - descripción;
            - ubicación;
            - área;
            - prioridad;
            - operario;
            - origen;
            - fechas;
            - observaciones;
            - material;
            - fotos cuando corresponda;
            - vinculación con su origen.
            """
        )

        st.info(
            "Los números de OT no se reutilizan aunque una orden de prueba "
            "sea eliminada."
        )

        st.markdown("### Histórico Legionella")

        st.write(
            """
            Permite consultar controles realizados y descargar datos.

            Para inspección debe poder demostrarse:

            - qué se controló;
            - dónde;
            - cuándo;
            - quién lo realizó;
            - qué valores se obtuvieron;
            - cuál fue el resultado.
            """
        )

        st.markdown("### Informes disponibles")

        st.write(
            """
            Según el módulo pueden existir:

            - históricos CSV;
            - controles Legionella;
            - informes de laboratorio;
            - documentos PDF;
            - informes externos;
            - datos de seguimiento;
            - evidencias fotográficas.
            """
        )

        st.markdown("### 🧾 Antes de una inspección")

        st.warning(
            "Comprobar siempre puntos, planificación, registros, "
            "resultados anómalos, actuaciones correctivas e informes externos."
        )

    # =====================================================
    # PIE DEL MANUAL
    # =====================================================
    st.markdown("---")

    st.markdown("### 🧠 Filosofía del sistema")

    st.success(
        "COLEGIO VIVO muestra lo que ocurre · "
        "el ❤️ CORAZÓN ordena el trabajo · "
        "el OPERARIO ejecuta · "
        "el HISTÓRICO conserva la trazabilidad."
    )

    st.caption(
        "Sistema Integral de Mantenimiento · Loreto Abat Oliba"
    )
