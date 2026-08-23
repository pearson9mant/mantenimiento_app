import streamlit as st

from ui.ui_inteligencia_preventiva import (
    pantalla_inteligencia_preventiva,
)


def _estilo_inteligencia_mantenimiento():
    st.markdown(
        """
        <style>
        .im-cabecera {
            background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
            color: white;
            border-radius: 22px;
            padding: 20px 22px;
            margin-bottom: 14px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.14);
        }

        .im-titulo {
            font-size: 27px;
            font-weight: 950;
            line-height: 1.1;
            margin-bottom: 6px;
        }

        .im-subtitulo {
            font-size: 14px;
            font-weight: 650;
            opacity: .92;
            line-height: 1.4;
        }

        .im-nota {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 11px 13px;
            color: #475569;
            font-size: 13px;
            line-height: 1.45;
            margin-bottom: 10px;
        }

        @media(max-width:760px){
            .im-cabecera {
                padding: 15px 14px;
                border-radius: 16px;
            }

            .im-titulo {
                font-size: 20px;
            }

            .im-subtitulo {
                font-size: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _mostrar_proximamente(titulo, descripcion):
    """
    Pestaña ligera.
    No consulta base de datos ni ejecuta análisis.
    """
    st.markdown(f"### {titulo}")
    st.info(descripcion)
    st.caption("Esta sección todavía no ejecuta ningún cálculo.")


def pantalla_inteligencia_mantenimiento():
    """
    Centro de inteligencia exclusivo de Administración.

    Filosofía:
    - entrar en esta pantalla NO lanza análisis pesados;
    - cada motor trabaja únicamente cuando el usuario pulsa Analizar;
    - se reutilizan módulos existentes;
    - no modifica órdenes, preventivos, Legionella ni Corazón.
    """

    _estilo_inteligencia_mantenimiento()

    st.markdown(
        """
        <div class="im-cabecera">
            <div class="im-titulo">🧠 Inteligencia de mantenimiento</div>
            <div class="im-subtitulo">
                Análisis técnico para decidir dónde actuar, qué prevenir
                y qué merece seguimiento.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="im-nota">
            La inteligencia trabaja bajo demanda. Entrar en esta pantalla
            no analiza históricos ni fotografías automáticamente.
        </div>
        """,
        unsafe_allow_html=True,
    )

    (
        tab_incidencias_preventivo,
        tab_salud_edificios,
        tab_reincidencias,
        tab_reparaciones,
        tab_evolucion,
    ) = st.tabs(
        [
            "⚖️ Incidencias - Preventivo",
            "🏫 Salud edificios",
            "🔁 Reincidencias",
            "🔧 Calidad reparaciones",
            "📈 Evolución",
        ]
    )

    with tab_incidencias_preventivo:
        pantalla_inteligencia_preventiva()

    with tab_salud_edificios:
        _mostrar_proximamente(
            "🏫 Salud de edificios",
            (
                "Comparará edificios según incidencias, preventivos, "
                "reincidencias, antigüedad y evolución."
            ),
        )

    with tab_reincidencias:
        _mostrar_proximamente(
            "🔁 Reincidencias",
            (
                "Detectará espacios y elementos donde se repiten averías "
                "y diferenciará patrón real de coincidencia de área."
            ),
        )

    with tab_reparaciones:
        _mostrar_proximamente(
            "🔧 Calidad de reparaciones",
            (
                "Revisará solución registrada, histórico y, más adelante, "
                "fotografías para valorar si existe una alternativa técnica "
                "más duradera."
            ),
        )

    with tab_evolucion:
        _mostrar_proximamente(
            "📈 Evolución",
            (
                "Mostrará si el mantenimiento mejora o empeora con el tiempo "
                "y si los preventivos están reduciendo las incidencias."
            ),
        )
