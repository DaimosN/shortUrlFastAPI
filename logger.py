# файл logger.py
import logging
from sqlalchemy.orm import Session
from models import LogEntry


class DBHandler(logging.Handler):
    def __init__(self, db: Session):
        super().__init__()
        self.db = db

    def emit(self, record):
        log_entry = LogEntry(level=record.levelname, message=self.format(record))
        self.db.add(log_entry)
        self.db.commit()


def setup_logging(db: Session):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Создаем обработчик для базы данных
    db_handler = DBHandler(db)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    db_handler.setFormatter(formatter)

    logger.addHandler(db_handler)
    return logger
