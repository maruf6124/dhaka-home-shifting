"""Live chat: WebSocket for real time + REST for history and as a fallback.

Messages are always saved to the database before they are pushed, so nothing
is lost when the free Render server sleeps and the socket drops; the client
reconnects and loads missed messages from /history.
"""
import asyncio
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db, utcnow
from app.core.deps import ACCESS_COOKIE, get_verified_user
from app.core.errors import AppError
from app.core.security import decode_token
from app.models import ChatParticipant, ChatRoom, Message, User
from app.schemas import MessageIn
from app.services.email import send_email
from app.services.listings import get_listing
from app.services.notify import notify

router = APIRouter(tags=["chat"])
settings = get_settings()
EMAIL_EVERY = timedelta(minutes=10)
MAX_PER_MINUTE = 20


class ConnectionManager:
    """In-memory (single server instance, enough for the free tier)."""

    def __init__(self) -> None:
        self.rooms: dict[int, dict[int, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))

    def add(self, room_id: int, user_id: int, ws: WebSocket) -> None:
        self.rooms[room_id][user_id].add(ws)

    def remove(self, room_id: int, user_id: int, ws: WebSocket) -> None:
        self.rooms[room_id][user_id].discard(ws)

    def online(self, room_id: int, user_id: int) -> bool:
        return bool(self.rooms.get(room_id, {}).get(user_id))

    async def broadcast(self, room_id: int, payload: dict) -> None:
        for sockets in list(self.rooms.get(room_id, {}).values()):
            for ws in list(sockets):
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass


manager = ConnectionManager()


def _msg(m: Message) -> dict:
    return {"id": m.id, "room_id": m.room_id, "sender_id": m.sender_id, "body": m.body, "created_at": m.created_at.isoformat()}


async def _participant(db: AsyncSession, room_id: int, user_id: int) -> tuple[ChatRoom, ChatParticipant, ChatParticipant]:
    room = await db.get(ChatRoom, room_id)
    if room is None:
        raise AppError("not_found", 404)
    me = next((p for p in room.participants if p.user_id == user_id), None)
    other = next((p for p in room.participants if p.user_id != user_id), None)
    if me is None or other is None:
        raise AppError("forbidden", 403)
    return room, me, other


async def save_message(db: AsyncSession, room_id: int, user: User, body: str, background: BackgroundTasks | None) -> Message:
    body = body.strip()
    if not body or len(body) > 2000:
        raise AppError("invalid", 422)
    room, me, other = await _participant(db, room_id, user.id)
    if me.has_blocked or other.has_blocked:
        raise AppError("blocked", 403)
    recent = await db.scalar(select(func.count()).select_from(Message).where(
        Message.sender_id == user.id, Message.created_at >= utcnow() - timedelta(minutes=1)))
    if recent >= MAX_PER_MINUTE:
        raise AppError("rate_limited", 429)
    msg = Message(room_id=room_id, sender_id=user.id, body=body)
    db.add(msg)
    me.last_read_at = utcnow()
    # Notify the other side; email only if they are offline and not emailed recently.
    receiver = await db.get(User, other.user_id)
    if not manager.online(room_id, other.user_id):
        await notify(db, receiver, "new_message", f"{user.name}: {body[:80]}", f"/messages/{room_id}")
        if other.last_emailed_at is None or other.last_emailed_at < utcnow() - EMAIL_EVERY:
            other.last_emailed_at = utcnow()
            args = (receiver.email, "new_message", receiver.language)
            kwargs = {"sender": user.name, "preview": body[:140], "link": f"{settings.frontend_url}/messages/{room_id}"}
            if background is not None:
                background.add_task(send_email, *args, **kwargs)
            else:
                asyncio.get_running_loop().run_in_executor(None, lambda: send_email(*args, **kwargs))
    await db.commit()
    return msg


