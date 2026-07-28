from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.database.base import Base


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True)

    delivery_id = Column(
        String(255),
        nullable=False,
        unique=True,
    )

    event_type = Column(
        String(100),
        nullable=False,
    )

    received_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    