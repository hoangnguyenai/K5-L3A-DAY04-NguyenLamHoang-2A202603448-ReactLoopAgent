# Ghi chú phân tích · Day 04

Họ và tên:
MSSV:

Trạng thái: đã hoàn thiện code và tests offline. Chưa có eval LLM thật trước/sau;
các trường kết quả bên dưới cần điền sau khi chạy CP4 và CP6. Không dùng kết quả
FakeProvider làm điểm eval. Lệnh chi tiết: `checkpoints/README.md`.

## 1. Case được chọn

- ID case:
- Câu trả lời của agent:
- Điểm ở lần chạy 1:

## 2. Bằng chứng trong trace

Dán đoạn trace chứng minh lỗi và nêu nguyên nhân có thể xảy ra.

```text

```

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: thêm source gate trong `agent.py`; giữ bản trước cải tiến tại
  `checkpoints/agent_cp3.py`. Chỉ lưu URL từ `get_incident_details` có `ok: true`.
  Nếu final thiếu mọi URL đã quan sát, ghi event `validation_missing_source`,
  yêu cầu model sửa và tính lần sửa vào `max_steps`.
- Vì sao chọn thay đổi này: prompt yêu cầu dẫn nguồn nhưng không tự bảo đảm model
  thực hiện. Gate kiểm tra bằng code điều kiện tối thiểu trước khi completed.
  Đây là cải tiến chuẩn bị trước eval; cần đối chiếu trace thật để xác định case
  nào thực sự hưởng lợi, không suy ra cải thiện điểm khi chưa đo.
- Bằng chứng offline: `python checkpoints/demo.py` dùng cùng kịch bản hai tool calls;
  CP3 chấp nhận final thiếu URL ở step 3, CP5 yêu cầu sửa và completed ở step 4.
  `tests/test_validation.py` kiểm tra sửa trong budget, hết budget và tool thất bại.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng |  |  |
| Điểm case đã chọn |  |  |
| Số model calls |  |  |
| Token, chi phí nếu có |  |  |

- Lỗi đã giải quyết:
- Lỗi còn lại hoặc mới xuất hiện:

## 5. Giới hạn

Nêu giới hạn của điểm judge, của snapshot và của việc chỉ chạy một lần mỗi phiên bản.

- Judge LLM là đánh giá xấp xỉ, có thể sai hoặc thiên lệch, nhất là khi cùng model
  tự chấm. Cần đối chiếu expected, câu trả lời và trace.
- Snapshot là dữ liệu đã lưu, không chứng minh trạng thái dịch vụ hiện tại.
  Tool chỉ tìm trong 50 incident gần nhất và có thể rút gọn updates.
- Một lần chạy mỗi phiên bản không chứng minh độ ổn định hoặc quan hệ nhân quả
  giữa thay đổi code và điểm số. Phải giữ nguyên cấu hình để so sánh.
- Source gate chỉ kiểm tra sự hiện diện ít nhất một URL đã quan sát, không xác minh
  mọi claim hoặc mọi incident. Việc yêu cầu sửa tốn thêm lượt model và token.
- Chưa có dữ liệu eval thật để kết luận lỗi đã giải quyết hoặc điểm tăng/giảm.

## Bonus — triển khai và kiểm chứng

- Code: `agent.py` chọn schemas/system prompt từ tools; `bonus/agent_policy.py`
  bổ sung chính sách retry, context và nguồn trong chế độ bonus. Không thay đổi
  fixtures, cases, scenarios hoặc grading.
- Retry: model nhận lỗi và chọn thử lại; code giới hạn 3 lần 429 liên tiếp/provider,
  chờ Retry-After dạng giây hoặc HTTP-date. Tổng ngân sách chờ là 5 giây/run;
  quá budget thì chặn gọi sớm và báo thiếu dữ liệu. Không có header thì backoff
  1/2/4 giây. Tool/arguments lỗi giống nhau cũng bị chặn sau 3 lần thất bại.
- Trace: `tool` giữ result gốc; `rate_limit_wait` ghi thời gian chờ;
  `tool_skipped` ghi yêu cầu bị chặn và vẫn có observation đúng tool-call ID.
- Context: 160 bản ghi distractors được giữ trong trace nhưng bỏ khỏi context;
  có event `context_compacted`. Giữ nguyên nguồn, thời gian, incidents và updates.
- Pagination: model được nhắc đọc tiếp next_offset khi câu hỏi cần, nhận ghi chú
  còn trang. Chưa có cơ chế xác minh ngữ nghĩa rằng model đã đọc đủ để trả lời.
- Sources: bắt URL theo từng provider đã đọc details thành công; status-only dựa
  vào prompt và eval. URL xuất hiện không chứng minh mọi claim đều đúng.
- Offline: 10 tests bonus và 41 tests trong `tests/` đã đạt. Bằng chứng gồm rate
  limit kéo dài bị chặn, vẫn trả được GitHub khi Vercel lỗi, HTTP-date/Retry-After,
  hai trang khác nhau, giữ trace gốc và kiểm tra nguồn của hai provider.
- Eval bonus thật: chưa chạy từ môi trường trợ lý vì không có API key trong process.
  Sau khi chạy đủ 10 case, bổ sung điểm, trace thực tế và hạn chế còn lại tại đây.
- Lệnh chạy: `bonus/README.md`.
