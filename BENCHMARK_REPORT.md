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

### 4.1 Dashboard dưới tải

Docker Compose chạy hai replica của v2. Locust tăng 5 user/giây tới 30 user. Lúc **21:41:05 ngày 25/11/2026 (GMT+7)**, Prometheus ghi nhận khoảng **18,86 request/giây** cho `POST /ask`, tỷ lệ lỗi **1,16%** và **6 request đang xử lý**. Các tốc độ và phân vị dưới đây dùng cửa sổ 1 phút. [Dashboard Grafana khi có tải](screenshots/grafana-dashboard.png)

| Câu hỏi Exercise 7.4 | Quan sát và giải thích |
|---|---|
| p95 so với trung bình | Trung bình **241,44 ms**, p95 **295,27 ms**, p99 **1855,97 ms**. Phần lớn request phản hồi nhanh; một nhóm nhỏ phải chờ lâu hơn một giây. Prometheus ước lượng các phân vị từ histogram. |
| Nginx chia tải thế nào? | Hai target đang hoạt động nhận **9,42** và **9,44 request/giây**, gần 50% mỗi bên. Dashboard còn hiển thị lịch sử của replica thứ ba từ lượt đo scaling trước đó. |
| Vì sao nhiều input token hơn output token? | **1371,67 input token/giây** và **729,32 output token/giây**. Với v2, đầu vào gồm system prompt, câu hỏi và phần context truy xuất được; câu trả lời thường ngắn hơn prompt đó. |
| Gọi `/metrics` qua Nginx có kết quả gì? | `GET http://localhost:8080/metrics` trả **404**. Nginx chặn route này ở cổng public. Prometheus tìm từng agent qua DNS của Docker rồi scrape trực tiếp cổng 8000 trên mạng nội bộ. |

### 4.2 Thí nghiệm A và B

Hai thay đổi được áp dụng cùng lúc trên hai replica để chụp cùng một lần cả hai alert đang firing. Tính thời gian từ lúc bắt đầu đổi cấu hình đến lần đầu Prometheus API trả trạng thái `firing` cho từng rule. Script kiểm tra khoảng 3 giây/lần; Prometheus đánh giá rule mỗi 5 giây. Bộ unit test của lab chạy bằng `promtool test rules` cho kết quả `SUCCESS`.

| Thí nghiệm | Panel và giá trị khi cả hai alert cùng firing | Rule | Từ lúc đổi đến firing |
|---|---|---|---:|
| A · `MOCK_ERROR_RATE=0.2` | Error rate của /ask đạt 22,10% | `AgentHighErrorRate` (trên 5% liên tục 1 phút) | 92,7 giây |
| B · `MOCK_SLOW_RATE=0.3` | Latency p95 của /ask đạt 1,893 giây | `AgentHighLatencyP95` (trên 1 giây liên tục 2 phút) | 150,1 giây |

Thời gian đo bao gồm cả lúc tạo lại container và chờ đủ mẫu trong cửa sổ rate 1 phút. Trang Alerts hiển thị cả hai rule của nhóm `agent-slo` cùng firing. Alert chi phí ở nhóm `agent-cost` đã firing từ trước khi đổi cấu hình. [Ảnh Prometheus Alerts](screenshots/prometheus-alert-firing.png)

**Câu hỏi về phiên bản v1 (E).** Agent có thể trả HTTP 200 trong thời gian cho phép nhưng nội dung sai do thiếu bước truy xuất kiến thức. Các rule hạ tầng ở đây chỉ đo lỗi HTTP, latency, khả dụng và chi phí. Chạy golden dataset theo phiên bản, so với baseline và chặn phát hành khi accuracy giảm hoặc có regression. Trong production, có thể chạy bộ câu hỏi kiểm soát định kỳ và đối chiếu với phản hồi người dùng. CP7 đã đo được v1 đúng 1/23 câu trong khi v2 ban đầu đúng 21/23.

### 4.3 Theo dõi request từ trace tới log

