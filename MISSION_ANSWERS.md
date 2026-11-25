# Day 14 Lab - Mission Answers

## Part 1 — Localhost vs Production

### Exercise 1.1 — Các anti-pattern trong bản develop

1. [Dòng 17–18](01-localhost-vs-production/develop/app.py#L17) ghi cứng API key và URL cơ sở dữ liệu có thông tin đăng nhập. Credential thật có thể lộ trong repo và lịch sử Git.
2. [Dòng 33–38](01-localhost-vs-production/develop/app.py#L33) dùng `print()` để in câu hỏi, câu trả lời và cả API key. Log bị thu thập tập trung có thể làm lộ nội dung người dùng và secret.
3. [Dòng 21–22](01-localhost-vs-production/develop/app.py#L21) đặt cứng `DEBUG` và `MAX_TOKENS`. Muốn đổi các giá trị này giữa các môi trường phải sửa mã nguồn.
4. [Dòng 51–52](01-localhost-vs-production/develop/app.py#L51) chỉ bind vào `localhost` và cố định cổng `8000`. Nền tảng có thể cấp cổng khác, còn địa chỉ loopback chỉ nhận kết nối trong cùng máy hoặc container.
5. [Dòng 53](01-localhost-vs-production/develop/app.py#L53) luôn bật `reload=True`. Uvicorn theo dõi file và có thể khởi động lại worker khi file thay đổi.
6. [Dòng 42–43](01-localhost-vs-production/develop/app.py#L42) ghi nhận app thiếu `/health`. App cũng thiếu `/ready`, nên hệ thống điều phối thiếu tín hiệu để phân biệt tiến trình còn sống với instance đã sẵn sàng nhận traffic.
7. [Dòng 13](01-localhost-vs-production/develop/app.py#L13) tạo FastAPI app mà không khai báo `lifespan`. Uvicorn vẫn quản lý việc dừng server, nhưng ứng dụng chưa có logic riêng để cập nhật readiness hoặc đóng tài nguyên khi dừng.

### Exercise 1.2 — Chạy bản develop

Đã chạy bản develop qua Uvicorn trên `127.0.0.1:8000` và gửi câu hỏi qua query string theo hướng dẫn K5. Kết quả thực tế từ lần chạy CP1:

```text
POST /ask?question=Hello → HTTP 200
{"answer": "Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}

GET /health → HTTP 404
{"detail": "Not Found"}
```

### Exercise 1.3 — So sánh với bản production

| Hạng mục | Develop | Production | Vì sao quan trọng |
| --- | --- | --- | --- |
| Cấu hình và secret | Giá trị nằm trong mã nguồn. | `Settings` đọc `PORT`, `DEBUG`, `OPENAI_API_KEY` và các cấu hình khác từ biến môi trường. | Dùng cùng mã nguồn cho nhiều môi trường và cấp secret bên ngoài Git. |
| Host, port và reload | `localhost:8000`, luôn bật reload. | Mặc định bind `0.0.0.0`, đọc host và cổng từ env, mặc định tắt reload. | Nền tảng có thể cấp cổng động và định tuyến tới container. |
| Health check | Thiếu `/health` và `/ready`. | `/health` báo tiến trình còn sống. `/ready` dùng cờ readiness của ứng dụng. | Hệ thống điều phối có thể phát hiện tiến trình lỗi và quyết định có gửi traffic vào instance hay không. |
| Logging | `print()` ghi câu hỏi, câu trả lời và key. | Các sự kiện ghi qua `logging` với trường dữ liệu như `question_length` và `response_length`. | Dễ lọc log theo sự kiện và tránh ghi secret hoặc nội dung câu hỏi. |
| Graceful shutdown | Thiếu logic lifecycle dành riêng cho ứng dụng. | Uvicorn quản lý shutdown và FastAPI `lifespan` cập nhật cờ readiness trong bước shutdown. | Server có thể chờ request đang xử lý hoàn tất trong thời gian chờ và ứng dụng có chỗ để dọn tài nguyên trước khi thoát. |

**Đối chiếu mã nguồn.** [Develop đặt cứng cổng ở dòng 52](01-localhost-vs-production/develop/app.py#L52). [Production truyền `settings.port` cho Uvicorn ở dòng 197](01-localhost-vs-production/production/app.py#L197). [Cấu hình đọc biến `PORT` ở dòng 18](01-localhost-vs-production/production/config.py#L18).

**Kết quả chạy bản production.** `GET /health` trả `200` với `status: ok`, `GET /ready` trả `200` với `ready: true`, và `POST /ask` với JSON `{"question":"Hello"}` trả `200` cùng câu trả lời mock. Nhận xét về shutdown dựa trên mã nguồn.

## Part 2 — Docker

### Exercise 2.1 — Dockerfile cơ bản

1. **Base image.** Bản develop dùng `python:3.11`, image Python 3.11 đầy đủ.
2. **Working directory.** `WORKDIR /app` đặt thư mục làm việc bên trong container. Các đích sao chép tương đối như `COPY ... .` trỏ vào thư mục này.
3. **Thứ tự copy.** Dockerfile copy `requirements.txt` và chạy `pip install` trước khi copy mã nguồn. Khi chỉ đổi `app.py`, Docker có thể dùng lại layer dependencies đã cache. Khi đổi `requirements.txt`, layer cài đặt được tạo lại.
4. **`CMD` và `ENTRYPOINT`.** `CMD` khai báo lệnh mặc định, hoặc tham số mặc định cho `ENTRYPOINT` khi dùng cùng nhau. Tham số sau tên image trong `docker run` thay `CMD`. `ENTRYPOINT` dạng exec xác định executable nhận các tham số đó và có thể được ghi đè bằng `--entrypoint`. Bản develop chỉ có `CMD ["python", "app.py"]`.

### Exercise 2.2 — Build và chạy container develop

Chạy từ thư mục gốc của repo vì các đường dẫn nguồn trong Dockerfile tính từ build context `.`.

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run --rm --name k5-day14-cp2-develop -p 127.0.0.1:8000:8000 my-agent:develop
```

| Request gửi tới container | Kết quả thực tế |
| --- | --- |
| `GET /health` | HTTP 200, `status: ok`, `container: true` |
| `POST /ask?question=What%20is%20Docker%3F` | HTTP 200, câu trả lời mock giải thích container dùng để đóng gói app để chạy ở nhiều nơi. |

### Exercise 2.3 — Multi-stage build và kích thước image

- **Builder:** Dùng `python:3.11-slim`, cài `gcc` và `libpq-dev`, sau đó cài Python dependencies vào `/root/.local` bằng `pip install --user`.
- **Runtime:** Bắt đầu bằng một stage `python:3.11-slim` mới, chỉ copy Python dependencies đã cài và mã ứng dụng. Runtime chạy Uvicorn bằng user `appuser` và khai báo health check.
- **Vì sao nhỏ hơn:** Base image slim có ít thành phần hơn bản Python đầy đủ. Việc tách stage giữ các gói phục vụ build trong builder, đồng thời chỉ chuyển kết quả cần để chạy sang runtime.

```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images --filter 'reference=my-agent:*'
docker image inspect my-agent:develop my-agent:advanced --format '{{.Size}}'
```

| Image | Content size từ `docker images` | Disk usage từ `docker images` | Content size chính xác |
| --- | ---: | ---: | ---: |
| `my-agent:develop` | 426 MB | 1,67 GB | 426.319.978 byte |
| `my-agent:advanced` | 57,4 MB | 240 MB | 57.409.125 byte |

Tính theo content size chính xác, bản advanced giảm **86,53%** so với develop, theo công thức `(426319978 - 57409125) / 426319978 × 100`.

### Exercise 2.4 — Kiến trúc Docker Compose và kiểm tra qua Nginx

```mermaid
flowchart LR
    Client["Client · localhost:80"] --> Nginx["Nginx · reverse proxy"]
    subgraph Internal["Docker network: internal"]
        Nginx -->|"HTTP · agent:8000"| Agent["FastAPI agent"]
        Agent -.->|"depends_on · redis:6379"| Redis["Redis · cache"]
        Agent -.->|"depends_on · qdrant:6333"| Qdrant["Qdrant · vector database"]
    end
    Redis --- RedisData[("redis_data")]
    Qdrant --- QdrantData[("qdrant_data")]
```

Nginx nhận HTTP trên cổng 80 của máy và chuyển tiếp tới `agent:8000` qua mạng Compose. Agent chờ Redis và Qdrant có trạng thái `healthy` trước khi khởi động. Compose cấu hình `REDIS_URL` và `QDRANT_URL`, còn hai request mẫu được xử lý bằng mock LLM. Redis và Qdrant có volume riêng và chỉ kết nối qua mạng Docker.

Chạy trong `02-docker/production/` với file `.env.local` rỗng và project `k5-day14-docker`:

```bash
docker compose -p k5-day14-docker up -d --build --wait
docker compose -p k5-day14-docker ps
docker compose -p k5-day14-docker logs --tail 8 nginx agent
```

`docker compose ps` cho thấy Nginx đang chạy, agent, Redis và Qdrant đều `healthy`. Gửi hai request qua cổng 80 cho kết quả:

| Request qua Nginx | Kết quả thực tế |
| --- | --- |
| `GET http://127.0.0.1/health` | HTTP 200, `Server: nginx`, `status: ok`, `version: 2.0.0` |
| `POST http://127.0.0.1/ask` với `{"question":"Explain microservices"}` | HTTP 200, `Server: nginx`, body có trường `answer` từ mock LLM. Log Nginx và agent đều ghi `POST /ask` trả 200. |

## Part 3: Cloud Deployment

### Exercises 3.1–3.2 — Triển khai agent Part 6

Đã có [URL public trên Railway](https://k5-l3a-day14-nguyenhoathanhtung-2a202603519-depl-production.up.railway.app/). Kiểm tra từ bên ngoài: /health trả 200, /ready trả 200 và POST /ask thiếu key trả 401. Người triển khai xác nhận POST /ask với key hợp lệ hoạt động (HTTP 200, có câu trả lời). [Chi tiết triển khai](DEPLOYMENT.md).

Railway dùng `railway.toml` để chọn Dockerfile và health check `/health`. Khi triển khai theo file này, người triển khai cấp Redis và cấu hình các biến của agent trên nền tảng. Render dùng một Blueprint mô tả cả web service và Key Value, tự sinh `AGENT_API_KEY` và nối `REDIS_URL` đến datastore qua mạng riêng.

### Exercise 3.3 — Pipeline Cloud Run

1. Cloud Build chạy bước cài Python dependencies và gọi pytest.
2. Bước build tạo Docker image với hai tag là commit SHA và `latest`.
3. Bước push đưa các tag lên Container Registry. Bước deploy chọn image theo SHA và triển khai Cloud Run tại `asia-southeast1`.
4. Manifest `service.yaml` mô tả giới hạn 1–10 instance, startup probe `/ready`, liveness probe `/health` và secret lấy từ Secret Manager.

## Part 4 — API Security

### Exercise 4.1 — API key

`verify_api_key()` là dependency của `POST /ask`. Hàm đọc header `X-API-Key` và so sánh với biến môi trường `AGENT_API_KEY`. Thiếu key trả `401`, gửi sai key trả `403`, gửi đúng key thì request được xử lý. Để xoay key của bản demo, cập nhật biến môi trường, khởi động lại service để nạp key mới và cập nhật client.

Trích kết quả `curl -i` khi gửi JSON `{"question":"Hello"}`:

```text
# Thiếu key
HTTP/1.1 401 Unauthorized
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

# Sai key
HTTP/1.1 403 Forbidden
{"detail":"Invalid API key."}

# Đúng key
HTTP/1.1 200 OK
{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

### Exercise 4.2 — JWT

Tài khoản demo `student` đăng nhập qua `POST /auth/token`. Server ký JWT bằng HS256, đặt `sub` là username, đưa role vào claim `role` và đặt thời hạn 60 phút. Client gửi JWT trong `Authorization: Bearer <token>`. Dependency `verify_token()` kiểm tra chữ ký và hạn dùng trước khi chuyển username và role cho endpoint.

```text
# POST /auth/token
HTTP/1.1 200 OK
{"token_type":"bearer","expires_in_minutes":60,"hint":"[REDACTED]","access_token":"[REDACTED]"}

# POST /ask thiếu JWT
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer
{"detail":"Authentication required. Include: Authorization: Bearer <token>"}
```

### Exercise 4.3 — Rate limiting

Bản demo dùng **sliding window** 60 giây theo từng username. Mỗi username có một `deque` lưu timestamp của các request đã được chấp nhận. Mỗi lần gọi, limiter bỏ các timestamp cũ và trả `429` khi đã đủ quota. Tài khoản `student` có quota **10 request/60 giây**. Server chọn quota **100 request/60 giây** cho role `admin` đã được xác thực từ JWT. State trong demo nằm trong bộ nhớ của tiến trình.

Đã gửi 20 request liên tiếp bằng `curl -i` với JWT của `student`. Request **1–10** trả `200`, request **11–20** trả `429`.

```text
# Request 10
HTTP/1.1 200 OK
{"question":"Test 10","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":0,"budget_remaining_usd":0.000191}}

# Request 11
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

Trong response demo trên, trường `budget_remaining_usd` đang chứa chi phí đã dùng theo cách gán trong `app.py`.

### Exercise 4.4 — Cost guard với Redis

Hàm [`check_budget(user_id, estimated_cost)`](04-api-gateway/production/cost_guard.py) của bài tập giữ trước chi phí ước tính theo hạn mức **10 USD/user/tháng**. Redis lưu tổng chi phí dưới key `budget:<user_id>:<YYYY-MM>` bằng đơn vị một phần triệu USD. Key hết hạn lúc 00:00 UTC ngày đầu tháng kế tiếp.

Hàm đọc tổng đã giữ, cộng chi phí ước tính và từ chối nếu vượt 10 USD. `WATCH` và `MULTI/EXEC` giúp phép đọc, kiểm tra và ghi an toàn với các request đồng thời. Nếu key thay đổi trước lúc ghi, hàm đọc lại và thử giao dịch mới. Endpoint `/ask` của bản demo JWT dùng cost guard theo ngày có sẵn. Hàm theo tháng được kiểm thử riêng với Redis.

Kết quả kiểm thử trên Redis 7:

- Cùng một user giữ 7,50 USD và 2,50 USD thành công. Khoản 0,01 USD tiếp theo bị từ chối, tổng vẫn là 10 USD.
- User khác vẫn giữ được 0,01 USD. Key hết hạn đúng đầu tháng kế tiếp theo UTC.
- Trong 8 lượt giữ đồng thời, mỗi lượt 3 USD, có 3 lượt thành công và 5 lượt bị từ chối. Tổng cuối là 9 USD.

Rate limit giới hạn số request trong một cửa sổ thời gian. Cost guard giới hạn tổng tiền vì các request có thể dùng số token và chi phí rất khác nhau.

## Part 5: Scaling & Reliability

### Exercise 5.1 — Kiểm tra liveness và readiness

Mở PowerShell ở gốc repo. Dùng image `my-agent:develop` đã build ở CP2 làm môi trường Linux, gắn mã nguồn **CP4 develop** vào container ở chế độ chỉ đọc. Cổng trên máy là 18004.

```powershell
$src = (Resolve-Path '05-scaling-reliability/develop').Path
docker run -d --name k5-day14-cp4-probes -p 127.0.0.1:18004:8000 --mount "type=bind,source=$src,target=/cp4,readonly" -w /cp4 -e PYTHONDONTWRITEBYTECODE=1 my-agent:develop python app.py
curl.exe -i http://127.0.0.1:18004/health
curl.exe -i http://127.0.0.1:18004/ready
```

Khi app khởi động xong, cả hai endpoint trả HTTP 200. `/health` trả `status: ok` và uptime, cho biết tiến trình còn phản hồi. `/ready` trả `ready: true`, cho biết instance có thể nhận traffic. Trong bản develop, readiness dựa trên cờ khởi tạo của app. Khi cờ là false, handler trả 503.

### Exercise 5.2 — Dừng agent khi đang xử lý request

Trong cùng cửa sổ PowerShell, gửi một request bất đồng bộ rồi yêu cầu Docker dừng container. Bản develop đọc `question` từ query string. Mock LLM xử lý khoảng 3 giây nên có thời gian gửi SIGTERM trước khi request hoàn tất.

```powershell
$client = New-Object System.Net.WebClient
$client.Encoding = [Text.Encoding]::UTF8
$pending = $client.UploadStringTaskAsync([uri]'http://127.0.0.1:18004/ask?question=Long%20task', 'POST', '')
Start-Sleep -Milliseconds 500
docker stop -t 10 k5-day14-cp4-probes
$pending.GetAwaiter().GetResult()
docker logs k5-day14-cp4-probes
docker inspect -f '{{.State.ExitCode}}' k5-day14-cp4-probes
docker rm k5-day14-cp4-probes
```

Client nhận được JSON có `answer`. Log ghi `POST /ask ... 200 OK`, `Shutdown complete` và tín hiệu 15 (SIGTERM). Container thoát với mã **0**. Request đang xử lý đã hoàn tất trong thời gian Docker chờ dừng.

### Exercise 5.3 — Xác định nơi lưu lịch sử

Đọc `save_session()` và `load_session()` trong [production/app.py](05-scaling-reliability/production/app.py). Các replica có RAM riêng. Nếu mỗi replica giữ lịch sử trong RAM, request kế tiếp đến replica khác có thể mất ngữ cảnh. Bản production ghi session vào Redis theo key `session:<session_id>`, gia hạn TTL 3.600 giây khi ghi và giữ tối đa 20 tin nhắn. Client dùng cùng `session_id` để tiếp tục hội thoại.

### Exercise 5.4 — Chạy ba replica và quan sát Nginx chia tải

Từ gốc repo, chạy:

```powershell
Set-Location '05-scaling-reliability/production'
if (-not (Test-Path .env.local)) { New-Item -ItemType File .env.local | Out-Null }
docker compose -p k5-day14-scaling up -d --build --scale agent=3 --wait
docker compose -p k5-day14-scaling ps
Invoke-RestMethod http://localhost:8080/health
1..10 | ForEach-Object {
    $body = @{ question = "Request $_" } | ConvertTo-Json
    (Invoke-RestMethod -Method Post -Uri http://localhost:8080/chat -ContentType application/json -Body $body).served_by
} | Group-Object | Select-Object Name,Count
```

Compose báo ba agent và Redis đều `healthy`. Health qua Nginx trả `storage: redis`, `redis_connected: true`. Trong 10 request, `instance-9a2ccd` xử lý 4, `instance-5ba4b2` xử lý 3 và `instance-5808b4` xử lý 3. ID được tạo lại khi khởi động container mới.

### Exercise 5.5 — Kiểm tra cùng một session qua nhiều replica

Vẫn ở thư mục production:

```powershell
$env:PYTHONIOENCODING = 'utf-8'
python test_stateless.py
```

Script gửi 5 câu hỏi tuần tự vào `POST /chat`, dùng lại session ID từ response đầu và đọc `GET /chat/<session_id>/history`. Trong lần chạy này, session `0fdf6ae4-e401-4508-8ed6-9bc76719eac7` đi qua cả ba instance. History có **10 tin nhắn** theo thứ tự 5 cặp user/assistant. Script không tự dừng replica.

Để kiểm tra thêm, dừng một replica rồi đọc lại đúng session vừa tạo. Dùng ID mà script in trên máy của bạn.

```powershell
$sessionId = Read-Host 'Nhap Session ID tu test_stateless.py'
docker stop k5-day14-scaling-agent-1
(Invoke-RestMethod "http://localhost:8080/chat/$sessionId/history").count
docker compose -p k5-day14-scaling down
```

Sau khi dừng replica thứ nhất, hai replica còn lại vẫn phục vụ được yêu cầu qua Nginx và history trả về đủ **10** tin nhắn.

## Part 6 — Production-ready agent (CP5)

Kết quả chạy toàn bộ `python check_production_ready.py` trên Linux với Docker và Redis thật. Script đo image 63 MB, giới hạn 5 request/phút vẫn có hiệu lực sau restart và container dừng trong 0,6 giây với exit code 0.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

## AI log

- **CP2:** Hỏi Codex về các command của Docker để lấy ra các thông tin của các image được build
- **CP3:** Hỏi Codex về cách triên khai bài lab, gợi ý code.
- **CP4:** Hỏi Codex về các lệnh docker, giải thích lệnh.
- **CP5:** Codex hướng dẫn Part 6, cấu hình Docker và Railway.
- **CP6:** Codex hướng dẫn thao tác trên Railway để deploy Redis và App.
- **CP7:** Codex hướng dẫn chạy benchmark local, bổ sung histogram và hai câu trả lời JWT/HPA, đối chiếu golden dataset và lập báo cáo từ JSON.
- **CP8:** Codex hướng dẫn chạy stack observability và thu bằng chứng.
