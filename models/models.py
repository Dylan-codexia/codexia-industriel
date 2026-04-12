from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from core.database import Base

def generate_uid():
    return str(uuid.uuid4())

# ──────────────────────────────────────────────
# ÉNUMÉRATIONS
# ──────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    user        = "user"
    manager     = "manager"
    admin_local = "admin_local"
    admin       = "admin"

class MissionStatusEnum(str, enum.Enum):
    active              = "active"
    pending_validation  = "pending_validation"
    validated           = "validated"
    expired             = "expired"

class NotifTypeEnum(str, enum.Enum):
    mission                    = "mission"
    mission_validated          = "mission_validated"
    mission_rejected           = "mission_rejected"
    validation_request         = "validation_request"
    objectif                   = "objectif"
    objectif_validated         = "objectif_validated"
    objectif_rejected          = "objectif_rejected"
    objectif_validation_request = "objectif_validation_request"

# ──────────────────────────────────────────────
# TABLE : USERS
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id          = Column(String, primary_key=True, default=generate_uid)
    name        = Column(String(80), nullable=False)
    email       = Column(String(120), unique=True, nullable=False, index=True)
    pseudo      = Column(String(30), unique=True, nullable=False, index=True)
    pwd_hash    = Column(String, nullable=False)
    role        = Column(Enum(RoleEnum), default=RoleEnum.user, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    is_active   = Column(Boolean, default=True)

    # Relations
    progression = relationship("Progression", back_populates="user", uselist=False)
    missions_received  = relationship("Mission",  foreign_keys="Mission.receiver_id",  back_populates="receiver")
    missions_sent      = relationship("Mission",  foreign_keys="Mission.manager_id",   back_populates="manager")
    objectifs_received = relationship("Objectif", foreign_keys="Objectif.receiver_id", back_populates="receiver")
    objectifs_sent     = relationship("Objectif", foreign_keys="Objectif.manager_id",  back_populates="manager")
    notifications      = relationship("Notification", back_populates="user", order_by="Notification.created_at.desc()")
    affiliations_as_user    = relationship("Affiliation", foreign_keys="Affiliation.user_id",    back_populates="user")
    affiliations_as_manager = relationship("Affiliation", foreign_keys="Affiliation.manager_id", back_populates="manager")

# ──────────────────────────────────────────────
# TABLE : PROGRESSION
# Une ligne par utilisateur, stocke tout son état
# ──────────────────────────────────────────────

class Progression(Base):
    __tablename__ = "progressions"

    id          = Column(String, primary_key=True, default=generate_uid)
    user_id     = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    done_json   = Column(Text, default="{}")   # JSON : { "quest_id_0": true, ... }
    mission_xp  = Column(Integer, default=0)   # XP bonus des missions/objectifs validés
    active_days = Column(Integer, default=1)
    last_day    = Column(String, default="")   # date ISO pour compter les jours actifs
    active_title_json = Column(Text, default="null")  # JSON du titre actif choisi
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="progression")

# ──────────────────────────────────────────────
# TABLE : AFFILIATIONS
# Quel utilisateur est rattaché à quel manager
# ──────────────────────────────────────────────

class Affiliation(Base):
    __tablename__ = "affiliations"

    id         = Column(String, primary_key=True, default=generate_uid)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    manager_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user    = relationship("User", foreign_keys=[user_id],    back_populates="affiliations_as_user")
    manager = relationship("User", foreign_keys=[manager_id], back_populates="affiliations_as_manager")

# ──────────────────────────────────────────────
# TABLE : MISSIONS
# ──────────────────────────────────────────────

class Mission(Base):
    __tablename__ = "missions"

    id           = Column(String, primary_key=True, default=generate_uid)
    text         = Column(String(200), nullable=False)
    xp           = Column(Integer, nullable=False)    # 20, 40 ou 80
    deadline     = Column(DateTime, nullable=False)
    status       = Column(Enum(MissionStatusEnum), default=MissionStatusEnum.active)
    manager_id   = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id  = Column(String, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    requested_at = Column(DateTime, nullable=True)   # quand l'utilisateur demande validation
    validated_at = Column(DateTime, nullable=True)   # quand le manager valide

    manager  = relationship("User", foreign_keys=[manager_id],  back_populates="missions_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="missions_received")

# ──────────────────────────────────────────────
# TABLE : OBJECTIFS ANNUELS
# ──────────────────────────────────────────────

class Objectif(Base):
    __tablename__ = "objectifs"

    id           = Column(String, primary_key=True, default=generate_uid)
    text         = Column(String(200), nullable=False)
    xp           = Column(Integer, nullable=False)    # 50, 100 ou 200
    deadline     = Column(DateTime, nullable=False)
    status       = Column(Enum(MissionStatusEnum), default=MissionStatusEnum.active)
    manager_id   = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id  = Column(String, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
    requested_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)

    manager  = relationship("User", foreign_keys=[manager_id],  back_populates="objectifs_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="objectifs_received")

# ──────────────────────────────────────────────
# TABLE : NOTIFICATIONS
# ──────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id           = Column(String, primary_key=True, default=generate_uid)
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    type         = Column(Enum(NotifTypeEnum), nullable=False)
    title        = Column(String(100), nullable=False)
    sub          = Column(String(200), default="")
    is_read      = Column(Boolean, default=False)
    mission_id   = Column(String, nullable=True)   # référence optionnelle
    objectif_id  = Column(String, nullable=True)
    requester_id = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
