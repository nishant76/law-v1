"""
Creates a dev user for local development.
Run after migrations: python scripts/seed_dev_user.py

Credentials created:
  Email:    dev@superadvocate.ai
  Password: devpassword123
  Firm:     SuperAdvocate Dev
  Role:     firm_admin
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import AsyncSessionLocal
from backend.services.auth_service import get_auth_service


async def seed():
    async with AsyncSessionLocal() as db:
        auth_service = await get_auth_service(db)
        success, message, data = await auth_service.register_firm(
            firm_name="SuperAdvocate Dev",
            email="dev@superadvocate.ai",
            password="devpassword123",
            plan="trial",
        )
        if success:
            print(f"✓ Dev user created")
            print(f"  Email:    dev@superadvocate.ai")
            print(f"  Password: devpassword123")
            if data:
                print(f"  Firm ID:  {data.get('firm_id', 'n/a')}")
        else:
            print(f"✗ Seed failed: {message}")


if __name__ == "__main__":
    asyncio.run(seed())
