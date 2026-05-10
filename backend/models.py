from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    predictions = relationship("PredictionHistory", back_populates="owner")

class PredictionHistory(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    total_assets = Column(Float)
    total_liabilities = Column(Float)
    current_assets = Column(Float)
    current_liabilities = Column(Float)
    net_income = Column(Float)
    revenue = Column(Float)
    operating_income = Column(Float)
    cash_flow = Column(Float)
    debt_equity_ratio = Column(Float)
    credit_score = Column(Float)
    
    risk_label = Column(Integer) # 0 for Low Risk, 1 for High Risk
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="predictions")
