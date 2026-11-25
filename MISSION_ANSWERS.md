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

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: [Your answer]
2. Working directory: [Your answer]
...

### Exercise 2.3: Image size comparison
- Develop: [X] MB
- Production: [Y] MB
- Difference: [Z]%

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://your-app.railway.app
- Screenshot: [Link to screenshot in repo]

## Part 4: API Security

### Exercise 4.1-4.3: Test results
[Paste your test outputs]

### Exercise 4.4: Cost guard implementation
[Explain your approach]

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
[Your explanations and test results]

## AI log
