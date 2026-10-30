import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("SERVICEDESK_DB", str(tmp_path / "t.db"))
    import execution.servicedesk.app as app
    importlib.reload(app)
    return TestClient(app.app)


def test_full_flow(api):
    c = api.post("/clients", json={"name": "Acme"}).json()
    w = api.post("/work-orders", json={"client_id": c["id"], "description": "Reparar", "hours": 2, "hourly_rate": 50}).json()
    assert api.post(f"/work-orders/{w['id']}/status", json={"status": "terminado"}).status_code == 409
    assert api.post(f"/work-orders/{w['id']}/status", json={"status": "en_curso"}).status_code == 200
    assert api.post(f"/work-orders/{w['id']}/status", json={"status": "terminado"}).status_code == 409  # sin firma
    api.post(f"/work-orders/{w['id']}/signature", json={"signature": "data:image/png;base64,AAAA"})
    assert api.post(f"/work-orders/{w['id']}/status", json={"status": "terminado"}).status_code == 200
    inv = api.post(f"/work-orders/{w['id']}/invoice").json()
    assert inv["subtotal"] == 100 and inv["total"] == 121
    assert "Acme" in api.get(f"/invoices/{inv['id']}/print").text
    p = api.get(f"/portal/{c['portal_token']}").json()
    assert p["work_orders"][0]["status"] == "facturado"
    assert api.get("/portal/nope").status_code == 404


def test_web_ui(api):
    assert api.post("/ui/clients", data={"name": "Beta"}, follow_redirects=False).status_code == 303
    r = api.post("/ui/work-orders", data={"client_id": 1, "description": "Cambio pantalla", "hours": 1, "hourly_rate": 40},
                 follow_redirects=False)
    assert r.headers["location"] == "/work-orders/1"
    assert "Cambio pantalla" in api.get("/").text
    r = api.post("/ui/work-orders/1/status", data={"status": "terminado"})
    assert "Transición no permitida" in r.text
    api.post("/ui/work-orders/1/status", data={"status": "en_curso"})
    api.post("/ui/work-orders/1/signature", data={"signature": "data:image/png;base64,AAAA"})
    api.post("/ui/work-orders/1/status", data={"status": "terminado"})
    assert "Generar factura" in api.get("/work-orders/1").text
    assert "Ver factura" in api.post("/ui/work-orders/1/invoice").text
    assert api.get("/work-orders/99").status_code == 404
