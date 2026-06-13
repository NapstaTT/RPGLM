"""
FastAPI router for lorebook endpoints using the three managers.
"""

from fastapi import APIRouter, HTTPException, Request
from .location import LocationManager
from .character import CharacterManager
from .entry import EntryManager

router = APIRouter(prefix="/lorebook", tags=["lorebook"])


def get_managers(request: Request):
    return request.app.state.lorebook_managers


@router.get("/locations")
async def get_locations(request: Request):
    return await get_managers(request)["locations"].get_all()

@router.post("/locations")
async def create_location(data: dict, request: Request):
    try:
        return await get_managers(request)["locations"].create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.put("/locations/{loc_id}")
async def update_location(loc_id: str, data: dict, request: Request):
    try:
        return await get_managers(request)["locations"].update(loc_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.delete("/locations/{loc_id}")
async def delete_location(loc_id: str, request: Request):
    try:
        await get_managers(request)["locations"].delete(loc_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))


# Characters
@router.get("/characters")
async def get_characters(request: Request):
    return await get_managers(request)["characters"].get_all()


@router.post("/characters")
async def create_character(data: dict, request: Request):
    try:
        return await get_managers(request)["characters"].create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/characters/{char_id}")
async def update_character(char_id: str, data: dict, request: Request):
    try:
        return await get_managers(request)["characters"].update(char_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/characters/{char_id}")
async def delete_character(char_id: str, request: Request):
    try:
        await get_managers(request)["characters"].delete(char_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))


# Entries
@router.get("/entries")
async def get_entries(request: Request):
    return await get_managers(request)["entries"].get_all()


@router.post("/entries")
async def create_entry(data: dict, request: Request):
    try:
        return await get_managers(request)["entries"].create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, data: dict, request: Request):
    try:
        return await get_managers(request)["entries"].update(entry_id, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str, request: Request):
    try:
        await get_managers(request)["entries"].delete(entry_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))


# Additional location-specific endpoints
@router.post("/locations/{loc_id}/characters/{char_id}")
async def add_character_to_location(loc_id: str, char_id: str, request: Request):
    try:
        await get_managers(request)["locations"].add_character_to_location(loc_id, char_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/locations/{loc_id}/characters/{char_id}")
async def remove_character_from_location(loc_id: str, char_id: str, request: Request):
    try:
        await get_managers(request)["locations"].remove_character_from_location(loc_id, char_id)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(400, str(e))