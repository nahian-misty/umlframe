from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import codegen, image

app = FastAPI(title="UMLFrame API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(codegen.router)
app.include_router(image.router)
