import uuid
from datetime import datetime
from sqlalchemy import DateTime,JSON,String,Float,func
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class CausalAnalysis(Base):
 __tablename__="causal_analyses";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()));dataset_id:Mapped[str]=mapped_column(String(36),index=True);treatment:Mapped[str]=mapped_column(String);outcome:Mapped[str]=mapped_column(String);confounders:Mapped[dict]=mapped_column(JSON);estimator:Mapped[str]=mapped_column(String);estimated_effect:Mapped[float]=mapped_column(Float);result:Mapped[dict]=mapped_column(JSON);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class ScenarioRun(Base):
 __tablename__="scenario_runs";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()));dataset_id:Mapped[str|None]=mapped_column(String(36));causal_analysis_id:Mapped[str|None]=mapped_column(String(36));intervention:Mapped[dict]=mapped_column(JSON);result:Mapped[dict]=mapped_column(JSON);method_type:Mapped[str]=mapped_column(String);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class ReliabilityEvaluation(Base):
 __tablename__="reliability_evaluations";id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()));decision_id:Mapped[str|None]=mapped_column(String(36));status:Mapped[str]=mapped_column(String(32));ecds:Mapped[float|None]=mapped_column(Float);details:Mapped[dict]=mapped_column(JSON);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
