# 업비트 평가지표 수집 시스템

업비트 WebSocket API를 활용하여 실시간으로 6가지 평가지표를 계산하고 저장하는 시스템입니다.

## 주요 기능

- **실시간 데이터 수집**: 업비트 WebSocket API를 통한 Orderbook, Trade, Candle, Ticker 데이터 수집
- **평가지표 계산**: 스프레드, 오더북 불균형, 예상 슬리피지, 체결 방향 비율, 단기 변동성, 24h 거래대금
- **REST API**: 평가지표 조회 및 모니터링 종목 관리
- **MCP 서버**: FastMCP를 사용한 Model Context Protocol 서버 (LLM 애플리케이션용)
- **Kubernetes 배포**: k8s-home-server 환경에 배포 가능

## 기술 스택

- **FastAPI**: REST API
- **FastMCP**: MCP 서버
- **SQLAlchemy + asyncpg**: PostgreSQL 비동기 ORM
- **Alembic**: 데이터베이스 마이그레이션
- **websockets**: WebSocket 클라이언트
- **asyncio**: 비동기 처리
- **numpy/pandas**: 통계 계산

## 프로젝트 구조

```
upbit-metrics-collector/
├── src/
│   ├── domain/              # 도메인 계층
│   ├── application/         # 애플리케이션 계층
│   ├── infrastructure/      # 인프라 계층
│   ├── interfaces/          # 인터페이스 계층
│   │   ├── api/            # REST API
│   │   └── mcp/            # MCP 서버
│   └── collectors/          # 데이터 수집기
├── alembic/                 # 데이터베이스 마이그레이션
├── tests/                   # 테스트
├── docker/                  # Docker 설정
└── README.md
```

## 빠른 시작

### 환경 변수 설정

`.env` 파일을 생성하거나 `src/config/env_config.py`를 수정하세요:

```bash
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/upbit_metrics
```

### 의존성 설치

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 실행
alembic upgrade head
```

## 서버 실행 방법

### 1. REST API 서버

REST API 서버는 FastAPI 기반으로 평가지표 조회 및 모니터링 종목 관리를 제공합니다.

```bash
# 기본 실행
uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port 8000

# 개발 모드 (자동 리로드)
uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**접속 주소:**
- API: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`
- 헬스 체크: `http://localhost:8000/health`

### 2. 데이터 수집기 (Collector)

데이터 수집기는 업비트 WebSocket API를 통해 실시간 데이터를 수집하고 평가지표를 계산합니다.

```bash
python -m src.collectors.main
```

**기능:**
- Orderbook 데이터 수집 및 스프레드/불균형/슬리피지 계산
- Trade 데이터 수집 및 체결 방향 비율 계산
- Candle 데이터 수집 및 변동성 계산
- Ticker 데이터 수집 및 유동성 계산

### 3. MCP 서버

MCP 서버는 FastMCP를 사용하여 LLM 애플리케이션에서 사용할 수 있는 tools를 제공합니다.

```bash
python -m src.interfaces.mcp.server
```

**제공하는 Tools:**
- `get_monitored_symbols`: 모니터링 종목 목록 조회
- `get_latest_metrics`: 최신 평가지표 조회 (여러 심볼 지원)
- `get_metrics_summary`: 평가지표 요약 조회

**사용 예시:**
MCP 서버는 stdio transport로 실행되며, MCP 클라이언트(예: Claude Desktop, Cursor)에서 사용할 수 있습니다.

### 전체 시스템 실행 (로컬)

모든 서비스를 동시에 실행하려면 각각 별도의 터미널에서 실행하세요:

```bash
# 터미널 1: REST API 서버
uvicorn src.interfaces.api.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 2: 데이터 수집기
python -m src.collectors.main

# 터미널 3: MCP 서버 (필요시)
python -m src.interfaces.mcp.server
```

## API 엔드포인트

### REST API

#### 일반 API (`/api/v1`)
- `GET /api/v1/metrics/{symbol}`: 종목별 평가지표 조회
- `GET /api/v1/metrics/{symbol}/history`: 시계열 조회
- `POST /api/v1/symbols`: 모니터링 종목 추가
- `DELETE /api/v1/symbols/{symbol}`: 모니터링 종목 제거
- `GET /api/v1/symbols`: 모니터링 종목 목록

#### 에이전트용 API (`/v1`)
- `GET /v1/symbols`: 모니터링 종목 목록 조회
- `GET /v1/agent/metrics/latest`: 최신 평가지표 번들 조회
  - 파라미터: `symbols`, `order_size_krw`, `slippage_side`, `ti_windows_sec`, `freshness_ms`
- `GET /v1/agent/metrics/summary`: 평가지표 요약 조회
  - 파라미터: `symbol`, `lookback_sec`, `order_size_krw`, `slippage_side`, `ti_windows_sec`

### MCP Tools

MCP 서버는 다음 tools를 제공합니다:

1. **get_monitored_symbols**
   - 설명: 활성 모니터링 종목 목록을 조회합니다
   - 파라미터: `is_active` (bool, optional)

2. **get_latest_metrics**
   - 설명: 여러 심볼의 최신 평가지표를 한 번에 조회합니다
   - 파라미터:
     - `symbols` (str): 조회할 심볼 목록 (comma-separated)
     - `order_size_krw` (float): 슬리피지 계산용 주문 크기
     - `slippage_side` (str, optional): 슬리피지 방향 (BUY/SELL)
     - `ti_windows_sec` (str, optional): trade imbalance 윈도우
     - `freshness_ms` (int, optional): 데이터 신선도 기준

