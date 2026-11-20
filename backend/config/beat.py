"""Construcción del horario de Celery Beat para la cartelera.

Vive aparte de settings/base.py para poder probarse sin Django ni Redis.
"""
try:
    from celery.schedules import crontab
except ImportError:
    def crontab(**kwargs):
        return kwargs


# Regla de la fase: nunca más de dos ejecuciones al día por cine.
MAX_EJECUCIONES_DIARIAS = 2


def parsear_pares(valores):
    """Convierte ["cinepolis:valledupar", ...] en [("cinepolis", "valledupar"), ...]."""
    pares = []
    for valor in valores:
        cine, separador, ciudad = valor.partition(":")
        cine, ciudad = cine.strip(), ciudad.strip().lower()
        if not separador or not cine or not ciudad:
            raise ValueError(
                f"Par cine-ciudad inválido: {valor!r}. Usa el formato cine:ciudad."
            )
        pares.append((cine, ciudad))
    return pares


def construir_beat_schedule(pares, horas=(6, 18), espaciado_minutos=10):
    """Arma CELERY_BEAT_SCHEDULE con un scrape por cine en cada hora indicada.

    El cine n-ésimo arranca n * espaciado_minutos después de la hora base,
    para que las solicitudes a los sitios queden espaciadas.
    Además programa dos tareas que solo tocan la base de datos: la limpieza de
    funciones vencidas (cada hora) y la de tokens vencidos (una vez por semana).
    """
    horas = tuple(horas)
    if not 1 <= len(horas) <= MAX_EJECUCIONES_DIARIAS or len(set(horas)) != len(horas):
        raise ValueError(
            f"Debe haber entre 1 y {MAX_EJECUCIONES_DIARIAS} horas distintas por día."
        )
    if espaciado_minutos < 1:
        raise ValueError("El espaciado entre cines debe ser de al menos 1 minuto.")

    schedule = {}
    for hora in horas:
        for indice, (cine, ciudad) in enumerate(pares):
            total_minutos = hora * 60 + indice * espaciado_minutos
            hora_inicio = (total_minutos // 60) % 24
            minuto_inicio = total_minutos % 60
            nombre = f"cartelera-{cine}-{ciudad}-{hora_inicio:02d}{minuto_inicio:02d}"
            schedule[nombre] = {
                "task": "cines.tasks.scrape_cartelera_task",
                "schedule": crontab(minute=minuto_inicio, hour=hora_inicio),
                "args": (cine, ciudad),
            }

    schedule["limpiar-cartelera-vencida"] = {
        "task": "cines.tasks.limpiar_cartelera_vencida",
        "schedule": crontab(minute=30),  # cada hora, en el minuto 30
    }
    schedule["limpiar-tokens-vencidos"] = {
        "task": "usuarios.tasks.limpiar_tokens_vencidos",
        # Domingos a las 3:00 a. m. (hora de Bogotá): hora de poco uso, lejos de los
        # scrapes de las 6:00 y las 18:00.
        "schedule": crontab(minute=0, hour=3, day_of_week="sunday"),
    }
    return schedule