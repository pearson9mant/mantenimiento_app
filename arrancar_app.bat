@echo off
title Importar incidencias Outlook -> PostgreSQL

cd /d "%~dp0"

set DATABASE_URL=postgresql://mantenimiento_db_x19q_user:QiP9pd8zhPQQMdxZiFT2w1ByZRHpMLNf@dpg-d7ik0pv7f7vs739956s0-a.oregon-postgres.render.com:5432/mantenimiento_db_x19q

echo ==========================================
echo   IMPORTACION OUTLOOK -> OT POSTGRESQL
echo ==========================================
echo.
echo Carpeta actual:
echo %cd%
echo.

py -m core.email_importer_postgres

echo.
echo ==========================================
echo   PROCESO TERMINADO
echo ==========================================
pause