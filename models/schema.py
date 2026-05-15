from sqlalchemy import Column, Integer, String, Float, DateTime
from models.database import Base
import datetime

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, unique=True, index=True)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

class PlayerCache(Base):
    __tablename__ = "player_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    second_name = Column(String)
    team_id = Column(Integer)
    element_type = Column(Integer) # 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost = Column(Float)
    total_points = Column(Integer)
    ep_next = Column(Float) # Expected points next gameweek
    selected_by_percent = Column(Float)
    form = Column(Float)
