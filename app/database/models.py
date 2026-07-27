"""
Snapfy Downloader Pro - Database Models & Persistence Layer
"""

import os
from datetime import datetime
from typing import Generator
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

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

    histories = relationship("DownloadHistory", back_populates="video_item", cascade="all, delete-orphan")

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

class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("video_items.id"), nullable=True)
    download_time = Column(DateTime, default=datetime.utcnow)
    size = Column(Float, default=0.0)        # in MB
    duration = Column(Float, default=0.0)    # in seconds
    speed = Column(String(50), default="0 KB/s")
    result = Column(String(50), default="Success")  # Success, Failed, Cancelled
    error_message = Column(Text, nullable=True)

    video_item = relationship("VideoItem", back_populates="histories")

class AppSettingsModel(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)

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
