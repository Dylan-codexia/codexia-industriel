from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from core.database import get_db
from core.dependencies import get_current_user, require_manager
from models.models import User, Objectif, Notification, Progression, Affiliation, RoleEnum
from models.models import MissionStatusEnum, NotifTypeEnum
from models.schemas import ObjectifCreate, ObjectifOut

router = APIRouter(prefix="/objectifs", tags=["Objectifs Annuels"])

MAX_OBJECTIFS = 5

def _add_notif(db, user_id, type_, title, sub, objectif_id=None, requester_id=None):
    notif = Notification(
        user_id=user_id, type=type_, title=title, sub=sub,
        objectif_id=objectif_id, requester_id=requester_id
    )
    db.add(notif)

@router.post("/", response_model=ObjectifOut, status_code=201)
def send_objectif(
    data: ObjectifCreate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Le manager attribue un objectif annuel. Maximum 5 actifs par utilisateur."""
    if current_user.role == RoleEnum.manager:
        affil = db.query(Affiliation).filter(
            Affiliation.user_id    == data.receiver_id,
            Affiliation.manager_id == current_user.id
        ).first()
        if not affil:
            raise HTTPException(status_code=403, detail="Utilisateur non affilié")

    # Vérifier le plafond de 5 objectifs actifs
    active_count = db.query(Objectif).filter(
        Objectif.receiver_id == data.receiver_id,
        Objectif.status.in_([MissionStatusEnum.active, MissionStatusEnum.pending_validation])
    ).count()
    if active_count >= MAX_OBJECTIFS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_OBJECTIFS} objectifs actifs atteint")

    deadline = datetime.utcfromtimestamp(data.deadline_ms / 1000)
    objectif = Objectif(
        text        = data.text,
        xp          = data.xp,
        deadline    = deadline,
        manager_id  = current_user.id,
        receiver_id = data.receiver_id,
    )
    db.add(objectif)
    db.flush()

    _add_notif(
        db, data.receiver_id,
        NotifTypeEnum.objectif,
        "🏆 Nouvel objectif annuel reçu",
        f"{data.xp} XP — \"{data.text[:50]}\"",
        objectif_id=objectif.id
    )
    db.commit()
    db.refresh(objectif)
    objectif.manager_name = current_user.pseudo
    return objectif

@router.get("/mine", response_model=List[ObjectifOut])
def get_my_objectifs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    objectifs = db.query(Objectif).filter(Objectif.receiver_id == current_user.id).all()
    for o in objectifs:
        if o.status == MissionStatusEnum.active and o.deadline < now:
            o.status = MissionStatusEnum.expired
        o.manager_name = o.manager.pseudo if o.manager else None
    db.commit()
    return objectifs

@router.post("/{objectif_id}/request-validation", response_model=ObjectifOut)
def request_validation(
    objectif_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    objectif = db.query(Objectif).filter(
        Objectif.id == objectif_id,
        Objectif.receiver_id == current_user.id
    ).first()
    if not objectif:
        raise HTTPException(status_code=404, detail="Objectif introuvable")
    if objectif.deadline < datetime.utcnow():
        objectif.status = MissionStatusEnum.expired
        db.commit()
        raise HTTPException(status_code=400, detail="Objectif expiré")
    if objectif.status != MissionStatusEnum.active:
        raise HTTPException(status_code=400, detail="Objectif non actif")

    objectif.status       = MissionStatusEnum.pending_validation
    objectif.requested_at = datetime.utcnow()

    _add_notif(
        db, objectif.manager_id,
        NotifTypeEnum.objectif_validation_request,
        "📤 Demande validation objectif",
        f"{current_user.pseudo} — \"{objectif.text[:40]}...\"",
        objectif_id=objectif.id,
        requester_id=current_user.id
    )
    db.commit()
    db.refresh(objectif)
    objectif.manager_name = objectif.manager.pseudo if objectif.manager else None
    return objectif

@router.post("/{objectif_id}/validate", response_model=ObjectifOut)
def validate_objectif(
    objectif_id: str,
    accept: bool,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db)
):
    objectif = db.query(Objectif).filter(
        Objectif.id         == objectif_id,
        Objectif.manager_id == current_user.id
    ).first()
    if not objectif:
        raise HTTPException(status_code=404, detail="Objectif introuvable")
    if objectif.status != MissionStatusEnum.pending_validation:
        raise HTTPException(status_code=400, detail="Objectif non en attente de validation")

    if accept:
        objectif.status       = MissionStatusEnum.validated
        objectif.validated_at = datetime.utcnow()
        prog = db.query(Progression).filter(Progression.user_id == objectif.receiver_id).first()
        if prog:
            prog.mission_xp = (prog.mission_xp or 0) + objectif.xp
        _add_notif(
            db, objectif.receiver_id,
            NotifTypeEnum.objectif_validated,
            "✓ Objectif annuel validé !",
            f"+{objectif.xp} XP",
            objectif_id=objectif.id
        )
    else:
        objectif.status       = MissionStatusEnum.active
        objectif.requested_at = None
        _add_notif(
            db, objectif.receiver_id,
            NotifTypeEnum.objectif_rejected,
            "✗ Validation objectif refusée",
            f"\"{objectif.text[:40]}...\"",
            objectif_id=objectif.id
        )

    db.commit()
    db.refresh(objectif)
    objectif.manager_name = current_user.pseudo
    return objectif
