"""
Router intermediario para operaciones con Apify
Administra y centraliza todos los endpoints del paquete apify/
Organizacion: Cada red social tiene su propio paquete con actor y routes
"""
from fastapi import APIRouter

# crea el roter principal
router = APIRouter()

# Importar router general (listado de actores, datasets, runs)
try:
    from .general import router as general_router
    router.include_router(
        general_router,
        # agrupa las rutas bajo /general
        prefix="/general"
    )
except Exception as e:
    import traceback

    print("WARNING: General routes not available:")
    print(traceback.format_exc())

# Importar routers del paquete apify con manejo de errores
try:
    from .tiktok import router as tiktok_router
    router.include_router(
        tiktok_router,
        # agrupa las rutas bajo /tiktok
        prefix="/tiktok"
    )
# si hay un error al importar, muestra una advertencia
except Exception as e:
    import traceback

    print("WARNING: TikTok routes not available:")
    print(traceback.format_exc())

try:
    from .facebook import router as facebook_router
    router.include_router(
        facebook_router,
        # agrupa las rutas bajo /facebook
        prefix="/facebook"
    )
# si hay un error al importar, muestra una advertencia
except Exception as e:
    import traceback

    print("WARNING: Facebook routes not available:")
    print(traceback.format_exc())

try:
    from .instagram import router as instagram_router
    router.include_router(
        instagram_router,
        # agrupa las rutas bajo /instagram
        prefix="/instagram"
    )
# si hay un error al importar, muestra una advertencia
except Exception as e:
    import traceback

    print("WARNING: Instagram routes not available:")
    print(traceback.format_exc())
