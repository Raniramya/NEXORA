import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

decision_evidence = Table("decision_evidence", Base.metadata, Column("decision_id", String(36), ForeignKey("decisions.id"), primary_key=True), Column("evidence_id", String(36), ForeignKey("decision_evidence_records.id"), primary_key=True))

class DecisionEvidenceRecord(Base):
 __tablename__="decision_evidence_records"; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); dataset_id:Mapped[str|None]=mapped_column(String(36)); evidence_type:Mapped[str]=mapped_column(String(64)); source_type:Mapped[str]=mapped_column(String(64)); source_id:Mapped[str|None]=mapped_column(String(36)); payload:Mapped[dict]=mapped_column(JSON); uncertainty:Mapped[dict]=mapped_column(JSON,default=dict); metadata_json:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class ProvenanceNode(Base):
 __tablename__="provenance_nodes"; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); node_type:Mapped[str]=mapped_column(String(64)); resource_type:Mapped[str]=mapped_column(String(64)); resource_id:Mapped[str|None]=mapped_column(String(36)); metadata_json:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class ProvenanceEdge(Base):
 __tablename__="provenance_edges"; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); source_node_id:Mapped[str]=mapped_column(String(36),ForeignKey("provenance_nodes.id")); target_node_id:Mapped[str]=mapped_column(String(36),ForeignKey("provenance_nodes.id")); relation_type:Mapped[str]=mapped_column(String(32)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class Decision(Base):
 __tablename__="decisions"; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); question:Mapped[str]=mapped_column(String); decision_type:Mapped[str]=mapped_column(String(32)); recommendation:Mapped[str|None]=mapped_column(String); reliability_status:Mapped[str]=mapped_column(String(32)); ecds:Mapped[float|None]=mapped_column(); review_required:Mapped[bool]=mapped_column(); abstention_reason:Mapped[str|None]=mapped_column(String); reliability_details:Mapped[dict]=mapped_column(JSON); provenance_root_id:Mapped[str|None]=mapped_column(String(36),ForeignKey("provenance_nodes.id")); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now()); evidence=relationship("DecisionEvidenceRecord",secondary=decision_evidence)
