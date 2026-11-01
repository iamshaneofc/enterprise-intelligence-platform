"""
Idempotent Demo User Creation Script for EIP Local Development.
Creates:
- Email: demo@eip.local
- Password: EIP-Demo@2026!
- Full Name: EIP Demo User
- Default Workspace & Admin Member
"""
import sys
import os
import re

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, engine
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.core.logging import logger

DEMO_EMAIL = "demo@eip.local"
DEMO_PASSWORD = "EIP-Demo@2026!"
DEMO_NAME = "EIP Demo User"


def provision_demo_user(db: Session) -> dict:
    user = db.query(User).filter(User.email == DEMO_EMAIL.lower()).first()
    if not user:
        user = User(
            email=DEMO_EMAIL.lower(),
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name=DEMO_NAME,
            role="engineer",
            is_active=True,
        )
        db.add(user)
        db.flush()
        print(f"[CREATED] User: {user.email} (ID: {user.id})")
    else:
        user.hashed_password = hash_password(DEMO_PASSWORD)
        user.full_name = DEMO_NAME
        user.is_active = True
        db.flush()
        print(f"[EXISTS] User: {user.email} (ID: {user.id}) - password hash refreshed")

    # Verify password verification
    assert verify_password(DEMO_PASSWORD, user.hashed_password), "Password verification failed!"

    # Ensure default workspace exists
    workspace = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
    if not workspace:
        slug_base = re.sub(r"[^a-zA-Z0-9]+", "-", user.full_name.lower()).strip("-") or "default"
        slug = f"{slug_base}-{user.id[:8]}"
        workspace = Workspace(
            name=f"{user.full_name}'s Workspace",
            slug=slug,
            description="Default workspace created for demo user",
            owner_id=user.id,
        )
        db.add(workspace)
        db.flush()
        print(f"[CREATED] Workspace: {workspace.name} (ID: {workspace.id}, Slug: {workspace.slug})")

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="admin",
        )
        db.add(member)
        db.flush()
        print(f"[CREATED] Workspace Member: Admin role assigned to user")
    else:
        print(f"[EXISTS] Workspace: {workspace.name} (ID: {workspace.id})")
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        ).first()
        if not member:
            member = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role="admin",
            )
            db.add(member)
            db.flush()
            print(f"[CREATED] Workspace Member: Admin role assigned to user")

    db.commit()

    # Generate JWT token to verify authentication flow
    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
    })

    return {
        "status": "success",
        "email": user.email,
        "full_name": user.full_name,
        "user_id": user.id,
        "workspace_id": workspace.id,
        "token_prefix": token[:20] + "...",
    }


def main():
    print("=" * 60)
    print("Provisioning EIP Demo User in Configured Database...")
    print("=" * 60)

    db = SessionLocal()
    try:
        res = provision_demo_user(db)
        print(f"\nDemo user successfully provisioned and verified!")
        print(f"Email: {res['email']}")
        print(f"Workspace ID: {res['workspace_id']}")
        print(f"Token generation verified: {res['token_prefix']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
