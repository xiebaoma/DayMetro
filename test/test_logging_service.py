from __future__ import annotations

import importlib
import logging
from pathlib import Path

from fastapi.testclient import TestClient


def test_backend_writes_unified_log_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DAYMETRO_DB_PATH", str(tmp_path / "test_save.db"))
    monkeypatch.setenv("DAYMETRO_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data"))
    monkeypatch.setenv("DAYMETRO_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DAYMETRO_LOG_FILE", "daymetro-test.log")

    import server.logging_service as logging_service

    logging_service._CONFIGURED = False
    import server.main as main

    importlib.reload(logging_service)
    main = importlib.reload(main)

    with TestClient(main.app) as client:
        response = client.get("/health")

    for handler in logging.getLogger().handlers:
        handler.flush()

    log_path = tmp_path / "logs" / "daymetro-test.log"
    assert response.status_code == 200
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "server startup complete" in log_text
    assert "request method=GET path=/health status=200" in log_text
