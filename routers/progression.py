from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_user
from models.models import User, Progression
from models.schemas import ProgressionIn, ProgressionOut

router = APIRouter(prefix="/progression", tags=["Progression"])

@router.get("/me", response_model=ProgressionOut)
def get_my_progression(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Charge la progression du compte connecté."""
    prog = db.query(Progression).filter(Progression.user_id == current_user.id).first()
    if not prog:
        # Créer une progression vide si elle n'existe pas
        prog = Progression(user_id=current_user.id)
        db.add(prog)
        db.commit()
        db.refresh(prog)
    return prog

@router.put("/me", response_model=ProgressionOut)
def save_my_progression(
    data: ProgressionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sauvegarde la progression du compte connecté.
    Remplace complètement les données existantes.
    """
    prog = db.query(Progression).filter(Progression.user_id == current_user.id).first()
    if not prog:
        prog = Progression(user_id=current_user.id)
        db.add(prog)

    prog.done_json         = data.done_json
    prog.mission_xp        = data.mission_xp
    prog.active_days       = data.active_days
    prog.last_day          = data.last_day
    prog.active_title_json = data.active_title_json

    db.commit()
    db.refresh(prog)
    return prog

@router.get("/{user_id}", response_model=ProgressionOut)
def get_user_progression(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Charge la progression d'un autre utilisateur.
    Accessible uniquement par un manager affilié ou un admin.
    """
    from models.models import RoleEnum, Affiliation

    # Vérification accès
    if current_user.role == RoleEnum.user:
        raise HTTPException(status_code=403, detail="Accès non autorisé")

    if current_user.role == RoleEnum.manager:
        affil = db.query(Affiliation).filter(
            Affiliation.user_id    == user_id,
            Affiliation.manager_id == current_user.id
        ).first()
        if not affil:
            raise HTTPException(status_code=403, detail="Cet utilisateur n'est pas dans votre équipe")

    prog = db.query(Progression).filter(Progression.user_id == user_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Progression introuvable")
    return prog
