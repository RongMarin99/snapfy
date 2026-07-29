"""
Snapfy Downloader Pro - Database Models & Persistence Layer
"""

import os
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class VideoItem(Base):
    __tablename__ = "video_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, default="Untitled Video")
    url = Column(Text, nullable=False, unique=True)
    thumbnail = Column(Text, nullable=True)
    platform = Column(String(100), nullable=False, default="Generic")
    episode_num = Column(Integer, default=1)
    status = Column(String(50), default="Waiting")  # Waiting, Scraping, Downloading, Paused, Merging, Finished, Failed
    folder = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    file_size = Column(Float, default=0.0)  # Size in MB
    duration = Column(Float, default=0.0)   # Duration in seconds
    progress = Column(Float, default=0.0)   # Progress 0.0 - 100.0
    speed = Column(String(50), default="0 KB/s")
    eta = Column(String(50), default="--:--")
    stream_url = Column(Text, nullable=True)
    subtitle_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "platform": self.platform,
            "episode_num": self.episode_num,
            "status": self.status,
            "folder": self.folder,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration": self.duration,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

def get_db_path(custom_dir: str = None) -> str:
    if custom_dir:
        os.makedirs(custom_dir, exist_ok=True)
        return os.path.join(custom_dir, "snapfy.db")
    
    app_data_dir = os.path.join(os.path.expanduser("~"), ".snapfy")
    os.makedirs(app_data_dir, exist_ok=True)
    return os.path.join(app_data_dir, "snapfy.db")

def init_db(db_path: str = None):
    path = db_path or get_db_path()
    engine = create_engine(f"sqlite:///{path}", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

def get_session_factory(db_path: str = None):
    return init_db(db_path)
