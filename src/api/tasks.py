# Task ID: T034-T036, T040-T042, T049-T052, T056-T058, T062-T064 - Tasks CRUD endpoints
"""Tasks API router.

Per Constitution Principle III: Security-First Design
- user_id derived ONLY from JWT claims
- Tasks filtered by user_id for data isolation

Per FR-009 through FR-018:
- POST /tasks: Create task with title validation
- GET /tasks: List tasks ordered by created_at DESC
- PATCH /tasks/{taskId}: Update task (title, description, is_completed)
- DELETE /tasks/{taskId}: Permanently delete task
- POST /tasks/{taskId}/complete: Mark task as complete
- DELETE /tasks/{taskId}/complete: Mark task as incomplete
"""

from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.session import get_session
from src.models.task import Task, TaskCreate, TaskUpdate, TaskRead
from src.api.deps import CurrentUserId

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_session)]


class ValidationError(HTTPException):
    """Custom exception for validation failures."""

    def __init__(self, message: str, field: str, constraint: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "details": {"field": field, "constraint": constraint},
                }
            },
        )


class NotFoundError(HTTPException):
    """Custom exception for not found resources."""

    def __init__(self, message: str = "Task not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": message}},
        )


# ============================================
# T034-T036: POST /tasks - Create Task (US3)
# ============================================


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    user_id: CurrentUserId,
    session: DbSession,
) -> Task:
    """Create a new task for the authenticated user.

    Task ID: T034 - POST /api/v1/tasks endpoint
    Task ID: T035 - Title validation (1-200 chars, required)
    Task ID: T036 - Associate task with user_id from JWT

    Per FR-009: System creates task when user submits valid title
    Per FR-010: Title required (1-200 chars), description optional
    Per FR-020: user_id derived exclusively from JWT token

    Args:
        task_data: Task creation payload (title required, description optional)
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        Created task with id, timestamps

    Raises:
        HTTPException 400: If title validation fails
        HTTPException 401: If not authenticated
    """
    # T035: Title validation is handled by Pydantic model (min_length=1, max_length=200)
    # Additional explicit validation for better error messages
    if not task_data.title or not task_data.title.strip():
        raise ValidationError("Title is required", "title", "required")

    if len(task_data.title) > 200:
        raise ValidationError("Title must be 1-200 characters", "title", "length")

    # T036: Create task with user_id from JWT
    task = Task(
        title=task_data.title.strip(),
        description=task_data.description,
        user_id=user_id,  # From JWT only
        is_completed=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(task)
    await session.flush()
    await session.refresh(task)

    return task


# ============================================
# T040-T042: GET /tasks - List Tasks (US4)
# ============================================


@router.get("", response_model=List[TaskRead])
async def list_tasks(
    user_id: CurrentUserId,
    session: DbSession,
) -> List[Task]:
    """Get all tasks for the authenticated user.

    Task ID: T040 - GET /api/v1/tasks endpoint
    Task ID: T041 - Filter tasks by user_id from JWT (data isolation)
    Task ID: T042 - Order tasks by created_at DESC (newest first)

    Per FR-011: System retrieves all tasks owned by authenticated user
    Per FR-012: Tasks displayed in chronological order (newest first)
    Per FR-020: user_id derived exclusively from JWT token

    Args:
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        List of tasks owned by the user, ordered by created_at DESC

    Raises:
        HTTPException 401: If not authenticated
    """
    # T041: Filter by user_id, T042: Order by created_at DESC
    statement = (
        select(Task)
        .where(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
    )

    result = await session.execute(statement)
    tasks = result.scalars().all()

    return list(tasks)


# ============================================
# Helper: Get task with ownership verification
# ============================================


async def get_task_with_ownership(
    task_id: int,
    user_id: str,
    session: AsyncSession,
) -> Task:
    """Get a task and verify ownership.

    Per FR-014, FR-016, FR-018: Verify task ownership before operations
    Per security: Return 404 (not 403) to prevent enumeration attacks

    Args:
        task_id: Task ID to retrieve
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        Task if found and owned by user

    Raises:
        NotFoundError: If task not found or not owned by user
    """
    statement = select(Task).where(Task.id == task_id)
    result = await session.execute(statement)
    task = result.scalars().first()

    # T051, T058, T064: Return 404 if not found OR not owned (prevents enumeration)
    if not task or task.user_id != user_id:
        raise NotFoundError("Task not found")

    return task


# ============================================
# T049-T052: PATCH /tasks/{taskId} - Update Task (US5)
# ============================================


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    user_id: CurrentUserId,
    session: DbSession,
) -> Task:
    """Update a task.

    Task ID: T049 - PATCH /api/v1/tasks/{taskId} endpoint
    Task ID: T050 - Verify task ownership before update
    Task ID: T051 - Return 404 if task not found or not owned
    Task ID: T052 - Update updated_at timestamp on modification

    Per FR-013: Allow updating title, description, or completion status
    Per FR-014: Validate ownership before update
    Per FR-020: user_id derived exclusively from JWT token

    Args:
        task_id: ID of the task to update
        task_data: Update payload (all fields optional)
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        Updated task

    Raises:
        HTTPException 400: If validation fails
        HTTPException 401: If not authenticated
        HTTPException 404: If task not found or not owned
    """
    # T050: Verify ownership
    task = await get_task_with_ownership(task_id, user_id, session)

    # Apply updates (only non-None fields)
    update_data = task_data.model_dump(exclude_unset=True)

    if not update_data:
        # No updates provided, return task as-is
        return task

    # Validate title if provided
    if "title" in update_data:
        title = update_data["title"]
        if not title or not title.strip():
            raise ValidationError("Title is required", "title", "required")
        if len(title) > 200:
            raise ValidationError("Title must be 1-200 characters", "title", "length")
        update_data["title"] = title.strip()

    for field, value in update_data.items():
        setattr(task, field, value)

    # T052: Update timestamp on modification
    task.updated_at = datetime.utcnow()

    session.add(task)
    await session.flush()
    await session.refresh(task)

    return task


# ============================================
# T056-T058: DELETE /tasks/{taskId} - Delete Task (US6)
# ============================================


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    user_id: CurrentUserId,
    session: DbSession,
) -> None:
    """Permanently delete a task.

    Task ID: T056 - DELETE /api/v1/tasks/{taskId} endpoint
    Task ID: T057 - Verify task ownership before delete
    Task ID: T058 - Return 404 if task not found or not owned

    Per FR-015: Allow users to delete their tasks
    Per FR-016: Verify ownership before deletion
    Per clarification: Deletion is permanent (no soft delete)

    Args:
        task_id: ID of the task to delete
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        None (204 No Content)

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If task not found or not owned
    """
    # T057: Verify ownership
    task = await get_task_with_ownership(task_id, user_id, session)

    # Permanent deletion per clarification
    await session.delete(task)
    await session.flush()


