# WebSocket 負載平衡測試服務

這是一個增強版的 WebSocket 測試服務，支援**服務實例識別**功能，專門用於測試負載平衡器在 Docker 和 Kubernetes 環境中的行為。

## 🚀 新功能特色

### 服務實例識別

- **自動檢測運行環境** (本機/Docker/Kubernetes)
- **唯一實例 ID** 生成
- **Pod/容器資訊收集** (hostname, IP, Pod名稱等)
- **即時連線資訊** 顯示用戶連接到哪個服務實例

### 完整的 WebSocket 功能

- Health Check 端點 (`/` 和 `/health`)
- HTTP WebSocket 端點 (`/ws`)
- 獨立 WebSocket 服務器 (port 8765)
- 訊息回音、廣播、Ping/Pong 功能

## 🏗️ 部署方式

### 1. 本機 Docker 運行

```bash
# 構建鏡像
docker build -t websocket-test .

# 運行單個容器
docker run -p 8080:8080 -p 8765:8765 websocket-test

# 運行多個容器測試負載平衡
docker run -d -p 8081:8080 -p 8766:8765 --name ws-test-1 websocket-test
docker run -d -p 8082:8080 -p 8767:8765 --name ws-test-2 websocket-test
docker run -d -p 8083:8080 -p 8768:8765 --name ws-test-3 websocket-test
```

### 2. Kubernetes 部署

```bash
# 部署服務 (3個副本)
kubectl apply -f k8s-deployment.yaml

# 檢查 Pod 狀態
kubectl get pods -l app=websocket-test

# 檢查服務
kubectl get svc websocket-test-service

# 檢查負載平衡器 (如果使用 LoadBalancer type)
kubectl get svc websocket-test-lb
```

## 🔧 環境變數配置

在 Kubernetes 中，以下環境變數會自動設定：

```yaml
env:
- name: POD_NAME
  valueFrom:
    fieldRef:
      fieldPath: metadata.name
- name: POD_NAMESPACE
  valueFrom:
    fieldRef:
      fieldPath: metadata.namespace
- name: NODE_NAME
  valueFrom:
    fieldRef:
      fieldPath: spec.nodeName
- name: SERVICE_NAME
  value: "websocket-test-service"
```

## 🧪 測試負載平衡

### 使用內建測試腳本

```bash
# 安裝依賴
pip install websockets aiohttp

# 測試本機 Docker 容器
python test_lb.py --host localhost --connections 10

# 測試 Kubernetes 服務 (透過 port-forward)
kubectl port-forward svc/websocket-test-service 8080:8080 8765:8765
python test_lb.py --host localhost --connections 10

# 測試 LoadBalancer 服務
python test_lb.py --host <EXTERNAL-IP> --connections 10
```

### 手動測試

#### 1. 健康檢查測試

```bash
# 檢查服務狀態和實例資訊
curl http://localhost:8080/health | jq

# 範例回應:
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "active_websocket_connections": 0,
  "service": "websocket-test-service",
  "version": "1.0.0",
  "service_identity": {
    "instance_id": "a1b2c3d4",
    "hostname": "websocket-test-service-7d8f9-xyz12",
    "container_ip": "10.244.1.15",
    "pod_name": "websocket-test-service-7d8f9-xyz12",
    "node_name": "k8s-worker-1",
    "namespace": "default",
    "service_name": "websocket-test-service",
    "environment": "kubernetes",
    "display_name": "websocket-test-service-websocket-test-service-7d8f9-xyz12"
  }
}
```

#### 2. WebSocket 連線測試

使用瀏覽器開發者工具或 WebSocket 客戶端：

```javascript
// 連接到 HTTP WebSocket 端點
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
    
    // 第一次連線會收到 welcome 訊息
    if (data.type === 'welcome') {
        console.log(`Connected to: ${data.service_identity.display_name}`);
        console.log(`Environment: ${data.service_identity.environment}`);
        console.log(`Pod Name: ${data.service_identity.pod_name}`);
    }
};

// 發送測試訊息
ws.send(JSON.stringify({
    type: "ping",
    message: "Hello from client"
}));
```

