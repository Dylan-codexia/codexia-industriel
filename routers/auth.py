from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token
from core.dependencies import get_current_user
from models.models import User, Progression, RoleEnum
from models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentification"])

# ──────────────────────────────────────────────
# INSCRIPTION
# ──────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Crée un nouveau compte utilisateur.
    - Vérifie que l'email et le pseudo sont uniques
    - Hash le mot de passe avec bcrypt
    - Crée une progression vide liée au compte
    - Retourne un token JWT pour connexion immédiate
    """
    # Vérification unicité
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    if db.query(User).filter(User.pseudo.ilike(data.pseudo)).first():
        raise HTTPException(status_code=400, detail="Ce pseudo est déjà pris")

    # Bootstrap : Thomas devient admin automatiquement
    role = RoleEnum.user
    if data.email.lower() == "dj.tom@gmail.com" or data.pseudo.lower() == "thomas":
        role = RoleEnum.admin

    user = User(
        name     = data.name,
        email    = data.email.lower(),
        pseudo   = data.pseudo,
        pwd_hash = hash_password(data.password),
        role     = role,
    )
    db.add(user)
    db.flush()  # obtenir l'id avant le commit

    # Créer une progression vide
    progression = Progression(user_id=user.id)
    db.add(progression)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

# ──────────────────────────────────────────────
# CONNEXION
# ──────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Connexion par email ou pseudo + mot de passe.
    Retourne un token JWT valide 7 jours.
    """
    identifier = data.identifier.strip().lower()

    user = (
        db.query(User)
        .filter(
            (User.email == identifier) | (User.pseudo.ilike(identifier))
        )
        .first()
    )

    if not user or not verify_password(data.password, user.pwd_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect"
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

# ──────────────────────────────────────────────
# PROFIL CONNECTÉ
# ──────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Retourne les informations du compte connecté."""
    return current_user
