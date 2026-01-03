"""
업비트 Orderbook WebSocket 어댑터
"""
import asyncio
import json
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ...config.logging import logger


class UpbitOrderbookAdapter:
    """업비트 Orderbook WebSocket 어댑터"""
    
    WS_URL = "wss://api.upbit.com/websocket/v1"
    
    def __init__(self):
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
            logger.info("Orderbook WebSocket 연결 시도", url=self.WS_URL)
            self.websocket = await websockets.connect(
                self.WS_URL,
                ping_interval=20,
                ping_timeout=10,
            )
            self.connected = True
            self.reconnect_attempts = 0
            logger.info("Orderbook WebSocket 연결 성공")
        except Exception as e:
            error_str = str(e)
            self.reconnect_attempts += 1
            logger.error("Orderbook WebSocket 연결 실패", error=error_str, error_type=type(e).__name__, attempts=self.reconnect_attempts)
            if "429" in error_str or "Too Many Requests" in error_str:
                raise Exception(f"WebSocket 연결 실패 (Rate Limit): {error_str}") from e
            raise Exception(f"WebSocket 연결 실패: {error_str}") from e
    
    async def disconnect(self) -> None:
        """WebSocket 연결 해제"""
        logger.info("Orderbook WebSocket 연결 해제")
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
        """Orderbook 구독"""
        if not self.websocket or not self.connected:
            await self.connect()
        
        self.subscribed_symbols = symbols
        self.callback = callback
        
        try:
            # 구독 메시지 생성
            subscribe_message = [
                {"ticket": "upbit-metrics-collector"},
                {
                    "type": "orderbook",
                    "codes": symbols,
                },
                {"format": "DEFAULT"}
            ]
            
            message_str = json.dumps(subscribe_message)
            await self.websocket.send(message_str)
            logger.info("Orderbook 구독 메시지 전송", symbols=symbols)
            
            # 수신 태스크 시작
            if not self.receive_task or self.receive_task.done():
                self.receive_task = asyncio.create_task(self._receive_loop())
                logger.info("Orderbook 수신 루프 시작")
            
        except Exception as e:
            logger.error("Orderbook 구독 실패", error=str(e), symbols=symbols)
            raise Exception(f"구독 실패: {str(e)}") from e
    
    async def _receive_loop(self) -> None:
        """수신 루프"""
        receive_count = 0
        logger.info("Orderbook 수신 루프 시작")
        while self.connected:
            try:
                message = await self.websocket.recv()
                
                if isinstance(message, bytes):
                    message = message.decode('utf-8')
                
                data = json.loads(message)
                
                if data.get("type") == "orderbook" and self.callback:
                    receive_count += 1
                    self.last_data_time = datetime.utcnow()
                    if receive_count % 100 == 0:  # 100개마다 로그
                        logger.debug("Orderbook 데이터 수신 중", count=receive_count)
                    await self.callback(data)
                    
            except ConnectionClosed:
                if not self.reconnecting:
                    logger.warning("Orderbook WebSocket 연결 끊김, 재연결 시도")
                    self.connected = False
                    self.reconnecting = True
                    try:
                        wait_time = min(5 * (2 ** min(self.reconnect_attempts, 4)), 60)
                        await asyncio.sleep(wait_time)
                        await self.connect()
                        if self.subscribed_symbols and self.callback:
                            await self.subscribe(self.subscribed_symbols, self.callback)
                        logger.info("Orderbook WebSocket 재연결 성공")
                        self.reconnecting = False
                    except Exception as e:
                        error_str = str(e)
                        logger.error("Orderbook WebSocket 재연결 실패", error=error_str, attempts=self.reconnect_attempts)
                        if "429" in error_str or "Rate Limit" in error_str:
                            wait_time = 60
                            logger.warning("Rate Limit 감지, 60초 대기", wait_time=wait_time)
                        else:
                            wait_time = min(10 * (2 ** min(self.reconnect_attempts, 3)), 60)
                        await asyncio.sleep(wait_time)
                        self.reconnecting = False
                        continue
                else:
                    await asyncio.sleep(5)
                    continue
            except json.JSONDecodeError as e:
                logger.warning("Orderbook JSON 파싱 오류", error=str(e))
                continue
            except Exception as e:
                logger.error("Orderbook 수신 루프 오류", error=str(e), error_type=type(e).__name__)
                await asyncio.sleep(1)
        
        logger.info("Orderbook 수신 루프 종료", total_received=receive_count)
    
    def is_subscribed(self) -> bool:
        """구독 상태 확인"""
        if not self.connected or not self.websocket:
            return False
        
        # 마지막 데이터 수신 시간이 30초 이내면 구독 중으로 간주
        if self.last_data_time:
            time_since_last = (datetime.utcnow() - self.last_data_time).total_seconds()
            if time_since_last > 30:
                logger.warning("Orderbook 구독 상태 의심", seconds_since_last=time_since_last)
                return False
        
        return True
    
    async def ensure_subscribed(self) -> bool:
        """구독 상태 확인 및 재구독"""
        if self.reconnecting:
            return False
            
        if self.last_reconnect_time:
            time_since_last_reconnect = (datetime.utcnow() - self.last_reconnect_time).total_seconds()
            if time_since_last_reconnect < 30:
                return True
        
        if not self.is_subscribed():
            logger.warning("Orderbook 구독 상태 확인 실패, 재구독 시도")
            self.last_reconnect_time = datetime.utcnow()
            try:
                if self.subscribed_symbols and self.callback:
                    self.reconnecting = True
                    try:
                        await self.subscribe(self.subscribed_symbols, self.callback)
                        logger.info("Orderbook 재구독 완료")
                        self.reconnecting = False
                        return True
                    except Exception as e:
                        self.reconnecting = False
                        error_str = str(e)
                        if "429" in error_str or "Rate Limit" in error_str:
                            logger.warning("Rate Limit 감지, 재구독 연기", error=error_str)
                            await asyncio.sleep(60)
                        raise
            except Exception as e:
                logger.error("Orderbook 재구독 실패", error=str(e))
                return False
        return True


