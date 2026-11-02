"""Exfiltration Monitor — standalone webhook, separate process from the RAG app.

Exfil contract (CLAUDE.md): GET/POST /collect?key=<value>&doc_id=<id> logs
{timestamp, doc_id, payload_variant, raw_query_string} to a JSON file the
Evaluation Matrix reads. Binds to loopback only (rules of engagement).

Open contract gap (flagged in CLAUDE.md): the contract query string carries no
payload_variant field, so it is read from an optional `variant` param when the
harness supplies one, else null. Resolve with the owner before Day 3 wiring.
"""

import datetime
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response

from ..config import get_settings

app = FastAPI(title="Exfil Monitor (local research only)")

# 1x1 transparent GIF, so a markdown-image callback fetch resolves naturally.
_PIXEL = bytes.fromhex(
    "47494638396101000100800000000000ffffff21f90401000000002c"
    "00000000010001000002024401003b"
)


@app.api_route("/collect", methods=["GET", "POST"])
async def collect(request: Request) -> Response:
    s = get_settings()
    params = request.query_params
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "doc_id": params.get("doc_id"),
        "payload_variant": params.get("payload_variant") or params.get("variant"),
        "raw_query_string": request.url.query,
    }
    log = Path(s.exfil_log)
    data = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    data.append(entry)
    log.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return Response(content=_PIXEL, media_type="image/gif")


def main() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run(app, host=s.exfil_host, port=s.exfil_port)


if __name__ == "__main__":
    main()
