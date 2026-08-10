"""
Snapfy Queue Manager & Workflow Orchestrator
"""

from typing import List
from PySide6.QtCore import QObject, Signal
from app.database.models import get_session_factory, VideoItem
from app.core.logger import logger

class QueueManager(QObject):
    item_added = Signal(dict)
    item_updated = Signal(dict)
    item_deleted = Signal(int)

    def __init__(self, db_path: str = None):
        super().__init__()
        self.Session = get_session_factory(db_path)

    def add_video(self, video_data: dict) -> dict:
        session = self.Session()
        try:
            # Check if URL already exists
            existing = session.query(VideoItem).filter_by(url=video_data["url"]).first()
            if existing:
                logger.info(f"Video URL already exists in queue: {video_data['url']}")
                return existing.to_dict()

            item = VideoItem(
                title=video_data.get("title", "Untitled Video"),
                url=video_data["url"],
                thumbnail=video_data.get("thumbnail"),
                platform=video_data.get("platform", "Generic"),
                episode_num=video_data.get("episode_num", 1),
                status=video_data.get("status", "Waiting"),
                folder=video_data.get("folder"),
                stream_url=video_data.get("stream_url")
            )
            session.add(item)
            session.commit()
            item_dict = item.to_dict()
            self.item_added.emit(item_dict)
            return item_dict
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add video to queue DB: {e}")
            return {}
        finally:
            session.close()

    def add_videos_batch(self, videos_list: List[dict]) -> List[dict]:
        added = []
        for v in videos_list:
            res = self.add_video(v)
            if res:
                added.append(res)
        return added

    def update_status(self, video_id: int, status: str, progress: float = None, speed: str = None, eta: str = None, file_path: str = None, file_size: float = None):
        session = self.Session()
        try:
            item = session.query(VideoItem).filter_by(id=video_id).first()
            if item:
                item.status = status
                if progress is not None:
                    item.progress = progress
                if speed is not None:
                    item.speed = speed
                if eta is not None:
                    item.eta = eta
                if file_path is not None:
                    item.file_path = file_path
                if file_size is not None:
                    item.file_size = file_size
                
                session.commit()
                item_dict = item.to_dict()
                self.item_updated.emit(item_dict)
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update video status in DB: {e}")
        finally:
            session.close()

    def get_all_items(self) -> List[dict]:
        session = self.Session()
        try:
            items = session.query(VideoItem).order_by(VideoItem.id.asc()).all()
            return [item.to_dict() for item in items]
        finally:
            session.close()

    def get_waiting_items(self) -> List[dict]:
        session = self.Session()
        try:
            items = session.query(VideoItem).filter_by(status="Waiting").order_by(VideoItem.id.asc()).all()
            return [item.to_dict() for item in items]
        finally:
            session.close()

    def delete_video(self, video_id: int) -> bool:
        session = self.Session()
        try:
            item = session.query(VideoItem).filter_by(id=video_id).first()
            if not item:
                return False
            session.delete(item)
            session.commit()
            self.item_deleted.emit(video_id)
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete video {video_id} from queue DB: {e}")
            return False
        finally:
            session.close()

    def clear_queue(self):
        session = self.Session()
        try:
            session.query(VideoItem).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to clear queue DB: {e}")
        finally:
            session.close()

queue_manager = QueueManager()
