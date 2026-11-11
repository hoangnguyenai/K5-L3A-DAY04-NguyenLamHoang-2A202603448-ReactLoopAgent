# Ghi chú phân tích · Day 04

Họ và tên: Nguyễn Lâm Hoàng
MSSV: **2A202603448**

Bài chính đã chạy đủ 22 case trước và sau cải tiến; bonus đã chạy đủ 10 case.
Các số liệu và đoạn trace dưới đây được đối chiếu từ `eval_before.json`,
`eval_after.json` và `eval_bonus.json`. Tests offline dùng fake provider được
phân biệt với kết quả eval gọi model thật.

## 1. Case được chọn

- ID case: **H1** — đọc incident GitHub `h02n9572mx9y`, theo liên kết của nó để
  điều tra nguyên nhân/ảnh hưởng, rồi đối chiếu với Cloudflare `yaa0witbl2me`.
  Câu hỏi yêu cầu thời gian, trạng thái, component, bằng chứng nhân quả và nguồn
  cho từng bên.
- Điểm trước cải tiến: **93/100**; sau cải tiến: **96/100**.
- Câu trả lời trước cải tiến, tóm tắt: cả hai incident resolved; GitHub ảnh hưởng
  Actions, Cloudflare ảnh hưởng Workers Builds; không đủ bằng chứng chung nguyên
  nhân. Câu trả lời có dẫn liên kết incident gộp `xr3myzj7ms51` trong nội dung,
  nhưng không chứa hai URL nguồn của các incident đã được tool trả về.
- Trích phần dẫn nguồn trước cải tiến (chuẩn hóa Markdown và khoảng trắng):

```text
Source: GitHub incident details returned by the status API (incident h02n9572mx9y)【functions.get_incident_details】.
```

Dòng trích trên đã lược bỏ Markdown nhấn mạnh và ký tự khoảng trắng đặc biệt;
nguyên văn đầy đủ nằm tại `cases[id=H1].result.answer` trong `eval_before.json`.
Marker tên hàm không thay thế URL nguồn có thể mở để kiểm tra. Sau cải tiến,
câu trả lời có URL `https://stspg.io/7pwv28hvkmz8` và
`https://www.cloudflarestatus.com/incidents/yaa0witbl2me`.

## 2. Bằng chứng trong trace và nguyên nhân

Các đoạn dưới đây trích những trường liên quan; tool result đầy đủ nằm trong
file eval, không phải mọi trường của result đều được chép lại.

Ở H1 trước cải tiến, hai lần đọc details thành công trả nguồn như sau:

```json
[
  {
    "event": "tool",
    "step": 1,
    "name": "get_incident_details",
    "arguments": {"provider": "github", "incident_id": "h02n9572mx9y"},
    "result": {"ok": true, "url": "https://stspg.io/7pwv28hvkmz8"}
  },
  {
    "event": "tool",
    "step": 2,
    "name": "get_incident_details",
    "arguments": {"provider": "cloudflare", "incident_id": "yaa0witbl2me"},
    "result": {"ok": true, "url": "https://www.cloudflarestatus.com/incidents/yaa0witbl2me"}
  },
  {"event": "model", "step": 3, "finish": "stop"}
]
```

Run trả `completed` dù final không chứa hai URL đã quan sát. Nguyên nhân ở loop:
bản CP3 chấp nhận `finish == stop` khi không còn calls, chưa có điều kiện kiểm
tra URL. System prompt yêu cầu dẫn nguồn nhưng không bảo đảm model thực hiện.

Ở H1 sau cải tiến, hai tool calls vẫn được thực hiện, nhưng final đầu tiên
không qua kiểm tra nguồn và phải sửa trong cùng budget:

```json
[
  {"event": "model", "step": 3, "finish": "stop"},
  {
    "event": "validation_missing_source",
    "step": 3,
    "observed_urls": [
      "https://stspg.io/7pwv28hvkmz8",
      "https://www.cloudflarestatus.com/incidents/yaa0witbl2me"
    ]
  },
  {"event": "model", "step": 4, "finish": "stop"}
]
```

Điều này chứng minh gate đã phát hiện thiếu nguồn và tạo thêm lượt sửa; final
được lưu có cả hai URL. Trace không lưu nội dung draft ở step 3 nên không suy
luận thêm về các câu cụ thể trong draft đó.

