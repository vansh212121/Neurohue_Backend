from fastapi import APIRouter, Depends
from src.utils.deps import get_current_user
from src.schemas.user_schema import UserPayload

router = APIRouter()

@router.get("/test-token")
async def test_token_decoding(
    current_user: UserPayload = Depends(get_current_user)
):
    """
    If you see a response here, it means:
    1. The Token was valid.
    2. The Secret Key matches Auth Service.
    3. The Role and ID were extracted correctly.
    """
    return {
        "status": "Success",
        "verified_data": {
            "user_id": current_user.id,
            "role": current_user.role
        },
        "message": "Org Service trusts this user!"
    }