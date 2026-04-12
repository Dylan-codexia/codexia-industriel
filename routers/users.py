from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.dependencies import get_current_user, require_admin, require_super_admin
from models.models import User, Affiliation, RoleEnum
from models.schemas import UserOut, UserSummary, SetRoleRequest, AffiliationRequest, AffiliationOut

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

# ──────────────────────────────────────────────
# LISTE DE TOUS LES UTILISATEURS (admin)
# ──────────────────────────────────────────────

@router.get("/", response_model=List[UserSummary])
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retourne tous les utilisateurs. Réservé aux admins."""
    return db.query(User).filter(User.is_active == True).all()

# ──────────────────────────────────────────────
# CHANGER LE RÔLE D'UN UTILISATEUR (admin)
# ──────────────────────────────────────────────

@router.put("/role", response_model=UserSummary)
def set_role(
    data: SetRoleRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """
    Modifie le rôle d'un utilisateur.
    Réservé à l'administrateur général uniquement.
    """
    if data.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Impossible de modifier son propre rôle")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    user.role = data.role
    db.commit()
    db.refresh(user)
    return user

# ──────────────────────────────────────────────
# AFFILIATIONS
# ──────────────────────────────────────────────

@router.get("/affiliations", response_model=List[AffiliationOut])
def list_affiliations(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retourne toutes les affiliations. Réservé aux admins."""
    return db.query(Affiliation).all()

@router.post("/affiliations", response_model=AffiliationOut, status_code=201)
def create_affiliation(
    data: AffiliationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Affilie un utilisateur à un manager."""
    # Vérifier que les deux existent
    user = db.query(User).filter(User.id == data.user_id).first()
    mgr  = db.query(User).filter(User.id == data.manager_id).first()
    if not user or not mgr:
        raise HTTPException(status_code=404, detail="Utilisateur ou manager introuvable")
    if mgr.role not in (RoleEnum.manager, RoleEnum.admin_local, RoleEnum.admin):
        raise HTTPException(status_code=400, detail="L'utilisateur cible n'est pas manager")

    # Supprimer l'ancienne affiliation si elle existe
    existing = db.query(Affiliation).filter(Affiliation.user_id == data.user_id).first()
    if existing:
        db.delete(existing)

    affil = Affiliation(user_id=data.user_id, manager_id=data.manager_id)
    db.add(affil)
    db.commit()
    db.refresh(affil)
    return affil

@router.delete("/affiliations/{user_id}", status_code=204)
def delete_affiliation(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Supprime l'affiliation d'un utilisateur."""
    affil = db.query(Affiliation).filter(Affiliation.user_id == user_id).first()
    if not affil:
        raise HTTPException(status_code=404, detail="Affiliation introuvable")
    db.delete(affil)
    db.commit()

# ──────────────────────────────────────────────
# ÉQUIPE D'UN MANAGER
# ──────────────────────────────────────────────

@router.get("/my-team", response_model=List[UserSummary])
def get_my_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retourne les utilisateurs affiliés au manager connecté."""
    if current_user.role not in (RoleEnum.manager, RoleEnum.admin_local, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Accès réservé aux managers")

    affils = db.query(Affiliation).filter(Affiliation.manager_id == current_user.id).all()
    user_ids = [a.user_id for a in affils]
    return db.query(User).filter(User.id.in_(user_ids)).all()
