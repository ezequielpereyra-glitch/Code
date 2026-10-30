"""ERP de servicio técnico (MVP): clientes, partes de trabajo, firma, facturas y portal de cliente."""
import os
import secrets
import sqlite3
from contextlib import closing
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("SERVICEDESK_DB", ".tmp/servicedesk.db")
STATUSES = ("abierto", "en_curso", "terminado", "facturado")
TRANSITIONS = {"abierto": {"en_curso"}, "en_curso": {"terminado"}, "terminado": set(), "facturado": set()}

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, portal_token TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS work_orders (
  id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL REFERENCES clients(id),
  description TEXT NOT NULL, hours REAL NOT NULL DEFAULT 0, hourly_rate REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'abierto', signature TEXT, invoice_id INTEGER);
CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY, number TEXT UNIQUE NOT NULL, client_id INTEGER NOT NULL REFERENCES clients(id),
  issued_on TEXT NOT NULL, subtotal REAL NOT NULL, tax_rate REAL NOT NULL, total REAL NOT NULL);
"""


def db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    with closing(db()) as conn:
        conn.executescript(SCHEMA)


class ClientIn(BaseModel):
    name: str
    email: str | None = None


class WorkOrderIn(BaseModel):
    client_id: int
    description: str
    hours: float = 0
    hourly_rate: float = 0


class StatusIn(BaseModel):
    status: str


class SignatureIn(BaseModel):
    signature: str  # PNG en base64 (data URL)


app = FastAPI(title="ServiceDesk")
init_db()


@app.post("/clients", status_code=201)
def create_client(c: ClientIn):
    with closing(db()) as conn, conn:
        cur = conn.execute("INSERT INTO clients(name,email,portal_token) VALUES(?,?,?)",
                           (c.name, c.email, secrets.token_urlsafe(16)))
        return dict(conn.execute("SELECT * FROM clients WHERE id=?", (cur.lastrowid,)).fetchone())


@app.post("/work-orders", status_code=201)
def create_work_order(w: WorkOrderIn):
    with closing(db()) as conn, conn:
        if not conn.execute("SELECT 1 FROM clients WHERE id=?", (w.client_id,)).fetchone():
            raise HTTPException(404, "Cliente no existe")
        cur = conn.execute("INSERT INTO work_orders(client_id,description,hours,hourly_rate) VALUES(?,?,?,?)",
                           (w.client_id, w.description, w.hours, w.hourly_rate))
        return dict(conn.execute("SELECT * FROM work_orders WHERE id=?", (cur.lastrowid,)).fetchone())


def _order(conn, oid):
    row = conn.execute("SELECT * FROM work_orders WHERE id=?", (oid,)).fetchone()
    if not row:
        raise HTTPException(404, "Parte no existe")
    return row


@app.post("/work-orders/{oid}/status")
def set_status(oid: int, s: StatusIn):
    with closing(db()) as conn, conn:
        row = _order(conn, oid)
        if s.status not in TRANSITIONS.get(row["status"], set()):
            raise HTTPException(409, f"Transición no permitida: {row['status']} -> {s.status}")
        if s.status == "terminado" and not row["signature"]:
            raise HTTPException(409, "Falta la firma del cliente")
        conn.execute("UPDATE work_orders SET status=? WHERE id=?", (s.status, oid))
        return dict(_order(conn, oid))


@app.post("/work-orders/{oid}/signature")
def sign(oid: int, s: SignatureIn):
    with closing(db()) as conn, conn:
        _order(conn, oid)
        conn.execute("UPDATE work_orders SET signature=? WHERE id=?", (s.signature, oid))
        return dict(_order(conn, oid))


@app.post("/work-orders/{oid}/invoice", status_code=201)
def invoice(oid: int, tax_rate: float = 0.21):
    with closing(db()) as conn, conn:
        row = _order(conn, oid)
        if row["status"] != "terminado":
            raise HTTPException(409, "Solo se facturan partes terminados")
        subtotal = round(row["hours"] * row["hourly_rate"], 2)
        total = round(subtotal * (1 + tax_rate), 2)
        n = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] + 1
        number = f"{date.today().year}-{n:05d}"
        cur = conn.execute("INSERT INTO invoices(number,client_id,issued_on,subtotal,tax_rate,total) VALUES(?,?,?,?,?,?)",
                           (number, row["client_id"], date.today().isoformat(), subtotal, tax_rate, total))
        conn.execute("UPDATE work_orders SET status='facturado', invoice_id=? WHERE id=?", (cur.lastrowid, oid))
        return dict(conn.execute("SELECT * FROM invoices WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/invoices/{iid}/print", response_class=HTMLResponse)
def invoice_print(iid: int):
    with closing(db()) as conn:
        inv = conn.execute("SELECT i.*, c.name FROM invoices i JOIN clients c ON c.id=i.client_id WHERE i.id=?",
                           (iid,)).fetchone()
    if not inv:
        raise HTTPException(404, "Factura no existe")
    from html import escape
    return (f"<h1>Factura {escape(inv['number'])}</h1><p>Cliente: {escape(inv['name'])}</p>"
            f"<p>Fecha: {inv['issued_on']}</p><p>Base: {inv['subtotal']:.2f} €</p>"
            f"<p>IVA {inv['tax_rate']*100:.0f}%</p><p><b>Total: {inv['total']:.2f} €</b></p>")


@app.get("/portal/{token}")
def portal(token: str):
    with closing(db()) as conn:
        client = conn.execute("SELECT id,name FROM clients WHERE portal_token=?", (token,)).fetchone()
        if not client:
            raise HTTPException(404, "Portal no encontrado")
        orders = conn.execute("SELECT id,description,hours,status,invoice_id FROM work_orders WHERE client_id=?",
                              (client["id"],)).fetchall()
    return {"client": client["name"], "work_orders": [dict(o) for o in orders]}
