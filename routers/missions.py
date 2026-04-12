from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from core.database import get_db
from core.dependencies import get_current_user, require_manager
from models.models import User, Mission, Notification, Progression, Affiliation, RoleEnum
from models.models import MissionStatusEnum, NotifTypeEnum
from models.schemas import MissionCreate, MissionOut

router = APIRouter(prefix="/missions", tags=["Missions"])

def _add_notif(db, user_id, type_, title, sub, mission_id=None, requester_id=None):
    notif = Notification(
        user_id=user_id, type=type_, title=title, sub=sub,
        mission_id=mission_id, requester_id=requester_id
    )
    db.add(notif)

# ──────────────────────────────────────────────
# ENVOYER UNE MISSION (manager → utilisateur)
# ──────────────────────────────────────────────

@router.post("/", response_model=MissionOut, status_code=201)
def send_mission(
    data: MissionCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Le manager envoie une mission à un utilisateur affilié."""
    # Vérifier l'affiliation
    if current_user.role == RoleEnum.manager:
        affil = db.query(Affiliation).filter(
            Affiliation.user_id    == data.receiver_id,
            Affiliation.manager_id == current_user.id
        ).first()
        if not affil:
            raise HTTPException(status_code=403, detail="Utilisateur non affilié")

    deadline = datetime.utcfromtimestamp(data.deadline_ms / 1000)
    mission = Mission(
        text        = data.text,
        xp          = data.xp,
        deadline    = deadline,
        manager_id  = current_user.id,
        receiver_id = data.receiver_id,
    )
    db.add(mission)
    db.flush()

    _add_notif(
        db, data.receiver_id,
        NotifTypeEnum.mission,
        f"🎯 Nouvelle mission reçue",
        f"{data.xp} XP — \"{data.text[:50]}{'...' if len(data.text)>50 else ''}\"",
        mission_id=mission.id
    )
    db.commit()
    db.refresh(mission)
    mission.manager_name = current_user.pseudo
    return mission

# ──────────────────────────────────────────────
# VOIR MES MISSIONS (utilisateur)
# ──────────────────────────────────────────────

@router.get("/mine", response_model=List[MissionOut])
def get_my_missions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retourne toutes les missions de l'utilisateur connecté."""
    now = datetime.utcnow()
    missions = db.query(Mission).filter(Mission.receiver_id == current_user.id).all()

    # Expirer automatiquement les missions dépassées
    for m in missions:
        if m.status == MissionStatusEnum.active and m.deadline < now:
            m.status = MissionStatusEnum.expired
    db.commit()

    for m in missions:
        m.manager_name = m.manager.pseudo if m.manager else None
    return missions

# ──────────────────────────────────────────────
# DEMANDER VALIDATION (utilisateur)
# ──────────────────────────────────────────────

@router.post("/{mission_id}/request-validation", response_model=MissionOut)
def request_validation(
    mission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """L'utilisateur demande la validation de sa mission."""
    mission = db.query(Mission).filter(
        Mission.id == mission_id,
        Mission.receiver_id == current_user.id
    ).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if mission.deadline < datetime.utcnow():
        mission.status = MissionStatusEnum.expired
        db.commit()
        raise HTTPException(status_code=400, detail="Mission expirée")
    if mission.status != MissionStatusEnum.active:
        raise HTTPException(status_code=400, detail="Mission non active")

    mission.status       = MissionStatusEnum.pending_validation
    mission.requested_at = datetime.utcnow()

    _add_notif(
        db, mission.manager_id,
        NotifTypeEnum.validation_request,
        "📤 Demande de validation",
        f"{current_user.pseudo} — \"{mission.text[:40]}...\"",
        mission_id=mission.id,
        requester_id=current_user.id
    )
    db.commit()
    db.refresh(mission)
    mission.manager_name = mission.manager.pseudo if mission.manager else None
    return mission

# ──────────────────────────────────────────────
# VALIDER / REFUSER (manager)
# ──────────────────────────────────────────────

@router.post("/{mission_id}/validate", response_model=MissionOut)
def validate_mission(
    mission_id: str,
    accept: bool,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Le manager accepte ou refuse la demande de validation."""
    mission = db.query(Mission).filter(
        Mission.id         == mission_id,
        Mission.manager_id == current_user.id
    ).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable")
    if mission.status != MissionStatusEnum.pending_validation:
        raise HTTPException(status_code=400, detail="Mission non en attente de validation")

    if accept:
        mission.status       = MissionStatusEnum.validated
        mission.validated_at = datetime.utcnow()

        # Attribuer XP dans la progression
        prog = db.query(Progression).filter(Progression.user_id == mission.receiver_id).first()
        if prog:
            prog.mission_xp = (prog.mission_xp or 0) + mission.xp

        _add_notif(
            db, mission.receiver_id,
            NotifTypeEnum.mission_validated,
            "✓ Mission validée !",
            f"+{mission.xp} XP — \"{mission.text[:40]}...\"",
            mission_id=mission.id
        )
    else:
        mission.status       = MissionStatusEnum.active
        mission.requested_at = None
        _add_notif(
            db, mission.receiver_id,
            NotifTypeEnum.mission_rejected,
            "✗ Validation refusée",
            f"\"{mission.text[:40]}...\" — Vous pouvez resoumettre.",
            mission_id=mission.id
        )

    db.commit()
    db.refresh(mission)
    mission.manager_name = current_user.pseudo
    return mission

# ──────────────────────────────────────────────
# MISSIONS DE MON ÉQUIPE (manager)
# ──────────────────────────────────────────────

@router.get("/team", response_model=List[MissionOut])
def get_team_missions(
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Retourne toutes les missions envoyées par le manager connecté."""
    missions = db.query(Mission).filter(Mission.manager_id == current_user.id).all()
    for m in missions:
        m.manager_name = current_user.pseudo
    return missions
