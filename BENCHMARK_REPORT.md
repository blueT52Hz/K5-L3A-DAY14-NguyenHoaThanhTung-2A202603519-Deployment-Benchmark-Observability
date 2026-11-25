# Benchmark & Observability Report — Day 14

**Họ tên** Nguyễn Hoa Thanh Tùng  
**Ngày chạy** 25/11/2026  
**Môi trường** Windows, Python 3.12.5, Uvicorn một worker, mock LLM. Client chạy trên cùng máy với server. Số liệu gốc nằm trong [reports](reports/).

## 1. SLO của agent

| SLI | Ngưỡng | Lý do |
|---|---|---|
| p95 latency của POST /ask | ≤ 500 ms | Ít nhất 95% request cần phản hồi trong nửa giây. |
| Tỷ lệ lỗi /ask | ≤ 2% | Cho phép tối đa 6 lỗi trong mỗi lượt 300 request. |
| Accuracy trên golden dataset | ≥ 80% khi đo baseline, 100% sau khi sửa | Ngưỡng đầu dùng so sánh hai phiên bản. Ngưỡng cuối xác nhận đã xử lý đủ các câu thiếu trong kho kiến thức. |

## 2. Benchmark hiệu năng

### 2.1 Concurrency và latency của v2

Mỗi lượt gửi 300 request đến cùng endpoint, với tỷ lệ mô phỏng request chậm 3% và lỗi 1%.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Tỷ lệ lỗi | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.13 | 201.1 | 242.6 | 1715.1 | 0.33% | Đạt |
| 10 | 43.44 | 192.9 | 234.1 | 1680.4 | 0.33% | Đạt |
| 50 | 74.50 | 269.6 | 1286.7 | 1808.6 | 0.67% | Trượt p95 |
| 100 | 41.67 | 1212.1 | 5121.3 | 5412.7 | 2.00% | Trượt p95 |

Từ 1 lên 10 request đồng thời, client tận dụng được thời gian chờ I/O và thông lượng tăng khoảng 10 lần. Mức 50 có RPS cao nhất trong bốn lượt đo nhưng p95 đã vượt 1 giây. Tăng lên 100 làm RPS giảm và cả p50 cũng vượt 1 giây. Các số đo đầu cuối cho thấy dấu hiệu bão hòa trên máy chạy thử. Muốn xác định chính xác tài nguyên gây nghẽn cần đo riêng client và server.

### 2.2 Tail latency

Giữ concurrency ở 20 và gửi 300 request cho mỗi giá trị của `MOCK_SLOW_RATE`.

| Tỷ lệ mô phỏng request chậm | Trung bình (ms) | p95 (ms) | p99 (ms) | Kết quả SLO |
|---|---|---|---|---|
| 0 | 194.5 | 233.4 | 247.4 | Trượt tỷ lệ lỗi, 7/300 |
| 0.03 | 241.1 | 242.5 | 1705.4 | Đạt |
| 0.1 | 325.6 | 1707.3 | 1728.5 | Trượt p95 |

p99 phát hiện nhóm request chậm ngay ở mức 3%, khi p95 vẫn dưới 250 ms. Ở mức 10%, p95 cũng vượt 1.7 giây dù trung bình chỉ 326 ms. Dùng riêng trung bình sẽ bỏ sót thời gian chờ của nhóm người dùng này.

### 2.3 Đọc /metrics

- Counter `http_requests_total` ghi nhận 1217 lần POST /ask trả 200 và 10 lần trả 503 tại thời điểm đọc.
- Gauge `agent_in_flight_requests` bằng 0 khi đọc sau lượt thử. Nó tăng và giảm theo số request đang xử lý.
- Histogram mới `agent_question_length_chars` đã ghi nhận 1227 quan sát. Các bucket cho biết phân bố độ dài câu hỏi theo ký tự. Dùng độ dài làm giá trị quan sát và dùng route chuẩn hóa làm nhãn cho HTTP. Gắn nguyên văn câu hỏi hay request ID làm nhãn sẽ tạo thêm chuỗi thời gian cho từng giá trị mới, tăng bộ nhớ và chi phí truy vấn.

## 3. Benchmark chất lượng

Cả ba lượt dùng cùng 23 câu của golden dataset. Chi phí dưới đây do mock LLM tính theo token.

| Chỉ số | v1 | v2 ban đầu | v2 sau sửa |
|---|---|---|---|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100%) |
| Token trung bình/câu | 57.4 | 108.8 | 113.1 |
| Tổng chi phí (USD) | 0.000408 | 0.000758 | 0.000786 |
| Chi phí/câu đúng (USD) | 0.00040815 | 0.00003607 | 0.00003417 |
| p95 (ms) | 201.4 | 215.8 | 229.4 |
| Quality gate | FAIL (80%) | PASS (80%) | PASS (100%, 0 regression) |

| ID câu sai ở v2 ban đầu | Từ khóa thiếu | Nội dung bổ sung vào kho kiến thức |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Giải thích cách xác thực JWT, kiểm tra chữ ký và thời điểm token hết hạn. |
| scaling-03 | cpu, memory, custom metrics | Giải thích các loại metric mà Kubernetes HPA có thể dùng để điều chỉnh số replica. |

V2 dùng nhiều token hơn và p95 cao hơn v1, nhưng chi phí cho mỗi câu đúng giảm hơn 11 lần. Sau khi bổ sung hai câu trả lời, toàn bộ 21 câu đúng ở baseline tiếp tục đạt và hai câu thiếu đều đạt.

**Áp dụng trong CI.** Trên mỗi pull request, khởi động agent rồi chạy `eval/run_eval.py` với `--min-accuracy 0.85` và `--baseline` trỏ tới kết quả của phiên bản đã chấp nhận. Với 23 câu, cần ít nhất 20 câu đúng. Đặt job này làm required status check của nhánh chính để chặn merge khi accuracy dưới ngưỡng hoặc có câu từng đúng nay sai.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. ...
  2. ...
  3. ...
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

...
