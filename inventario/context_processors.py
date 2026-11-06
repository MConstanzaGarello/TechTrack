from .roles import es_analista, es_bp


def roles(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {"es_analista": False, "es_bp": False}
    return {"es_analista": es_analista(usuario), "es_bp": es_bp(usuario)}
