from datetime import datetime
from celery import Celery

from db.database import async_session_maker
from db.models import Link
from sqlalchemy import select, create_engine

from config import DAYS_TO_EXPIRE
from sqlalchemy.orm import sessionmaker

from config import POSTGRES_PASSWORD, POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB


DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

celery = Celery('tasks', broker='redis://redis:6379')

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

@celery.task(name="delete_expired_links", default_retry_delay=5, max_retries=3)
def delete_expired_links():
    query = select(Link).where(Link.expires_at < datetime.now())
    result = session.execute(query)
    links = result.scalars().all()

    for link in links:
        link.deleted = True

    session.commit()

@celery.task(name="delete_not_used_links", default_retry_delay=5, max_retries=3)
def delete_not_used_links():
    query = select(Link).filter((Link.last_usage_at - datetime.now()).days >= DAYS_TO_EXPIRE)
    result = session.execute(query)
    links = result.scalars().all()

    for link in links:
        link.deleted = True

    session.commit()


celery.conf.beat_schedule = {
    'delete_expired_links': {
        'task': 'tasks.delete_expired_links',
        'schedule': 60.0
    },
    'delete_not_used_links': {
        'task': 'tasks.delete_not_used_links',
        'schedule': 120.0
    }
}
