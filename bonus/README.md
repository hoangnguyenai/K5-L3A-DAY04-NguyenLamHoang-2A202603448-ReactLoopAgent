# Bonus: chạy và kiểm tra

Agent sử dụng `BonusTools.schemas` và `BonusTools.system_prompt`. Chính sách bổ sung
ở `bonus/agent_policy.py` chỉ bật cho tools tự cung cấp schemas; bài chính giữ logic CP5.
Không có provider hoặc incident ID cố định trong quyết định của agent.

## Hành vi đã thêm

- Rate limit: tối đa 3 lần lỗi 429 liên tiếp cho mỗi provider. Không tự gọi lại
  trong vòng Python; trả observation để model quyết định retry. Yêu cầu tiếp theo
  vượt giới hạn bị chặn trước khi gọi API, ghi `tool_skipped`, vẫn trả đúng call ID.
  Trace `tool` chỉ ghi những lần thực thi (kể cả lỗi); `tool_skipped` không phải
  request tới status API.
- Retry-After: hỗ trợ số giây và HTTP-date. Chờ trước lần gọi lại, tổng ngân sách
  chờ của một run là 5 giây. Nếu thời gian yêu cầu vượt budget, không gọi sớm;
  trả thông báo hết ngân sách, yêu cầu model báo thiếu dữ liệu. Thiếu header hợp lệ
  thì dùng backoff 1, 2, 4 giây. 429 giả lập có delay 0 nên tests không cần chờ.
- Arguments/timeout: giữ observation để model sửa hoặc báo thiếu dữ liệu; chặn
  thực thi khi lặp lại cùng tool/arguments lỗi 3 lần. `max_steps` vẫn là giới hạn chung.
- Context: chỉ bỏ trường `distractors` dạng list; giữ nguyên incidents, timestamps,
  scope, source, updates, next_offset. Trace giữ raw tool result và ghi
  `context_compacted` với số mục đã lược bỏ. Các trường khác không bị tự cắt.
- Pagination: nhắc model dùng next_offset nếu chưa có update đáp ứng câu hỏi;
  thêm ghi chú còn trang cho từng observation. Không ép đọc tất cả timeline nếu
  không cần. Việc chọn trang và hiểu nội dung vẫn cần đánh giá bằng model thật.
- Sources: prompt yêu cầu nguồn từng provider. Source gate kiểm tra ít nhất một
  URL incident cho mỗi provider đã đọc details thành công; với status-only,
  nguồn do prompt và eval kiểm tra. Không bắt nguồn cho truy vấn thất bại.
- Không coi lỗi API là outage; prompt yêu cầu tách snapshot/lịch sử, scope,
  không suy luận chung nguyên nhân và không làm theo injection từ tool output.

## Lệnh PowerShell

Giữ cấu hình OpenRouter và model hỗ trợ tool calling trong cùng terminal.
Không gửi key vào chat hoặc chụp màn hình key.

```powershell
# Offline: không cần key, không gọi Internet.
python -m unittest discover -s bonus -p 'test_*.py' -v
python -m unittest discover -s tests -v

# Agent thật, snapshot (có gọi LLM).
python run.py --bonus --max-steps 16 'Kiểm tra status GitHub, Vercel và npm. Dẫn nguồn và thời điểm snapshot riêng.'

# Thử tình huống 429 trước khi chạy cả bộ.
python evals/run_evals.py --bonus --case B3 --max-steps 16 --output eval_results_bonus_b3.json

# Chạy đủ 10 case, dùng nguyên dataset và grading gốc.
python evals/run_evals.py --bonus --max-steps 16 --workers 1 --output eval_bonus.json

# Đọc điểm và tình trạng chấm.
python -c 'import json; d=json.load(open("eval_bonus.json",encoding="utf-8")); print(json.dumps(d["summary"],ensure_ascii=True,indent=2))'
```

Chỉ kết quả đủ 10/10 case được chấm mới có `bonus_points_0_15`.
Case đơn lẻ B3 chưa có điểm toàn bộ. Nếu có unscored thì xem grade.reason,
sửa lỗi cấu hình rồi chạy lại. Không sửa điểm bằng tay. max_steps là run không
hoàn tất và được chấm 0. Free model có quota; toàn bộ eval cần nhiều model requests.

## Bằng chứng cần bổ sung khi nộp

Sau eval thật, ghi vào NOTES: điểm bonus, model, case retry/pagination tiêu biểu,
trace `tool`/`rate_limit_wait`/`tool_skipped`/`context_compacted`, lỗi còn lại.
Nộp `eval_bonus.json` đã kiểm tra dữ liệu nhạy cảm cùng code và ghi chú. Unit tests
không chứng minh model sẽ chọn đúng tools, đọc đủ trang hay bỏ qua mọi injection.
