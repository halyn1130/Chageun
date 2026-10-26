"""JWT 검증 — auth-server(Java)가 발급한 토큰을 같은 JWT_SECRET으로 확인한다.

토큰 내용: iss=simple-auth-server, sub=사용자 id, username, exp(1시간)
"""
import os
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET = os.environ["JWT_SECRET"]   # 없으면 서버가 뜨지 않게 해서 설정 누락을 바로 알 수 있게 한다
JWT_ISSUER = "simple-auth-server"

# auto_error=False: 헤더가 없을 때 FastAPI 기본값(403) 대신 명세대로 401을 돌려주기 위해
bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: int
    username: str


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    if cred is None:
        raise unauthorized("로그인이 필요해요.")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISSUER,
                             options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise unauthorized("로그인이 만료됐어요. 다시 로그인해 주세요.")
    except jwt.PyJWTError:
        raise unauthorized("로그인 정보가 올바르지 않아요. 다시 로그인해 주세요.")
    return CurrentUser(id=int(payload["sub"]), username=payload.get("username", ""))
