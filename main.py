import sqlite3
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBasic
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

DB_NAME = "reb_system.db"

# Базова авторизація (можна змінити дані)
def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    return credentials.username

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_time TEXT,
            detection_means TEXT,
            target_type TEXT,
            first_order TEXT,
            location_first TEXT,
            route_orders TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: str = Depends(verify_user)):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    records = conn.execute("SELECT * FROM detections ORDER BY id DESC").fetchall()
    
    # Аналітика: підрахунок кількості однакових цілей на однакових ділянках (первинний наказ/ділянка)
    analytics_query = """
        SELECT target_type, location_first, COUNT(*) as count 
        FROM detections 
        GROUP BY target_type, location_first 
        ORDER BY count DESC
    """
    analytics = conn.execute(analytics_query).fetchall()
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "records": records,
        "analytics": analytics
    })

@app.post("/add_detection")
async def add_detection(
    means: list[str] = Form(...),
    sovenia_sub: list[str] = Form([]),
    target_type: str = Form(...),
    first_order: str = Form(...),
    location_first: str = Form(...),
    routes: list[str] = Form([]),
    custom_route: str = Form(""),
    notes: str = Form(""),
    user: str = Depends(verify_user)
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Формуємо рядок засобів (включаючи підпункти Совеня, якщо вони обрані)
    all_means = means.copy()
    if "Совеня" in all_means and sovenia_sub:
        all_means.remove("Совеня")
        all_means.append(f"Совеня ({', '.join(sovenia_sub)})")
    means_str = ", ".join(all_means)
    
    # Формуємо маршрути
    all_routes = routes.copy()
    if custom_route.strip():
        all_routes.append(custom_route.strip())
    routes_str = ", ".join(all_routes)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO detections (date_time, detection_means, target_type, first_order, location_first, route_orders, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (now, means_str, target_type, first_order, location_first, routes_str, notes))
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{rec_id}")
async def delete_record(rec_id: int, user: str = Depends(verify_user)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections WHERE id=?", (rec_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)