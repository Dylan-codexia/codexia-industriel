from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import decode_token
from models.models import User, RoleEnum

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dépendance FastAPI : vérifie le token JWT et retourne l'utilisateur connecté.
    Utilisée sur toutes les routes protégées avec : Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise credentials_exception
    return user

def require_manager(current_user: User = Depends(get_current_user)) -> User:
    """Exige le rôle manager, admin_local ou admin."""
    if current_user.role not in (RoleEnum.manager, RoleEnum.admin_local, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Accès réservé aux managers")
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige le rôle admin ou admin_local."""
    if current_user.role not in (RoleEnum.admin_local, RoleEnum.admin):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return current_user

def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige le rôle admin uniquement."""
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur général")
    return current_user