3. **get_metrics_summary**
   - 설명: 최근 구간의 평가지표 요약을 조회합니다
   - 파라미터:
     - `symbol` (str): 조회할 심볼
     - `order_size_krw` (float): 슬리피지 계산용 주문 크기
     - `lookback_sec` (int, optional): 최근 N초
     - `slippage_side` (str, optional): 슬리피지 방향
     - `ti_windows_sec` (str, optional): trade imbalance 윈도우

## Kubernetes 배포

### 사전 준비

#### 1. Secret 업데이트

`k8s-home-server/manifests/upbit-metrics-collector/secret.yaml` 파일의 실제 값들을 업데이트해야 합니다:

```bash
cd k8s-home-server/manifests/upbit-metrics-collector

# secret.yaml 파일 편집
# 업비트 API 키 설정
UPBIT_ACCESS_KEY: "your-access-key"
UPBIT_SECRET_KEY: "your-secret-key"

# PostgreSQL 비밀번호 설정
POSTGRES_PASSWORD: "secure-password"
POSTGRES_USER: "upbit_metrics"
```

#### 2. 스토리지 경로 생성

```bash
sudo mkdir -p /mnt/k8s-storage/upbit-metrics-collector/postgres
sudo chown -R 999:999 /mnt/k8s-storage/upbit-metrics-collector/postgres
```

#### 3. Docker 이미지 빌드 및 푸시 (선택사항)

로컬에서 이미지를 빌드하고 레지스트리에 푸시할 수 있습니다:

```bash
# 이미지 빌드
docker build -t upbit-metrics-collector:latest .

# 레지스트리에 푸시 (예: Docker Hub)
docker tag upbit-metrics-collector:latest your-registry/upbit-metrics-collector:latest
docker push your-registry/upbit-metrics-collector:latest
```

또는 `deployments.yaml`에서 이미지를 로컬 빌드된 이미지로 사용하거나, 빌드된 이미지를 클러스터에 로드할 수 있습니다.

### 배포 방법

#### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
cd k8s-home-server/manifests/upbit-metrics-collector
./deploy.sh
```

배포 스크립트는 다음 순서로 자동 배포합니다:
1. 네임스페이스 생성
2. 스토리지 생성
3. Secret 및 ConfigMap 생성
4. 데이터베이스 배포 및 준비 대기
5. 애플리케이션 배포
6. Ingress 설정

#### 방법 2: 수동 배포

의존성 순서에 따라 다음 순서로 배포합니다:

```bash
cd k8s-home-server/manifests/upbit-metrics-collector

# 1. 네임스페이스 생성
kubectl apply -f namespace.yaml

# 2. 스토리지 생성
kubectl apply -f storage.yaml

# 3. Secret 및 ConfigMap 생성
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml

# 4. 데이터베이스 배포
kubectl apply -f postgresql.yaml

# 데이터베이스 준비 대기
kubectl wait --for=condition=ready pod -l app=postgresql -n upbit-metrics-collector --timeout=120s

# 5. 애플리케이션 배포
kubectl apply -f deployments.yaml
kubectl apply -f services.yaml

# 6. Ingress 설정
kubectl apply -f ingress.yaml
```

### 배포 후 작업

#### 데이터베이스 마이그레이션

배포 후 데이터베이스 마이그레이션을 실행해야 합니다:

```bash
# API Pod에서 마이그레이션 실행
kubectl exec -it deployment/api -n upbit-metrics-collector -- alembic upgrade head
```

### 상태 확인

```bash
# Pod 상태 확인
kubectl get pods -n upbit-metrics-collector

# 서비스 상태 확인
kubectl get svc -n upbit-metrics-collector

# 로그 확인
kubectl logs -f deployment/api -n upbit-metrics-collector
kubectl logs -f deployment/collector -n upbit-metrics-collector

# Pod 이벤트 확인
kubectl describe pod <pod-name> -n upbit-metrics-collector
```

### 접근

- **API**: `http://<tailscale-ip>/upbit-metrics/api`
- **API 문서**: `http://<tailscale-ip>/upbit-metrics/api/docs`
- **헬스 체크**: `http://<tailscale-ip>/upbit-metrics/api/health`

### 트러블슈팅

#### Pod가 시작되지 않는 경우

```bash
# Pod 이벤트 확인
kubectl describe pod <pod-name> -n upbit-metrics-collector

# 로그 확인
kubectl logs <pod-name> -n upbit-metrics-collector

# ConfigMap 및 Secret 확인
kubectl get configmap upbit-metrics-collector-config -n upbit-metrics-collector -o yaml
kubectl get secret upbit-metrics-collector-secret -n upbit-metrics-collector -o yaml
```

#### 데이터베이스 연결 문제

```bash
# PostgreSQL Pod 상태 확인
kubectl get pods -l app=postgresql -n upbit-metrics-collector

# PostgreSQL 로그 확인
kubectl logs -l app=postgresql -n upbit-metrics-collector

# 데이터베이스 연결 테스트
kubectl exec -it deployment/api -n upbit-metrics-collector -- python -c "from src.infrastructure.persistence.database.session import engine; print('DB 연결 성공')"
```

## 개발

### 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 실행
pytest tests/unit/test_metrics_query.py

# 커버리지 포함 테스트
pytest --cov=src tests/
```

### 코드 포맷팅

```bash
# 타입 체크
mypy src/

# 린터 실행 (설정된 경우)
# flake8 src/
# black src/
```

## 라이선스

이 프로젝트는 학습 목적으로 작성되었습니다.
