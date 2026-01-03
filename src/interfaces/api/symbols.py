"""
모니터링 종목 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from ...infrastructure.persistence.database.session import get_db
from ...infrastructure.persistence.database.models import MonitoredSymbolsModel

router = APIRouter()


class SymbolCreate(BaseModel):
    """종목 추가 요청"""
    symbol: str


class SymbolResponse(BaseModel):
    """종목 응답"""
    symbol: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@router.post("/symbols", response_model=SymbolResponse)
async def add_symbol(
    symbol_data: SymbolCreate,
    db: AsyncSession = Depends(get_db),
):
    """모니터링 종목 추가"""
    try:
        # 이미 존재하는지 확인
        result = await db.execute(
            select(MonitoredSymbolsModel).where(
                MonitoredSymbolsModel.symbol == symbol_data.symbol
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 이미 존재하면 활성화
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return SymbolResponse(
                symbol=existing.symbol,
                is_active=existing.is_active,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
            )
        else:
            # 새로 생성
            new_symbol = MonitoredSymbolsModel(
                symbol=symbol_data.symbol,
                is_active=True,
            )
            db.add(new_symbol)
            await db.commit()
            await db.refresh(new_symbol)
            return SymbolResponse(
                symbol=new_symbol.symbol,
                is_active=new_symbol.is_active,
                created_at=new_symbol.created_at,
                updated_at=new_symbol.updated_at,
            )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/symbols/{symbol}")
async def remove_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """모니터링 종목 제거 (비활성화)"""
    try:
        result = await db.execute(
            select(MonitoredSymbolsModel).where(
                MonitoredSymbolsModel.symbol == symbol
            )
        )
        monitored_symbol = result.scalar_one_or_none()
        
        if not monitored_symbol:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
        
        monitored_symbol.is_active = False
        monitored_symbol.updated_at = datetime.utcnow()
        await db.commit()
        
        return {"message": f"종목 {symbol}이(가) 비활성화되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols", response_model=List[SymbolResponse])
async def list_symbols(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """모니터링 종목 목록 조회"""
    try:
        query = select(MonitoredSymbolsModel)
        if active_only:
            query = query.where(MonitoredSymbolsModel.is_active == True)
        
        result = await db.execute(query)
        symbols = result.scalars().all()
        
        return [
            SymbolResponse(
                symbol=s.symbol,
                is_active=s.is_active,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in symbols
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# /v1/symbols는 메인 앱에 직접 등록 (agent.py 또는 main.py에서)