## 📊 負載平衡驗證

### 預期行為

當多個服務實例運行時：

1. **每次連線都會顯示實例資訊**

   ```json
   {
     "type": "welcome",
     "message": "Connected to websocket-test-service-pod-abc123",
     "service_identity": {
       "display_name": "websocket-test-service-pod-abc123",
       "hostname": "websocket-test-service-deployment-abc123",
       "pod_name": "websocket-test-service-deployment-abc123"
     }
   }
   ```

2. **多次連線應該分散到不同實例**
   - 連線 1: `websocket-test-service-pod-abc123`
   - 連線 2: `websocket-test-service-pod-def456`
   - 連線 3: `websocket-test-service-pod-ghi789`

### 測試結果範例

```bash
🚀 Starting WebSocket Load Balancer Test
==================================================
🔍 Testing health check: http://localhost:8080/health
✅ Health check OK - Instance: websocket-test-service-deployment-7d8f9-xyz12

📡 Testing HTTP WebSocket endpoint
🔄 Testing 5 connections for load balancing
   URL: ws://localhost:8080/ws

🔌 Testing WebSocket: Connection-1
✅ Connected to: websocket-test-service-deployment-7d8f9-xyz12

🔌 Testing WebSocket: Connection-2
✅ Connected to: websocket-test-service-deployment-5a6b7-def34

📊 Load Balancing Results:
   websocket-test-service-deployment-7d8f9-xyz12: 2 connections
   websocket-test-service-deployment-5a6b7-def34: 2 connections
   websocket-test-service-deployment-1c2d3-ghi56: 1 connections
✅ Load balancing is working - traffic distributed across multiple instances
```

## 🐛 故障排除

### 常見問題

1. **所有連線都打到同一個實例**
   - 檢查 Service 的 `sessionAffinity` 設定
   - 確認有多個 Pod 在運行 (`kubectl get pods`)

2. **環境變數未正確設定**

   ```bash
   # 檢查 Pod 環境變數
   kubectl exec -it <pod-name> -- env | grep POD_
   ```

3. **健康檢查失敗**

   ```bash
   # 檢查 Pod 日誌
   kubectl logs <pod-name>
   
   # 檢查 Pod 狀態
   kubectl describe pod <pod-name>
   ```

### 日誌範例

服務啟動時會顯示：

```bash
2024-01-20 10:30:00 - __main__ - INFO - Service Identity: {'instance_id': 'a1b2c3d4', 'hostname': 'websocket-test-service-7d8f9-xyz12', ...}
2024-01-20 10:30:00 - __main__ - INFO - === WebSocket Test Service Started ===
2024-01-20 10:30:00 - __main__ - INFO - Service Instance: websocket-test-service-websocket-test-service-7d8f9-xyz12
2024-01-20 10:30:00 - __main__ - INFO - Environment: kubernetes
```

## 🔧 客製化

### 自定義服務名稱

```yaml
env:
- name: SERVICE_NAME
  value: "my-custom-websocket-service"
```

### 添加額外的實例資訊

修改 `ServiceIdentity` 類別來包含更多資訊，例如：

- 版本號
- 部署時間
- 自定義標籤

## 📝 API 文檔

### WebSocket 訊息格式

#### Welcome 訊息 (自動發送)

```json
{
  "type": "welcome",
  "message": "Connected to websocket-test-service-pod-abc123",
  "timestamp": "2024-01-20T10:30:00Z",
  "client_ip": "192.168.1.100",
  "service_identity": {
    "instance_id": "a1b2c3d4",
    "hostname": "websocket-test-service-7d8f9-xyz12",
    "display_name": "websocket-test-service-websocket-test-service-7d8f9-xyz12",
    "environment": "kubernetes"
  }
}
```

#### Ping 訊息

```json
// 發送
{
  "type": "ping",
  "data": "test"
}

// 回應
{
  "type": "pong",
  "timestamp": "2024-01-20T10:30:00Z",
  "original_data": {"type": "ping", "data": "test"}
}
```
