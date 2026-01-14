import logging
from typing import Optional, Dict, Any
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timezone
from src.crud.user_crud import user_repository
from src.schemas.user_schema import (
    UserUpdateAdmin,
    UserUpdateProfile,
    UserListResponse,
    UserCreate,
)
from src.models.user_model import User, UserRole, UserStatus

from src.core.exception_utils import raise_for_status
from src.core.exceptions import (
    ResourceNotFound,
    NotAuthorized,
    ValidationError,
    ResourceAlreadyExists,
)
from src.core.security import password_manager

logger = logging.getLogger(__name__)


class UserService:
    """Handles all user-related business logic."""

    def __init__(self):
        """
        Initializes the UserService.
        This version has no arguments, making it easy for FastAPI to use,
        while still allowing for dependency injection during tests.
        """
        self.user_repository = user_repository
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _check_authorization(
        self, *, current_user: User, target_user: User, action: str
    ) -> None:
        """
        Central authorization check. An admin can do anything.
        A non-admin can only perform actions on their own account.

        Args:
            current_user: The user performing the action
            target_user: The user being acted upon
            action: Description of the action for error messages

        Raises:
            NotAuthorized: If user lacks permission for the action
        """
        # Users can only modify their own account
        # Admins have super powers
        if current_user.is_admin:
            return

        is_not_self = str(current_user.id) != str(target_user.id)
        raise_for_status(
            condition=is_not_self,
            exception=NotAuthorized,
            detail=f"You are not authorized to {action} this user.",
        )

    async def get_user_for_auth(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> Optional[User]:
        """
        A simplified user retrieval method for authentication purposes, using a
        cache-aside pattern.
        """

        return await self.user_repository.get(db=db, obj_id=user_id)

    async def get_user_by_id(
        self, db: AsyncSession, *, user_id: uuid.UUID, current_user: User
    ) -> Optional[User]:
        """get user by it's ID"""

        user = await self.user_repository.get(db=db, obj_id=user_id)
        raise_for_status(
            condition=(user is None),
            exception=ResourceNotFound,
            detail=f"User with id: {user_id} not found",
            resource_type="User",
        )

        # Fine-grained authorization check
        if current_user.is_admin:
            return user
        is_not_self = current_user.id != user.id

        raise_for_status(
            condition=(is_not_self),
            exception=NotAuthorized,
            detail="You are not authorized to view this user's profile.",
        )

        self._logger.debug(f"User {user_id} retrieved by user {current_user.id}")
        return user

    async def get_users(
        self,
        *,
        db: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> UserListResponse:
        """
        Lists users with pagination and filtering.

        Args:
            db: Database session
            current_user: User making the request
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            order_by: Field to order by
            order_desc: Whether to order in descending order

        Returns:
            UserListResponse: Paginated list of users

        Raises:
            NotAuthorized: If user lacks permission to list users
            ValidationError: If pagination parameters are invalid
        """
        # Input validation
        if skip < 0:
            raise ValidationError("Skip parameter must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")

        # Delegate fetching to the repository
        users, total = await self.user_repository.get_all(
            db=db,
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order_desc=order_desc,
        )

        # Calculate pagination info
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit  # Ceiling division

        # Construct the response schema
        response = UserListResponse(
            items=users, total=total, page=page, pages=total_pages, size=limit
        )

        self._logger.info(
            f"User list retrieved by {current_user.id}: {len(users)} users returned"
        )
        return response

    async def create_user(
        self,
        db: AsyncSession,
        *,
        user_in: UserCreate,
        current_user: User,
    ) -> User:
        """
        Handles the business logic of creating a new user with strict RBAC.
        """
        # 1. RBAC SECURITY CHECK
        if not current_user.is_admin:
            if current_user.role.priority <= user_in.role.priority:
                raise NotAuthorized(
                    f"You are not authorized to create a user with role '{user_in.role.value}'."
                )

        # 2. Check for Email Conflicts
        existing_user = await self.user_repository.get_by_email(
            db=db, email=user_in.email
        )
        raise_for_status(
            condition=existing_user is not None,
            exception=ResourceAlreadyExists,
            detail=f"User with email '{user_in.email}' already exists.",
            resource_type="User",
        )

        existing_user_code = await self.user_repository.get_by_user_code(
            db=db, user_code=user_in.user_code
        )
        raise_for_status(
            condition=existing_user_code is not None,
            exception=ResourceAlreadyExists,
            detail=f"User with user_code '{user_in.user_code}' already exists.",
            resource_type="User",
        )

        # 3. Prepare the user model
        user_dict = user_in.model_dump()
        password = user_dict.pop("password")

        # Hash the password
        user_dict["hashed_password"] = password_manager.hash_password(password)

        # Set Timestamps
        now = datetime.now(timezone.utc)
        user_dict["created_at"] = now
        user_dict["updated_at"] = now
        user_dict["tokens_valid_from_utc"] = now

        user_to_create = User(**user_dict)

        # 4. Delegate creation to the repository
        new_user = await self.user_repository.create(db=db, db_obj=user_to_create)

        # self._logger.info(
        #     f"User {new_user.id} ({new_user.role}) created by {current_user.id}"
        # )

        return new_user

    async def update_user_admin(
        self,
        db: AsyncSession,
        *,
        user_id_to_update: uuid.UUID,
        user_data: UserUpdateAdmin,
        current_user: User,
    ) -> User:
        """Updates a user after performing necessary authorization checks."""

        user_to_update = await self.user_repository.get(db=db, obj_id=user_id_to_update)

        raise_for_status(
            condition=(user_to_update is None),
            exception=ResourceNotFound,
            detail=f"User not Found",
            resource_type="User",
        )

        self._check_authorization(
            current_user=current_user, target_user=user_to_update, action="update"
        )

        update_dict = user_data.model_dump(exclude_unset=True, exclude_none=True)

        # Remove timestamp fields that should not be manually updated
        for ts_field in {"created_at", "updated_at"}:
            update_dict.pop(ts_field, None)

        updated_user = await self.user_repository.update(
            db=db,
            user=user_to_update,
            fields_to_update=update_dict,
        )

        self._logger.info(
            f"User {user_id_to_update} updated by {current_user.id}",
            extra={
                "updated_user_id": user_id_to_update,
                "updater_id": current_user.id,
                "updated_fields": list(update_dict.keys()),
            },
        )
        return updated_user

    async def update_user_profile(
        self,
        db: AsyncSession,
        *,
        user_id_to_update: uuid.UUID,
        user_data: UserUpdateProfile,
        current_user: User,
    ) -> User:
        """Updates a user after performing necessary authorization checks."""

        user_to_update = await self.user_repository.get(db=db, obj_id=user_id_to_update)

        raise_for_status(
            condition=(user_to_update is None),
            exception=ResourceNotFound,
            detail=f"User not Found",
            resource_type="User",
        )

        self._check_authorization(
            current_user=current_user, target_user=user_to_update, action="update"
        )

        update_dict = user_data.model_dump(exclude_unset=True, exclude_none=True)

        # Remove timestamp fields that should not be manually updated
        for ts_field in {"created_at", "updated_at"}:
            update_dict.pop(ts_field, None)

        updated_user = await self.user_repository.update(
            db=db,
            user=user_to_update,
            fields_to_update=update_dict,
        )

        self._logger.info(
            f"User {user_id_to_update} updated by {current_user.id}",
            extra={
                "updated_user_id": user_id_to_update,
                "updater_id": current_user.id,
                "updated_fields": list(update_dict.keys()),
            },
        )
        return updated_user

    async def delete_user(
        self, db: AsyncSession, *, user_id_to_delete: uuid.UUID, current_user: User
    ) -> Dict[str, str]:
        """
        Permanently deletes a user account.

        Args:
            db: Database session
            user_id_to_delete: ID of user to delete
            current_user: User making the request

        Returns:
            Dict with success message

        Raises:
            ResourceNotFound: If user doesn't exist
        """
        # Input validation

        # 1. Fetch the user to delete
        user_to_delete = await self.user_repository.get(db=db, obj_id=user_id_to_delete)

        raise_for_status(
            condition=(user_to_delete is None),
            exception=ResourceNotFound,
            detail=f"User with id {user_id_to_delete} not Found",
            resource_type="User",
        )

        # 2. Perform authorization check
        self._check_authorization(
            current_user=current_user,
            target_user=user_to_delete,
            action="delete",
        )

        await self._validate_user_deletion(
            db=db, current_user=current_user, user_to_delete=user_to_delete
        )

        # 3. Perform the deletion
        await self.user_repository.delete(db=db, obj_id=user_id_to_delete)

        self._logger.warning(
            f"User {user_id_to_delete} permanently deleted by {current_user.id}",
            extra={
                "deleted_user_id": user_id_to_delete,
                "deleter_id": current_user.id,
                "deleted_user_email": user_to_delete.email,
            },
        )
        return {"message": "User has been successfully deleted!"}

    async def deactivate_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, current_user: User
    ) -> User:
        """Deactivate a user by it's ID"""

        user_to_deactivate = await self.get_user_by_id(
            db=db, current_user=current_user, user_id=user_id
        )

        self._check_authorization(
            current_user=current_user,
            target_user=user_to_deactivate,
            action="deactivate",
        )

        # 3. Check if user is already deactivated
        raise_for_status(
            condition=(user_to_deactivate.status == UserStatus.INACTIVE),
            exception=ValidationError,  # Or a more specific BadRequestException
            detail="User is already inactive.",
        )

        # 4. Prevent self-deactivation for admins (business rule)
        if current_user.id == user_id and current_user.is_admin:
            raise ValidationError("Administrators cannot deactivate their own accounts")

        # 5. Update user status
        deactivated_user = await self.user_repository.update(
            db=db,
            user=user_to_deactivate,
            fields_to_update={"status": UserStatus.INACTIVE},
        )

        self._logger.info(
            f"User {user_id} deactivated by {current_user.id}",
            extra={
                "deactivated_user_id": user_id,
                "deactivator_id": current_user.id,
            },
        )
        return deactivated_user

    async def activate_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, current_user: User
    ) -> User:
        """activate a user by it's iD"""
        user_to_activate = await self.get_user_by_id(
            db=db, current_user=current_user, user_id=user_id
        )

        self._check_authorization(
            current_user=current_user,
            target_user=user_to_activate,
            action="activate",
        )

        # 3. Check if user is already deactivated
        raise_for_status(
            condition=(user_to_activate.status == UserStatus.ACTIVE),
            exception=ValidationError,  # Or a more specific BadRequestException
            detail="User is already active.",
        )

        # 5. Update user status
        activated_user = await self.user_repository.update(
            db=db,
            user=user_to_activate,
            fields_to_update={"status": UserStatus.ACTIVE},
        )

        self._logger.info(
            f"User {user_id} deactivated by {current_user.id}",
            extra={
                "activated_user_id": user_id,
                "activator_id": current_user.id,
            },
        )
        return activated_user

    async def change_role(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        new_role: UserRole,
        current_user: User,
    ) -> User:
        """Update a user's Role"""

        raise_for_status(
            condition=(user_id == current_user.id),
            exception=ValidationError,
            detail="Administrators cannot change their own role.",
        )

        user = await self.get_user_by_id(
            db=db, current_user=current_user, user_id=user_id
        )

        updated_user = await self.user_repository.update(
            db=db, user=user, fields_to_update={"role": new_role}
        )

        self._logger.info(
            f"User {user_id} role changed to {new_role.value} by {current_user.id}"
        )
        return updated_user

    async def _validate_user_deletion(
        self, db: AsyncSession, user_to_delete: User, current_user: User
    ) -> None:
        """
        Validates user deletion for business rules.

        Args:
            db: Database session
            user_to_delete: User to be deleted
            current_user: User performing the deletion

        Raises:
            ValidationError: If deletion violates business rules
        """
        # Prevent self-deletion
        if current_user.id == user_to_delete.id:
            raise ValidationError("Users cannot delete their own accounts")

        # Prevent deletion of the last admin
        if user_to_delete.is_admin:
            admin_count = await self.user_repository.count(
                db=db, filters={"role": UserRole.ADMIN, "status": UserStatus.ACTIVE}
            )
            if admin_count <= 1:
                raise ValidationError(
                    "Cannot delete the last active administrator account"
                )

        return {"message": "User deleted successfully"}


user_service = UserService()
