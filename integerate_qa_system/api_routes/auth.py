from fastapi import APIRouter, Depends, HTTPException

from .shared import LoginRequest, LoginResponse, SendCodeRequest, auth_service, email_service, get_current_user, qa_system, redis_client


router = APIRouter()


@router.post("/send-verification-code")
async def send_verification_code(request: SendCodeRequest):
    email = request.email.strip()

    if not email:
        raise HTTPException(status_code=400, detail="邮箱地址不能为空")

    code = email_service.generate_verification_code()
    success = email_service.send_verification_code(email, code)

    if not success:
        print(f"\n{'=' * 50}")
        print(f"[开发模式] 验证码: {code} (邮箱: {email})")
        print(f"{'=' * 50}\n")
        qa_system.logger.warning(f"邮件发送失败，验证码已打印到控制台: {code}")

    redis_key = f"verification_code:{email}"
    redis_client.client.setex(redis_key, 300, code)

    return {"message": "验证码已发送，请查收邮件（如未收到请查看控制台）", "email": email}


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    email = request.email.strip()
    code = request.verification_code.strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="邮箱和验证码不能为空")

    redis_key = f"verification_code:{email}"
    stored_code = redis_client.client.get(redis_key)

    if not stored_code:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")

    if stored_code != code:
        raise HTTPException(status_code=400, detail="验证码错误")

    redis_client.client.delete(redis_key)

    user_id = qa_system.mysql_client.get_or_create_user(email)
    token = auth_service.generate_token(user_id, email)

    return LoginResponse(
        token=token,
        user_id=user_id,
        email=email,
        message="登录成功",
    )


@router.get("/verify-token")
async def verify_token(user: dict = Depends(get_current_user)):
    return {
        "valid": True,
        "user_id": user["user_id"],
        "email": user["email"],
    }
