from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from models.models import RoleEnum, MissionStatusEnum

# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    str
    pseudo:   str
    password: str

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Mot de passe trop court (6 caractères minimum)")
        return v

    @field_validator("pseudo")
    def pseudo_max_length(cls, v):
        if len(v) > 30:
            raise ValueError("Pseudo trop long (30 caractères maximum)")
        return v.strip()

class LoginRequest(BaseModel):
    identifier: str   # email ou pseudo
    password:   str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"

# ──────────────────────────────────────────────
# USER
# ──────────────────────────────────────────────

class UserOut(BaseModel):
    id:         str
    name:       str
    email:      str
    pseudo:     str
    role:       RoleEnum
    created_at: datetime

    class Config:
        from_attributes = True

class UserSummary(BaseModel):
    """Version allégée pour les listes (vue manager)"""
    id:     str
    pseudo: str
    email:  str
    role:   RoleEnum

    class Config:
        from_attributes = True

class SetRoleRequest(BaseModel):
    user_id: str
    role:    RoleEnum

# ──────────────────────────────────────────────
# PROGRESSION
# ──────────────────────────────────────────────

class ProgressionIn(BaseModel):
    done_json:         str  # JSON stringifié
    mission_xp:        int = 0
    active_days:       int = 1
    last_day:          str = ""
    active_title_json: str = "null"

class ProgressionOut(BaseModel):
    user_id:           str
    done_json:         str
    mission_xp:        int
    active_days:       int
    last_day:          str
    active_title_json: str
    updated_at:        datetime

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────
# AFFILIATIONS
# ──────────────────────────────────────────────

class AffiliationRequest(BaseModel):
    user_id:    str
    manager_id: str

class AffiliationOut(BaseModel):
    id:         str
    user_id:    str
    manager_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────
# MISSIONS
# ──────────────────────────────────────────────

class MissionCreate(BaseModel):
    receiver_id:   str
    text:          str
    xp:            int
    deadline_ms:   int  # timestamp Unix en millisecondes

    @field_validator("xp")
    def xp_valid(cls, v):
        if v not in (20, 40, 80):
            raise ValueError("XP mission doit être 20, 40 ou 80")
        return v

    @field_validator("text")
    def text_max(cls, v):
        if len(v) > 200:
            raise ValueError("Description trop longue (200 caractères max)")
        return v.strip()

class MissionOut(BaseModel):
    id:           str
    text:         str
    xp:           int
    deadline:     datetime
    status:       MissionStatusEnum
    manager_id:   str
    manager_name: Optional[str] = None
    receiver_id:  str
    created_at:   datetime
    validated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────
# OBJECTIFS ANNUELS
# ──────────────────────────────────────────────

class ObjectifCreate(BaseModel):
    receiver_id:   str
    text:          str
    xp:            int
    deadline_ms:   int

    @field_validator("xp")
    def xp_valid(cls, v):
        if v not in (50, 100, 200):
            raise ValueError("XP objectif doit être 50, 100 ou 200")
        return v

    @field_validator("text")
    def text_max(cls, v):
        if len(v) > 200:
            raise ValueError("Description trop longue")
        return v.strip()

class ObjectifOut(BaseModel):
    id:           str
    text:         str
    xp:           int
    deadline:     datetime
    status:       MissionStatusEnum
    manager_id:   str
    manager_name: Optional[str] = None
    receiver_id:  str
    created_at:   datetime
    validated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────────────

class NotificationOut(BaseModel):
    id:           str
    type:         str
    title:        str
    sub:          str
    is_read:      bool
    mission_id:   Optional[str]
    objectif_id:  Optional[str]
    requester_id: Optional[str]
    created_at:   datetime

    class Config:
        from_attributes = True
