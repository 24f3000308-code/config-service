import os
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

DEFAULTS: Dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

YAML_LAYER: Dict[str, Any] = {
    "port": 8154,
    "workers": 7,
    "log_level": "error",
}

DOTENV_RAW: Dict[str, str] = {
    "APP_PORT": "8838",
    "NUM_WORKERS": "16",
    "APP_LOG_LEVEL": "error",
}

ALIASES = {"NUM_WORKERS": "workers"}


def _key_from_env_name(name: str) -> str:
    if name in ALIASES:
        return ALIASES[name]
    if name.startswith("APP_"):
        return name[len("APP_"):].lower()
    return name.lower()


def _dotenv_layer() -> Dict[str, str]:
    return {_key_from_env_name(k): v for k, v in DOTENV_RAW.items()}


TRUE_STRINGS = {"true", "1", "yes", "on"}


def coerce(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUE_STRINGS
    return str(value)


def _os_env_layer() -> Dict[str, str]:
    layer = {}
    for name, value in os.environ.items():
        if name.startswith("APP_"):
            layer[_key_from_env_name(name)] = value
    return layer


def _cli_overrides(request: Request) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for item in request.query_params.getlist("set"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        overrides[key.strip()] = value
    return overrides


@app.get("/effective-config")
async def effective_config(request: Request):
    merged: Dict[str, Any] = dict(DEFAULTS)
    for layer in (YAML_LAYER, _dotenv_layer(), _os_env_layer(), _cli_overrides(request)):
        for key, value in layer.items():
            merged[key] = coerce(key, value)

    result = {k: coerce(k, v) for k, v in merged.items()}
    if "api_key" in result:
        result["api_key"] = "****"

    known_keys = ("port", "workers", "debug", "log_level", "api_key")
    return {k: result[k] for k in known_keys if k in result}


@app.get("/")
async def root():
    return {"status": "ok"}
