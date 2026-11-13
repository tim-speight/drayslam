from typing import Any

from fastapi import FastAPI

from dslam.model import DSLAMStatus

app = FastAPI()

_CURRENT_STATUS: DSLAMStatus | None = None


def update_status(status: DSLAMStatus) -> None:

    global _CURRENT_STATUS

    # Single reference assignment: atomic under the GIL, safe to call
    # from the polling thread while uvicorn serves from its own thread.
    _CURRENT_STATUS = status


@app.get("/health")
def health() -> dict[str, Any]:

    return {
        "health": "OK",
        "have_status": _CURRENT_STATUS is not None,
    }


@app.get("/api/status")
def status() -> dict[str, Any]:

    current = _CURRENT_STATUS

    if current is None:

        return {
            "health": "STARTING",
        }

    return current.to_dict()
