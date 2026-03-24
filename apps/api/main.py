from fastapi import FastAPI

from apps.api.routes import router


app = FastAPI(
    title="SKDO API",
    version="0.1.0",
    description=(
        "API-first system for consolidated structural inspection and monitoring data, "
        "prepared for hidden-state identification."
    ),
)
app.include_router(router)

