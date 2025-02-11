from jose import jwt, JWTError
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import redis as redis_db
import pickle 


from app.database.db import get_db
from  app.repository import users  as repository_users
from   app.conf.config import  settings

class Auth :
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = settings.secret_key
    ALGORITHM = settings.algorithm
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
    r = redis_db.Redis(host=settings.redis_host, port=settings.redis_port, db=0)

    def verify_password(self, plain_password, hashed_password):
       
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str):
       
        return self.pwd_context.hash(password)
    
    #  функ. для создания нового токена доступа
    async def create_access_token(self, data: dict, expires_delta: Optional[float] = None):
        
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": "access_token"})
        encoded_access_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_access_token
    
    # создания токен обновлениe
    async def create_refresh_token(self, data: dict, expires_delta: Optional[float] = None):
      
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": "refresh_token"})
        encoded_refresh_token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_refresh_token
    
    async def decode_refresh_token(self, refresh_token: str):
        
        try:
            payload = jwt.decode(refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] == 'refresh_token':
                email = payload['sub']
                return email
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid scope for token (Неверная область действия токена)')
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials (Не удалось проверить учетные данные)')
        
    async def get_current_user(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
     
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials (Не удалось проверить учетные данные)",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            # Декодировать JWT
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload['scope'] == 'access_token':
                email = payload["sub"]
                if email is None:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception

        user = await repository_users.get_user_by_email(email, db)
        if user is None:
            raise credentials_exception
        user = self.r.get(f"user:{email}")
        if user is None:
            user = await repository_users.get_user_by_email(email, db)
            if user is None:
                raise credentials_exception
            self.r.set(f"user:{email}", pickle.dumps(user))
            self.r.expire(f"user:{email}", 900)
        else:
            user = pickle.loads(user)
        return user
    
   
    def create_email_token(self, data: dict):
  
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return token
    
    async def get_email_from_token(self, token: str):
   
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email = payload["sub"]
            return email
        except JWTError as e:
            print(e)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                          detail="Invalid token for email verification")


auth_service = Auth()