Lỗi điều tra vẫn còn: cả hai lần H1 chỉ có hai calls đọc details, chưa đọc
incident gộp `xr3myzj7ms51` dù câu hỏi yêu cầu theo liên kết. Sau cải tiến,
answer còn suy ra khoảng ảnh hưởng tới `updated_at` ngày 07/11 và dùng nó để
nói hai sự cố chồng lấn. `updated_at` có thể là lúc cập nhật hậu kiểm; không đủ
căn cứ coi đó là thời điểm kết thúc ảnh hưởng. Judge vẫn cho 96, minh họa vì sao
phải kiểm tra câu trả lời với trace và không chỉ dựa vào điểm.

## 3. Thay đổi đã thực hiện

- Giữ bản trước cải tiến trong `checkpoints/agent_cp3.py`. Wrapper
  `checkpoints/run_before.py` dùng bản này với nguyên runner/dataset/grading.
- Thêm kiểm tra nguồn vào `agent.py`: lưu URL từ `get_incident_details` có
  `ok: true`. Nếu final không có URL nào trong tập đã quan sát, ghi event
  `validation_missing_source`, thêm yêu cầu sửa rồi gọi model tiếp.
- Lượt sửa vẫn tính vào `max_steps`. Hết budget thì trả `max_steps`, không báo
  `completed` cho câu trả lời chưa đạt gate. Không bắt URL incident khi không có
  lần đọc details thành công.
- Giữ assistant message nguyên vẹn, trả mỗi tool result đúng `tool_call_id`, xử
  lý mọi call trước lượt model tiếp theo. JSON sai, timeout/tool error được trả
  thành observation; lỗi provider và output bị cắt không được báo completed.
- Tests nguồn kiểm tra ba tình huống: sửa thiếu URL trong budget, hết budget,
  và không bắt nguồn sau tool thất bại. `checkpoints/demo.py` minh họa bằng fake
  provider; demo offline không được tính là kết quả eval thật.

Cải tiến này kiểm tra điều kiện tối thiểu về nguồn, không kiểm tra đầy đủ tính
đúng, scope, timeline hoặc việc agent đã đọc mọi incident cần thiết. Phần gate
được chuẩn bị trước khi chạy eval thật; phân tích H1 ở đây là đối chiếu sau chạy,
không khẳng định thay đổi ban đầu được chọn từ một kết quả eval đã có trước đó.

## 4. So sánh hai lần chạy

Hai file có cùng cấu hình: provider và judge provider `openrouter`, agent model
và judge model `openai/gpt-oss-120b`, `max_steps=8`, dataset `core`. Cả hai dùng
snapshot qua cùng runner và đủ **22/22 case được chấm**, không có `unscored`.

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---:|---:|
| Điểm tổng /100 | 89,86 | 93,45 |
| Điểm H1 /100 | 93 | 96 |
| Model calls toàn bộ agent | 66 | 64 |
| Model calls H1 | 3 | 4 |
| Token agent | 78.685 | 76.793 |
| Token judge | 51.941 | 51.062 |
| Chi phí agent được API báo, USD | 0,006472652 | 0,007187163 |
| Chi phí judge được API báo, USD | 0,005138959 | 0,004589208 |
| Tổng chi phí được báo, USD | 0,011611611 | 0,011776371 |

Chi phí trên là tổng các trường `usage.cost` và `grade.judge_usage.cost` có trong
file, không phải xác nhận hóa đơn. A1 trước cải tiến hết bước nên được chấm 0
bằng code, không gọi judge; 21 case còn lại có usage judge. Sau cải tiến cả 22
case có usage judge. Token/cost thay đổi theo response, reasoning, cache và
endpoint; không suy ra chi phí chỉ từ tổng số token.

- Điểm tổng tăng **3,59 điểm**, H1 tăng 3 điểm. Riêng H1 tốn thêm một lượt model
  để sửa nguồn. Tổng số calls toàn bộ bộ eval lại giảm 2 lượt do các case khác
  có quỹ đạo thực thi khác.
- Kết quả cải tiến được xác nhận: H1 có gate ở step 3 và final step 4 có URL.
  Các case E2, E4, A7 và H6 cũng có event `validation_missing_source` ở lần after.
- A1 tăng **0 → 99**, H7 tăng **50 → 100**. Không có bằng chứng để quy toàn bộ
  thay đổi này cho gate nguồn; model/judge có biến động giữa hai lần chạy.
- H6 giảm **100 → 50**: lần after chỉ gọi hai `get_incident_details`, bỏ qua
  `get_status` bắt buộc. `raw_judge_score=92` nhưng mechanical đặt
  `score_cap=50` với lỗi `Chưa gọi tool cần thiết: get_status`. Đây là lỗi chọn
  tool, không phải hết budget hoặc thiếu URL.
