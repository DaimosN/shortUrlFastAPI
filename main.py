import string
import random
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import URLItem, LogEntry
from logger import setup_logging

Base.metadata.create_all(bind=engine)

app = FastAPI()


class URLCreate(BaseModel):
    url: HttpUrl


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    db = next(get_db())
    app.logger = setup_logging(db)  # Настраиваем логирование при старте приложения


def generate_short_id(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


@app.post("/shorten")
def shorten_url(item: URLCreate, request: Request, db: Session = Depends(get_db)):
    # Генерируем уникальный short_id
    for _ in range(10):
        short_id = generate_short_id()
        existing = db.query(URLItem).filter(URLItem.short_id == short_id).first()
        if not existing:
            new_item = URLItem(short_id=short_id, full_url=str(item.url))
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            app.logger.info(f"Создана короткая ссылка: {short_id} для URL: {item.url} ip - {request.client.host}")
            return {"short_url": f"http://localhost:8000/{short_id}"}
    raise HTTPException(status_code=500, detail="Не удалось сгенерировать короткую ссылку")


@app.get("/logs")
def get_logs(db: Session = Depends(get_db)):
    logs = db.query(LogEntry).all()  # Получаем все записи из таблицы логов
    return [
        {
            "id": log.id,
            "level": log.level,
            "message": log.message,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]


@app.get("/{short_id}")
def redirect_to_full(short_id: str, request: Request, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        app.logger.warning(f"Попытка доступа к несуществующей короткой ссылке: {short_id}  ip - {request.client.host}")
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    app.logger.info(
        f"Перенаправление по короткой ссылке: {short_id} на URL: {url_item.full_url}  ip - {request.client.host}")
    return RedirectResponse(url=url_item.full_url)


@app.get("/stats/{short_id}")
def get_stats(short_id: str, request: Request, db: Session = Depends(get_db)):
    url_item = db.query(URLItem).filter(URLItem.short_id == short_id).first()
    if not url_item:
        app.logger.warning(f"Запрос статистики для несуществующей короткой ссылки: {short_id}  ip - {request.client.host}")
        raise HTTPException(status_code=404, detail="Короткая ссылка не найдена")
    app.logger.info(f"Запрошена статистика для короткой ссылки: {short_id}  ip - {request.client.host}")
    return {
        "short_id": url_item.short_id,
        "full_url": url_item.full_url
    }