Trong cửa sổ log được kiểm tra, request thành công chậm nhất tìm được có trace ID `e5d2fa082f40c4b5741f8265f0b0465d`. Jaeger đo **2188,61 ms** từ đầu tới cuối request. Trong các bước xử lý bên trong agent, gọi `chat mock-llm-small` mất **1681,95 ms** (76,85% thời gian toàn request), còn `agent.retrieve_context` chỉ mất 67,8 ms. Span cha `agent.run` bao gồm cả hai bước. [Ảnh trace chậm](screenshots/jaeger-slow-trace.png)

Dòng log JSON của lần gọi LLM cùng trace ID:

```json
{"ts":"2026-11-25T14:35:56.197837+00:00","level":"INFO","service":"observable-agent","instance":"71d380e712f7","event":"llm_call","trace_id":"e5d2fa082f40c4b5741f8265f0b0465d","span_id":"e5244236e7197207","request_id":"bde5bf0ed000","model":"mock-llm-small","agent_version":"v2","input_tokens":73,"output_tokens":35,"cost_usd":0.000032,"llm_ms":1681.9}
```

Trace `f6bf3aa419e9b6692f47d1d793e34e68` ghi nhận HTTP 503 sau **401,61 ms**. Trong span chat, mục Events ghi `exception.type=utils.mock_llm.LLMError` và thông báo upstream trả 503. Log agent có cùng trace ID và request ID. [Ảnh trace lỗi và event exception](screenshots/jaeger-error-trace.png)

```json
{"ts":"2026-11-25T14:35:53.917451+00:00","level":"INFO","service":"observable-agent","instance":"71d380e712f7","event":"llm_error","trace_id":"f6bf3aa419e9b6692f47d1d793e34e68","span_id":"f4c06e2b58d8c096","request_id":"ce6232763c61","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling

Locust 2.47.0 chạy headless qua Nginx với 100 user, tăng 10 user/giây trong giai đoạn đầu, mỗi lượt kéo dài 2 phút. Cả hai lượt dùng cấu hình mặc định của v2 và giới hạn 0,5 CPU cho mỗi replica. Bảng dùng dòng `Aggregated` của CSV, gồm cả `POST /ask` và `GET /health`.

| Replica | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Số lỗi / số request |
|---|---:|---:|---:|---:|---:|
| 1 | 64.65 | 200 | 690 | 1700 | 77/7681 (1.00%) |
| 3 | 66.21 | 190 | 240 | 1700 | 65/7869 (0.83%) |

Từ 1 lên 3 replica, p95 tổng giảm từ 690 xuống 240 ms (65,2%). Riêng `/ask`, p95 giảm từ 730 xuống 250 ms. RPS tổng chỉ tăng khoảng 2,4% vì cùng 100 user và mỗi user nghỉ 0,5–2 giây giữa các request. p99 vẫn là 1700 ms ở cả hai lượt. Trace chậm cho thấy một lần gọi mock LLM có thể mất gần 1,7 giây ngay trong một request. Scale chia tải giữa các replica nhưng vẫn phải chờ lần gọi đó. [CSV 1 replica](benchmark-results/scale_1_stats.csv) · [CSV 3 replica](benchmark-results/scale_3_stats.csv)

## 6. Kết luận

1. Scale cải thiện rõ p95 trong lượt đo này. p99 vẫn phản ánh nhóm request chờ LLM lâu.
2. Dashboard chỉ ra có lỗi. Trace chỉ ra span phát sinh exception, còn log cùng trace ID nối được lỗi cụ thể với request.
3. Một agent vẫn có thể trả HTTP 200 khi câu trả lời sai. Cần đọc đồng thời SLO vận hành và kết quả eval trước khi phát hành.

Khi triển khai thật, nên thêm tỷ lệ 502/504 ghi trực tiếp ở load balancer, một phép thử định kỳ từ bên ngoài và tỷ lệ câu trả lời đạt trên bộ câu hỏi kiểm soát. Các tín hiệu này lần lượt bao phủ lỗi ở gateway, khả năng truy cập từ phía người dùng và chất lượng câu trả lời.