- H2 vẫn **50 → 50**, cũng bị trần vì thiếu `get_status`.
- A6 giảm **93 → 83**, trace after chỉ đọc incident đầu, chưa đọc incident liên
  quan. H1 cũng còn thiếu bước theo liên kết như phân tích ở mục 2.
- Hướng cải tiến tiếp theo, chưa triển khai/đánh giá trong hai file này: ưu tiên
  status khi câu hỏi yêu cầu trạng thái component; theo liên kết incident khi
  cần nguyên nhân; phân biệt thời gian update và thời gian ảnh hưởng. Không
  hard-code đáp án hoặc ID để làm từng case pass.

## 5. Giới hạn và kiểm chứng

- Judge LLM là phép đánh giá xấp xỉ; cùng model làm agent và judge có thể tạo
  thiên lệch. H1 được điểm cao vẫn có thiếu sót. Phải đọc `expected`, answer,
  trace và `grade.mechanical`. Điểm eval không tự động là điểm bài lab.
- Mỗi phiên bản chỉ chạy một lần; chưa có cơ sở khẳng định độ ổn định hoặc quan
  hệ nhân quả giữa source gate và toàn bộ mức tăng điểm.
- Snapshot GitHub/Cloudflare được lưu ngày 09/11/2026; ba dịch vụ bổ sung ngày
  10/11/2026. Dữ liệu không chứng minh tình trạng hiện tại ngoài thực tế.
- Tools bài chính chỉ tìm trong 50 incident gần nhất; trả tối đa 5 incident khớp.
  Details chỉ giữ hai update mới nhất và update đầu tiên, mỗi body tối đa 900 ký
  tự. Không tìm thấy không chứng minh không tồn tại; output có thể bị cắt.
- Gate bài chính chỉ bắt ít nhất một URL incident đã quan sát, không bảo đảm
  mọi provider, mọi incident hay mọi claim đều có nguồn phù hợp.