@router.get("/chat/rooms")
async def rooms(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    my_rooms = (await db.execute(
        select(ChatRoom).join(ChatParticipant).where(ChatParticipant.user_id == user.id)
    )).scalars().unique().all()
    out = []
    for room in my_rooms:
        me = next(p for p in room.participants if p.user_id == user.id)
        other = next((p for p in room.participants if p.user_id != user.id), None)
        other_user = await db.get(User, other.user_id) if other else None
        last = (await db.execute(select(Message).where(Message.room_id == room.id).order_by(Message.id.desc()).limit(1))).scalar_one_or_none()
        unread = await db.scalar(select(func.count()).select_from(Message).where(
            Message.room_id == room.id, Message.sender_id != user.id,
            Message.created_at > (me.last_read_at or room.created_at - timedelta(seconds=1))))
        try:
            listing = await get_listing(db, room.listing_type, room.listing_id)
            title, owner_id = listing.title, listing.owner_id
        except AppError:
            title, owner_id = "—", None
        out.append({
            "id": room.id, "listing_type": room.listing_type, "listing_id": room.listing_id, "listing_title": title,
            "i_am_owner": owner_id == user.id,
            "other": {"id": other_user.id, "name": other_user.name} if other_user else None,
            "last_message": _msg(last) if last else None, "unread": unread,
            "blocked": me.has_blocked, "blocked_by_other": bool(other and other.has_blocked),
            "updated_at": (last.created_at if last else room.created_at).isoformat(),
        })
    out.sort(key=lambda r: r["updated_at"], reverse=True)
    return out


@router.get("/chat/rooms/{room_id}/messages")
async def history(room_id: int, before_id: int | None = None, limit: int = Query(default=50, le=100),
                  user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    await _participant(db, room_id, user.id)
    q = select(Message).where(Message.room_id == room_id)
    if before_id:
        q = q.where(Message.id < before_id)
    rows = (await db.execute(q.order_by(Message.id.desc()).limit(limit))).scalars().all()
    return [_msg(m) for m in reversed(rows)]


@router.post("/chat/rooms/{room_id}/messages", status_code=201)
async def post_message(room_id: int, data: MessageIn, background: BackgroundTasks,
                       user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    msg = await save_message(db, room_id, user, data.body, background)
    payload = {"type": "message", "message": _msg(msg)}
    await manager.broadcast(room_id, payload)
    return payload["message"]


@router.post("/chat/rooms/{room_id}/read")
async def mark_read(room_id: int, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    _, me, _ = await _participant(db, room_id, user.id)
    me.last_read_at = utcnow()
    await db.commit()
    return {"status": "ok"}


@router.post("/chat/rooms/{room_id}/block")
async def block(room_id: int, blocked: bool = True, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    _, me, _ = await _participant(db, room_id, user.id)
    me.has_blocked = blocked
    await db.commit()
    return {"blocked": blocked}


@router.websocket("/ws/chat/{room_id}")
async def chat_socket(ws: WebSocket, room_id: int, token: str | None = None):
    token = token or ws.cookies.get(ACCESS_COOKIE)
    user_id = decode_token(token, "access") if token else None
    if user_id is None:
        await ws.close(code=4401)
        return
    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        try:
            if user is None or user.is_banned or user.email_verified_at is None:
                raise AppError("forbidden", 403)
            await _participant(db, room_id, user_id)
        except AppError:
            await ws.close(code=4403)
            return
    await ws.accept()
    manager.add(room_id, user_id, ws)
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
                continue
            if data.get("type") != "message":
                continue
            async with SessionLocal() as db:
                user = await db.get(User, user_id)
                try:
                    msg = await save_message(db, room_id, user, str(data.get("body", "")), None)
                except AppError as err:
                    await ws.send_json({"type": "error", "code": err.code})
                    continue
            await manager.broadcast(room_id, {"type": "message", "message": _msg(msg), "client_id": data.get("client_id")})
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(room_id, user_id, ws)
