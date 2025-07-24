# WebSocket Test Service

一個功能完整的 WebSocket 測試服務，提供健康檢查、訊息回應和廣播功能。適用於 WebSocket 連接測試、開發除錯和系統監控。

## 功能特色

- 🔄 **多種連接方式**：支援獨立 WebSocket 服務器和 HTTP WebSocket 端點
- 💬 **智能訊息處理**：自動識別 JSON 物件和純文字訊息
- 📊 **健康檢查**：內建 HTTP 健康檢查端點
- 📢 **廣播功能**：支援向所有連接的客戶端廣播訊息
- 🐛 **數字修復**：修復了純數字輸入導致連接中斷的問題
- 📝 **詳細日誌**：完整的連接和錯誤日誌記錄

## 快速開始

### 使用 Docker Hub 映像（推薦）

```bash
# 拉取映像
docker pull minihaha/websocket-test:latest

# 運行服務
docker run -d -p 8080:8080 -p 8765:8765 --name websocket-service minihaha/websocket-test:latest

# 檢查服務狀態
docker ps
```

### 本地建置

```bash
# 克隆專案
git clone <your-repo-url>
cd websocket-docker

# 建置映像
docker build -t websocket-test-service .

# 運行容器
docker run -d -p 8080:8080 -p 8765:8765 --name websocket-service websocket-test-service
```

### 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 運行服務
python app.py
```

## 服務端點

啟動後可以使用以下端點：

| 端點 | 類型 | 描述 |
|------|------|------|
| `http://localhost:8080/` | HTTP | 健康檢查端點 |
| `http://localhost:8080/health` | HTTP | 健康檢查端點 |
| `ws://localhost:8080/ws` | WebSocket | HTTP WebSocket 端點 |
| `ws://localhost:8765/` | WebSocket | 獨立 WebSocket 服務器 |

## 使用方法

### 健康檢查

```bash
curl http://localhost:8080/health
```

回應範例：
```json
{
  "status": "healthy",
  "timestamp": "2025-07-23T09:00:00.000000",
  "active_websocket_connections": 2,
  "service": "websocket-test-service",
  "version": "1.0.0"
}
```

### 使用 wscat 測試 WebSocket 連接

#### 安裝 wscat

```bash
npm install -g wscat
```

#### 連接到獨立 WebSocket 服務器

```bash
wscat --connect ws://localhost:8765
```

#### 連接到 HTTP WebSocket 端點

```bash
wscat --connect ws://localhost:8080/ws
```

### 訊息測試範例

連接成功後，你可以測試不同類型的訊息：

#### 1. 純文字訊息

```
> hello world
< {"type": "text_echo", "timestamp": "2025-07-23T09:01:00.000000", "original_message": "hello world", "message_length": 11}

> 123
< {"type": "text_echo", "timestamp": "2025-07-23T09:01:05.000000", "original_message": "123", "message_length": 3}
```

#### 2. Ping/Pong 測試

```
> {"type": "ping", "data": "test"}
< {"type": "pong", "timestamp": "2025-07-23T09:01:10.000000", "original_data": {"type": "ping", "data": "test"}}
```

#### 3. Echo 測試

```
> {"type": "echo", "message": "Hello Echo"}
< {"type": "echo_response", "timestamp": "2025-07-23T09:01:15.000000", "echoed_data": {"type": "echo", "message": "Hello Echo"}}
```

#### 4. 廣播訊息

```
> {"type": "broadcast", "message": "Hello everyone!"}
< {"type": "broadcast_confirmation", "timestamp": "2025-07-23T09:01:20.000000", "recipients": 3}
```

其他連接的客戶端會收到：
```json
{
  "type": "broadcast",
  "timestamp": "2025-07-23T09:01:20.000000",
  "message": "Hello everyone!",
  "sender": "172.17.0.1"
}
```

## 支援的訊息格式

### JSON 物件訊息

所有 JSON 物件訊息都應該包含 `type` 欄位：

- **ping**: 測試連接，回應 pong
- **echo**: 回應原始訊息
- **broadcast**: 向所有連接的客戶端廣播訊息

### 純文字訊息

任何非 JSON 格式的訊息（包括純數字）都會被當作純文字處理，並回應訊息的詳細資訊。

## Docker 相關指令

### 基本操作

```bash
# 檢查容器狀態
docker ps

# 查看日誌
docker logs websocket-service

# 查看即時日誌
docker logs -f websocket-service

# 停止服務
docker stop websocket-service

# 移除容器
docker rm websocket-service

# 移除映像
docker rmi minihaha/websocket-test:latest
```

### 進階操作

```bash
# 進入容器 shell
docker exec -it websocket-service /bin/bash

# 檢查容器資源使用
docker stats websocket-service

# 匯出容器
docker export websocket-service > websocket-service-backup.tar

# 重啟容器
docker restart websocket-service
```

## 故障排除

### 常見問題

1. **純數字輸入導致連接中斷**
   - ✅ 已修復：現在純數字會被當作普通文字處理

2. **端口被占用**
   ```bash
   # 檢查端口使用情況
   netstat -tlnp | grep :8080
   netstat -tlnp | grep :8765
   ```

3. **容器無法啟動**
   ```bash
   # 檢查詳細錯誤
   docker logs websocket-service
   ```

4. **WebSocket 連接失敗**
   - 確認防火牆設定
   - 檢查端口映射是否正確
   - 驗證 Docker 容器是否正在運行

### 日誌分析

服務提供詳細的日誌記錄：

```bash
# 查看連接日誌
docker logs websocket-service | grep "connection"

# 查看錯誤日誌
docker logs websocket-service | grep "ERROR"

# 查看特定時間的日誌
docker logs --since "2025-07-23T09:00:00" websocket-service
```

## 開發資訊

### 依賴套件

- **websockets**: WebSocket 服務器實現
- **aiohttp**: 異步 HTTP 服務器
- **aiohttp-cors**: CORS 支援

### 專案結構

```
websocket-docker/
├── app.py              # 主要應用程式
├── requirements.txt    # Python 依賴
├── Dockerfile         # Docker 建置檔案
└── README.md          # 專案說明
```

### 環境變數

目前服務使用預設配置，未來版本可能支援以下環境變數：

- `WEBSOCKET_HOST`: WebSocket 服務器綁定地址（預設: 0.0.0.0）
- `WEBSOCKET_PORT`: WebSocket 服務器端口（預設: 8765）
- `HTTP_HOST`: HTTP 服務器綁定地址（預設: 0.0.0.0）
- `HTTP_PORT`: HTTP 服務器端口（預設: 8080）

---

**Docker Hub**: [minihaha/websocket-test](https://hub.docker.com/r/minihaha/websocket-test)
