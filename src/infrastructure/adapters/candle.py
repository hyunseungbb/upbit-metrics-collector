"""
업비트 Candle WebSocket 어댑터
"""
import asyncio
import json
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ...config.logging import logger


class UpbitCandleAdapter:
    """업비트 Candle WebSocket 어댑터"""
    
    WS_URL = "wss://api.upbit.com/websocket/v1"
    
    def __init__(self, unit: int = 1):
        """
        Args:
            unit: 캔들 단위 (1, 3, 5, 15, 30, 60, 240 분)
        """
        self.unit = unit
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribed_symbols: List[str] = []
        self.callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.connected = False
        self.last_data_time: Optional[datetime] = None  # 마지막 데이터 수신 시간
        self.reconnecting = False  # 재연결 중 플래그
        self.reconnect_attempts = 0  # 재연결 시도 횟수
        self.last_reconnect_time: Optional[datetime] = None  # 마지막 재연결 시도 시간
    
    async def connect(self) -> None:
        """WebSocket 연결"""
        try:
            logger.info("Candle WebSocket 연결 시도", url=self.WS_URL, unit=f"{self.unit}분")
            self.websocket = await websockets.connect(
                self.WS_URL,
                ping_interval=20,
                ping_timeout=10,
            )
            self.connected = True
            self.reconnect_attempts = 0  # 연결 성공 시 재시도 횟수 리셋
            logger.info("Candle WebSocket 연결 성공")
        except Exception as e:
            error_str = str(e)
            self.reconnect_attempts += 1
            logger.error("Candle WebSocket 연결 실패", error=error_str, error_type=type(e).__name__, attempts=self.reconnect_attempts)
            
            # HTTP 429 에러인 경우 특별 처리
            if "429" in error_str or "Too Many Requests" in error_str:
                raise Exception(f"WebSocket 연결 실패 (Rate Limit): {error_str}") from e
            raise Exception(f"WebSocket 연결 실패: {error_str}") from e
    
    async def disconnect(self) -> None:
        """WebSocket 연결 해제"""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def subscribe(self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        """Candle 구독"""
        # 재연결 중이면 구독하지 않음
        if self.reconnecting:
            logger.debug("재연결 중이므로 구독 스킵")
            return
        
        if not self.websocket or not self.connected:
            await self.connect()
        
        self.subscribed_symbols = symbols
        self.callback = callback
        
        try:
            # 구독 메시지 생성
            subscribe_message = [
                {"ticket": "upbit-metrics-collector"},
                {
                    "type": "candle",
                    "codes": symbols,
                    "unit": self.unit,  # 분 단위
                },
                {"format": "DEFAULT"}
            ]
            
            message_str = json.dumps(subscribe_message)
            await self.websocket.send(message_str)
            logger.info("Candle 구독 메시지 전송", symbols=symbols, unit=f"{self.unit}분")
            
            # 수신 태스크 시작 (중복 실행 방지)
            if self.receive_task and not self.receive_task.done():
                logger.debug("Candle 수신 루프가 이미 실행 중입니다")
                return
            
            if not self.receive_task or self.receive_task.done():
                self.receive_task = asyncio.create_task(self._receive_loop())
                logger.info("Candle 수신 루프 시작")
            
        except Exception as e:
            logger.error("Candle 구독 실패", error=str(e), symbols=symbols)
            raise Exception(f"구독 실패: {str(e)}") from e
    
    async def _receive_loop(self) -> None:
        """수신 루프"""
        receive_count = 0
        logger.info("Candle 수신 루프 시작")
        while self.connected:
            try:
                if not self.websocket:
                    logger.warning("WebSocket이 None입니다, 루프 종료")
                    break
                    
                message = await self.websocket.recv()
                
                if isinstance(message, bytes):
                    message = message.decode('utf-8')
                
                data = json.loads(message)
                
                if data.get("type") == "candle" and self.callback:
                    receive_count += 1
                    self.last_data_time = datetime.utcnow()
                    symbol = data.get("code")
                    if receive_count % 10 == 0:  # 10개마다 로그
                        logger.debug("Candle 데이터 수신 중", count=receive_count, symbol=symbol)
                    await self.callback(data)
                    
            except ConnectionClosed:
                if not self.reconnecting:  # 이미 재연결 중이 아니면
                    logger.warning("Candle WebSocket 연결 끊김, 재연결 시도")
                    self.connected = False
                    self.reconnecting = True
                    try:
                        # Exponential backoff: 최소 5초, 최대 60초
                        wait_time = min(5 * (2 ** min(self.reconnect_attempts, 4)), 60)
                        logger.debug("재연결 대기", wait_time=wait_time, attempts=self.reconnect_attempts)
                        await asyncio.sleep(wait_time)
                        
                        await self.connect()
                        if self.subscribed_symbols and self.callback:
                            await self.subscribe(self.subscribed_symbols, self.callback)
                        logger.info("Candle WebSocket 재연결 성공")
                        self.reconnecting = False
                    except Exception as e:
                        error_str = str(e)
                        self.reconnect_attempts += 1
                        logger.error("Candle WebSocket 재연결 실패", error=error_str, attempts=self.reconnect_attempts)
                        
                        # HTTP 429 에러인 경우 더 긴 대기
                        if "429" in error_str or "Rate Limit" in error_str:
                            wait_time = 60  # 60초 대기
                            logger.warning("Rate Limit 감지, 60초 대기 후 재시도", wait_time=wait_time)
                        else:
                            wait_time = min(10 * (2 ** min(self.reconnect_attempts, 3)), 60)
                        
                        await asyncio.sleep(wait_time)
                        self.reconnecting = False
                        continue
                else:
                    # 이미 재연결 중이면 대기
                    await asyncio.sleep(5)
                    continue
            except json.JSONDecodeError as e:
                logger.warning("Candle JSON 파싱 오류", error=str(e))
                continue
            except Exception as e:
                logger.error("Candle 수신 루프 오류", error=str(e), error_type=type(e).__name__)
                await asyncio.sleep(1)
        
        logger.info("Candle 수신 루프 종료", total_received=receive_count)
    
    def is_subscribed(self) -> bool:
        """구독 상태 확인"""
        # 재연결 중이면 구독 중으로 간주하지 않음
        if self.reconnecting:
            return False
            
        if not self.connected or not self.websocket:
            return False
        
        # 마지막 데이터 수신 시간이 3분 이내면 구독 중으로 간주 (캔들은 1분마다 오므로 여유있게)
        if self.last_data_time:
            time_since_last = (datetime.utcnow() - self.last_data_time).total_seconds()
            if time_since_last > 180:  # 3분
                logger.debug("Candle 구독 상태 의심", seconds_since_last=time_since_last)
                return False
        
        return True
    
    async def ensure_subscribed(self) -> bool:
        """구독 상태 확인 및 재구독"""
        # 재연결 중이면 재구독 시도하지 않음
        if self.reconnecting:
            return False
            
        # 마지막 재연결 시도로부터 최소 30초 경과했는지 확인
        if self.last_reconnect_time:
            time_since_last_reconnect = (datetime.utcnow() - self.last_reconnect_time).total_seconds()
            if time_since_last_reconnect < 30:
                return True  # 최근에 재연결 시도했으면 스킵
        
        if not self.is_subscribed():
            logger.warning("Candle 구독 상태 확인 실패, 재구독 시도")
            self.last_reconnect_time = datetime.utcnow()
            try:
                if self.subscribed_symbols and self.callback:
                    # 재연결 중 플래그 설정
                    self.reconnecting = True
                    try:
                        await self.subscribe(self.subscribed_symbols, self.callback)
                        logger.info("Candle 재구독 완료")
                        self.reconnecting = False
                        return True
                    except Exception as e:
                        self.reconnecting = False
                        error_str = str(e)
                        # HTTP 429 에러인 경우 더 긴 대기
                        if "429" in error_str or "Rate Limit" in error_str:
                            logger.warning("Rate Limit 감지, 재구독 연기", error=error_str)
                            await asyncio.sleep(60)  # 60초 대기
                        raise
            except Exception as e:
                logger.error("Candle 재구독 실패", error=str(e))
                return False
        return True


