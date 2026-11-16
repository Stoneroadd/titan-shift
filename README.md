# Titan Shift

MVP full stack para registrar turnos mineros y consultar KPI de producción. Es una demo local con datos ingresados por el usuario; no está conectada a sistemas de faena.

## Ejecutar

Requiere Python 3.10 o superior. No usa dependencias externas.

```powershell
python app.py
```

Abre `http://127.0.0.1:8000`. Los datos se guardan en `titan_shift.sqlite3`. Para cambiar el puerto o la ubicación de la base de datos, usa `PORT` y `TITAN_DB_PATH`.

## Funciones

- Registrar turno Día/Noche con fecha, plan, producción y minutos de detención.
- Ver historial persistido y eliminar registros.
- Calcular cumplimiento = producción real / plan × 100.
- Calcular disponibilidad = (minutos programados − detención) / minutos programados × 100.
- Calcular tasa = producción real / horas operativas. Si no hubo tiempo operativo, la tasa no se calcula.
- Resumen agregado ponderado por toneladas planificadas y minutos programados.
- API JSON: `GET /api/health`, `GET /api/shifts`, `POST /api/shifts`, `DELETE /api/shifts/{id}`.

Los KPI describen únicamente los valores registrados; no prueban causas, rendimiento de equipos ni resultados de una operación real.

## Verificar

```powershell
python -m unittest discover -s tests -v
```

## Límites del MVP

No incluye autenticación, usuarios múltiples, conexión a telemetría ni cálculos de disponibilidad por equipo. Está diseñado para una demo en un equipo local.

## Licencia

MIT. Consulta `LICENSE`.
