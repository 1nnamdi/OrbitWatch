"""Basemap tile proxy — corporate filters block direct <img> tile loads."""
import httpx
from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/tiles", tags=["tiles"])

TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"

_cache: dict[tuple[int, int, int], bytes] = {}
_CACHE_MAX = 2000


@router.get("/{z}/{x}/{y}.png")
async def tile(z: int, x: int, y: int):
    key = (z, x, y)
    if key not in _cache:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(TILE_URL.format(z=z, x=x, y=y))
        if r.status_code != 200:
            raise HTTPException(r.status_code)
        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = r.content
    return Response(
        content=_cache[key],
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