# ============================================
# T062-T064: POST/DELETE /tasks/{taskId}/complete - Toggle Completion (US7)
# ============================================


@router.post("/{task_id}/complete", response_model=TaskRead)
async def complete_task(
    task_id: int,
    user_id: CurrentUserId,
    session: DbSession,
) -> Task:
    """Mark a task as complete.

    Task ID: T062 - POST /api/v1/tasks/{taskId}/complete endpoint
    Task ID: T064 - Verify task ownership for complete

    Per FR-017: Allow users to toggle task completion status

    Args:
        task_id: ID of the task to complete
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        Updated task with is_completed=True

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If task not found or not owned
    """
    # T064: Verify ownership
    task = await get_task_with_ownership(task_id, user_id, session)

    task.is_completed = True
    task.updated_at = datetime.utcnow()

    session.add(task)
    await session.flush()
    await session.refresh(task)

    return task


@router.delete("/{task_id}/complete", response_model=TaskRead)
async def uncomplete_task(
    task_id: int,
    user_id: CurrentUserId,
    session: DbSession,
) -> Task:
    """Mark a task as incomplete.

    Task ID: T063 - DELETE /api/v1/tasks/{taskId}/complete endpoint
    Task ID: T064 - Verify task ownership for incomplete

    Per FR-017: Allow users to toggle task completion status

    Args:
        task_id: ID of the task to mark incomplete
        user_id: Authenticated user ID from JWT
        session: Database session

    Returns:
        Updated task with is_completed=False

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If task not found or not owned
    """
    # T064: Verify ownership
    task = await get_task_with_ownership(task_id, user_id, session)

    task.is_completed = False
    task.updated_at = datetime.utcnow()

    session.add(task)
    await session.flush()
    await session.refresh(task)

    return task
