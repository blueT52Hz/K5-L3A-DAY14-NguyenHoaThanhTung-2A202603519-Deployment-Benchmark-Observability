# CP6 — Triển khai agent trên Railway

**Trạng thái:** Agent đang chạy, Redis sẵn sàng. Đã xác minh 3/4 request CP6.

| Thiết lập | Giá trị |
| --- | --- |
| Nhánh GitHub | `demo` |
| Root Directory | `/06-lab-complete` |
| Web service | Agent Part 6, Docker |
| Redis | Railway Redis (đã xác minh qua /ready) |
| Cấu hình | `ENVIRONMENT=production`, `AGENT_API_KEY` cấu hình trên service agent, `REDIS_URL` tham chiếu service Redis, `PORT` do nền tảng cấp |

## Kiểm tra URL public

Trong Git Bash, dùng URL bên dưới và nhập key từ mục Variables của service. Lệnh nhập key ẩn ký tự. Các lệnh curl chỉ in mã HTTP.

```bash
BASE='https://k5-l3a-day14-nguyenhoathanhtung-2a202603519-depl-production.up.railway.app'
BASE=${BASE%/}
read -rsp 'AGENT_API_KEY: ' AGENT_API_KEY
echo
curl -sS -o /dev/null -w 'health: %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w 'ready: %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w 'ask without key: %{http_code}\n' -H 'Content-Type: application/json' -d '{"question":"Hello"}' "$BASE/ask"
curl -sS -o /dev/null -w 'ask with key: %{http_code}\n' -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}' "$BASE/ask"
unset AGENT_API_KEY
```

URL public: https://k5-l3a-day14-nguyenhoathanhtung-2a202603519-depl-production.up.railway.app/. Kết quả thực tế: GET /health → 200, GET /ready → 200, POST /ask thiếu key → 401. Còn kiểm tra POST /ask với key hợp lệ (kỳ vọng 200).

## Ảnh minh chứng cần lưu

- `screenshots/dashboard.png` — dashboard hiển thị web service và Redis.
- `screenshots/running.png` — web service ở trạng thái Live cùng URL public.
- `screenshots/test.png` — kết quả bốn request trên URL public.
