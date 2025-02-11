from typing import List
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, or_, select

from app.database.models import   User, Image

from app.schemas.photo_tags import  PhotoModels, PhotoBase



async def get_photos(  skip: int, limit: int,user: User, db: Session) -> List[Image]:
    return db.query(Image).offset(skip).limit(limit).filter(Image.user_id == user.id).all()

    

async def get_photo(photo_id: int, user: User, db: Session):
    photo = db.query(Image).filter_by(and_(Image.id == photo_id, Image.user_id == user.id)).first()
    return photo




async def add_photo(  body: PhotoModels, user: User, db: Session, url:str) -> Image:
    photo = Image( description=body.description, image=body.name,  tags=body.tags, user_id=user.id, user=user.username, url= url)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo



async def update_description( photo_id: int, body: PhotoModels, user: User, db: Session) -> Image | None:
    photo = db.query(Image).filter_by(id=photo_id).first()
    if photo:
        photo.description = body.description
        db.commit()
    return photo


async def remove_photo( photo_id: int, user: User, db: Session) -> Image | None:
    photo = db.query(Image).filter(and_(Image.id == photo_id, Image.user_id == user.id)).first()
    if photo:
        db.delete(photo)
        db.commit()
    return photo
