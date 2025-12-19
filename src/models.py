from datetime import datetime

from sqlalchemy import Integer, DateTime, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)

    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    price_usd: Mapped[int] = mapped_column(Integer, nullable=False)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False)

    username: Mapped[str] = mapped_column(String(255), nullable=False)

    phone_number: Mapped[int] = mapped_column(BigInteger, nullable=False)

    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    images_count: Mapped[int] = mapped_column(Integer, nullable=False)

    car_number: Mapped[str] = mapped_column(String(20), nullable=False)
    car_vin: Mapped[str] = mapped_column(String(50), nullable=False)

    datetime_found: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
