from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def register(self, data: UserCreate) -> User:
        if await self.repository.exists(data.email):
            raise ValueError("Email is already registered.")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
        )

        return await self.repository.create(user)

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.repository.get_by_email(email)

        if user is None:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    async def login(self, email: str, password: str) -> str | None:
        user = await self.authenticate(email, password)

        if user is None:
            return None

        return create_access_token(user.email)