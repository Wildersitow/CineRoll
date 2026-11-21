from celery import shared_task
from django.core.management import call_command


@shared_task(soft_time_limit=60, time_limit=90)
def limpiar_tokens_vencidos():
    """Borra los refresh tokens vencidos (y su lista negra) de SimpleJWT.

    Con rotación y lista negra activas, cada refresh crea filas nuevas en
    OutstandingToken y BlacklistedToken; sin esta limpieza las tablas crecen
    sin límite. Solo toca tokens que ya expiraron, así que no cierra sesiones vigentes.
    """
    call_command("flushexpiredtokens")
    return {"limpieza": "tokens_vencidos", "ok": True}