- Tests offline đã chạy đạt: **41 tests** trong `tests/`, **10 tests** trong
  `bonus/`. Chúng chứng minh cơ chế theo kịch bản kiểm thử, không chứng minh năng
  lực điều tra của model ở mọi tình huống thực tế.

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s bonus -p 'test_*.py' -v
python checkpoints/compare.py
```

## Bonus — kết quả và bằng chứng

### Cấu hình và điểm

`eval_bonus.json`: provider và judge `openrouter`, model và judge model
`openai/gpt-oss-120b`, `max_steps=16`, dataset `bonus`, snapshot. Đủ **10/10 case
được chấm**, không `unscored`; điểm bộ bonus **88,8/100**, quy đổi tham khảo
**13,32/15**. B10 hết bước vẫn là case được chấm 0, không phải unscored.

| Case | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 | B10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Điểm | 100 | 100 | 100 | 100 | 91 | 100 | 97 | 100 | 100 | 0 |

Tổng agent: **53 model calls**, **134.784 token**, chi phí được báo
**0,007829641 USD**. Judge của 9 case hoàn tất: **31.753 token**, chi phí được
báo **0,002383746 USD**; B10 chấm bằng code. Tổng chi phí được báo
**0,010213387 USD**. Đây không phải điểm bonus cuối cùng do giảng viên xác nhận.

### Triển khai

- Agent lấy `tools.schemas` và `tools.system_prompt`, dùng được 5 provider mà
  không hard-code ID incident trong quyết định agent. `bonus/agent_policy.py`
  bổ sung policy; không thay đổi fixtures, scenarios, cases hoặc grading.
- Retry do model quyết định sau khi nhận observation. Code giới hạn 3 lỗi 429
  liên tiếp/provider, chờ Retry-After số giây hoặc HTTP-date, tổng budget chờ
  5 giây/run. Header không hợp lệ/không có thì backoff 1/2/4 giây. Nếu vượt
  budget thì chặn gọi sớm và yêu cầu báo thiếu dữ liệu.
- Cùng tool/arguments lỗi bị giới hạn 3 lần thực thi. Request bị chặn được ghi
  `tool_skipped` và vẫn có tool result đúng call ID; không tính là request API.
- Chỉ bỏ list `distractors` khỏi context. Raw result vẫn trong trace; ghi
  `context_compacted` và số bản ghi bị bỏ. Nguồn, timestamp, scope và updates
  được giữ lại. Chưa có bộ lọc ngữ nghĩa tổng quát cho mọi dạng dữ liệu nhiễu.
- Pagination vẫn do model chọn theo nhu cầu câu hỏi. Observation nhắc đọc
  `next_offset`, không tuyên bố đã đọc hết khi còn trang. Source gate bonus bắt
  URL theo từng provider đã đọc details thành công; status-only dựa vào prompt
  và eval. Cơ chế này không tự xác minh mọi claim hoặc mọi lần chống injection.

### Trace thật tiêu biểu

| Case | Bằng chứng từ trace | Kết quả/giới hạn |
|---|---|---|
| B2 | Step 2 đọc Vercel `sps6n39gm4sg`, offset 0, limit 3; step 3 đọc offset 3, limit 3 | Đọc tới trang chứa update cần tìm, đạt 100; không cần tuyên bố đã đọc hết timeline |
| B3 | `get_vercel_status` step 1 trả `RATE_LIMITED`, step 2 thành công; step 3 final | Retry thành công, đạt 100; delay giả lập là 0, không chứng minh đã chờ HTTP thật |
| B4 | GitHub step 1 thành công; Vercel steps 2–4 đều 429; step 5 final | Dừng sau 3 lần, vẫn báo GitHub và chưa biết Vercel, đạt 100 |
| B5 | Step 1 `INVALID_ARGUMENTS`; step 2 dùng offset 0/limit 2 thành công; step 3 đọc offset 2 | Phục hồi tham số, đạt 91; judge nhận xét final chưa nêu rõ lỗi lần đầu |
| B6 | `context_compacted` step 1 ghi `omitted_records: 160`; đọc details Vercel và npm | Giữ trace gốc, rút context, có hai nguồn; đạt 100 |
| B7 | Step 1 component null lỗi; step 2 arguments rỗng thành công | Không xuất marker injection trong final, đạt 97; chỉ là một tình huống kiểm thử |

Retry-After thật, việc chặn lần thực thi thứ tư và trả đúng ID được kiểm tra
thêm bằng unit tests mock; không mô tả chúng là kết quả HTTP live trong eval.

### Lỗi còn lại ở B10

B10 nhận đủ năm status providers nhưng trả `status=max_steps`, `answer` rỗng,
**0 điểm**. Trace cho thấy 16 model calls đều tiếp tục gọi tool:

```text
step 1:  get_github_status
step 2–3: đọc hai trang GitHub incident
step 4:  get_npm_status
step 5–6: đọc hai trang npm incident
step 7:  get_vercel_status → RATE_LIMITED
step 8:  get_vercel_status → thành công
step 9:  get_incident_details(vercel) → RATE_LIMITED
step 10–11: đọc hai trang Vercel incident
step 12: get_cloudflare_status
step 13–14: đọc hai trang Cloudflare incident
step 15: get_digitalocean_status
step 16: get_incident_details(digitalocean) → thành công
hết budget: không còn lượt model để tổng hợp final answer
```

Nguyên nhân có thể xảy ra: model đào sâu từng incident trước khi tổng hợp,
kết hợp hai lần 429 làm dùng hết 16 bước. Vấn đề còn lại là phân bổ budget và
điều kiện dừng điều tra, không phải bỏ sót provider hoặc bịa outage. Chưa có
policy dành lượt cuối cho câu trả lời, và chưa có kết quả chạy lại chứng minh
đã sửa B10. Hướng tiếp theo là ưu tiên tổng quan, chỉ đọc chi tiết khi câu hỏi
cần và dành budget cho final; không chỉ tăng max_steps để che giới hạn.

## Lệnh tái hiện và chuẩn bị demo

Giữ nguyên model và cấu hình đã nêu; đặt key trong terminal, không đưa vào repo.

```powershell
python checkpoints/run_before.py --max-steps 8 --output eval_before.json
python evals/run_evals.py --max-steps 8 --output eval_after.json
python checkpoints/compare.py
python evals/run_evals.py --bonus --max-steps 16 --output eval_bonus.json
```

Các lệnh eval ghi lại file kết quả, tốn token và có thể cho điểm khác lần đã
phân tích. Nếu chạy lại và thay file, cần cập nhật số liệu/trace trong NOTES.
Khi demo có thể dùng H1 để trình bày tool-call IDs và sửa thiếu nguồn, B2 để
trình bày pagination, B4 để trình bày partial failure và B10 để nêu lỗi còn lại.
