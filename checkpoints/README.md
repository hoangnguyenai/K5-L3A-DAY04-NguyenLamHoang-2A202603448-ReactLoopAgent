# Lệnh chạy từng checkpoint còn lại (PowerShell)

Các script này không push, không sửa dữ liệu hay grading và không tạo điểm giả.
Chạy tại thư mục gốc repo. Cấu hình API trong cùng terminal trước khi gọi LLM.

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PROVIDER = 'openrouter'
# MODEL: ID chính xác của model hỗ trợ tool calling mà bạn chọn.
# OPENROUTER_API_KEY: đặt key mới trực tiếp trong terminal, không chụp/chia sẻ key.
# Không mặc định model có giá $0 nếu không kiểm tra giá trên OpenRouter.
```

## CP3 — Xử lý lỗi và trace

```powershell
python -m unittest discover -s tests -p test_lab.py -v
python -m unittest discover -s tests -p test_agent_errors.py -v
```

Đọc tests để thấy JSON sai được trả lại bằng INVALID_ARGUMENTS; timeout tool
là observation có đúng ID; lỗi provider kết thúc run và giữ trace trước đó;
output bị cắt không được báo completed. Một step là một model call.

## CP4 — Eval trước cải tiến

`agent.py` hiện là phiên bản sau cải tiến. Vì vậy, lần before dùng bản CP3
được lưu ở `checkpoints/agent_cp3.py` (chưa có source gate). Wrapper chỉ thay
hàm agent được runner gọi; dùng nguyên runner, dataset, scenarios và grading.

```powershell
# Kiểm tra kết nối với một case trước (không phải kết quả đủ bộ).
python checkpoints/run_before.py --case E2 --max-steps 8 --output eval_results_smoke.json
# Nếu smoke chạy được, chạy đủ bộ.
python checkpoints/run_before.py --max-steps 8 --workers 1 --output eval_before.json
# Đọc summary và lý do chấm từng case.
python -c 'import json; d=json.load(open("eval_before.json",encoding="utf-8")); print(json.dumps(d["summary"],ensure_ascii=True,indent=2)); print(json.dumps([{ "id":c["id"], "grade":c["grade"] } for c in d["cases"]],ensure_ascii=True,indent=2))'
```

Cần đủ 22 case, summary.score_0_100 khác null. max_steps được chấm 0; error
có thể dẫn tới unscored. Sửa cấu hình khi có lỗi hạ tầng, không sửa điểm bằng tay.
Model free có quota; mỗi case có thể gọi model nhiều lần và thêm một lần judge.
Nếu quota chưa đủ thì cần chờ reset, không coi một phần bộ eval là đủ 22 case.

## CP5 — Kiểm tra cải tiến nguồn

```powershell
python -m unittest discover -s tests -p test_validation.py -v
python -m unittest discover -s tests -v
python checkpoints/demo.py
```

Demo dùng FakeProvider và snapshot thật, không gọi API. CP3 chấp nhận câu trả lời
thiếu URL; CP5 ghi validation_missing_source, yêu cầu sửa, sau đó mới completed.
Đây là bằng chứng offline về cơ chế, không thay thế eval của model thật.

Source gate chỉ bắt ít nhất một URL đã quan sát khi có get_incident_details
thành công; không kiểm chứng mọi claim, mọi incident hay độ đúng của câu trả lời.
Đối chiếu file eval before để phân tích lỗi thật trong NOTES trước khi chạy after.
Nếu lỗi chính của case khác với thiếu nguồn, ghi rõ và cân nhắc cải tiến bổ sung.

## CP6 — Eval sau cải tiến, so sánh

Giữ nguyên PROVIDER, MODEL, judge provider/model và max steps của lần before.
Không dùng bộ định tuyến chọn ngẫu nhiên model để so sánh hai phiên bản.

```powershell
python evals/run_evals.py --max-steps 8 --workers 1 --output eval_after.json
python checkpoints/compare.py
```

Lệnh compare kiểm tra đủ case, cùng config, không unscored; tạo CP_COMPARISON.md
với điểm, model calls, token/cost do provider trả, điểm từng case và trace case
thấp điểm nhất. Không ghi đè NOTES hoặc thay đổi hai file eval.

Điền đủ 5 mục NOTES từ kết quả này: case, evidence, thay đổi, so sánh, giới hạn.
Không nhận xét tăng điểm/đã sửa lỗi nếu bằng chứng thực tế không chứng minh điều đó.

## CP7 — Demo và chuẩn bị nộp

```powershell
python checkpoints/demo.py
python run.py --max-steps 8 'Theo snapshot, kiểm tra GitHub Actions và đọc chi tiết một incident liên quan. Nêu trạng thái, thời gian dữ liệu, nguồn và giới hạn.'
python -m unittest discover -s tests -v
python checkpoints/compare.py
git diff --check
git status --short
git ls-files .env
```

`git ls-files .env` phải không in gì. Kiểm tra NOTES đã đủ 5 mục và không có key
trong code, trace, screenshot hay file eval. Repo public, tên đúng, link mở được
khi chưa đăng nhập. Việc commit/push và nộp LMS do bạn thực hiện theo SUBMISSION.md;
các lệnh ở đây không push. CP7 chỉ hoàn thành sau demo và nộp link thực tế.

Bonus không bắt buộc và chưa chạy eval trong quy trình này.
