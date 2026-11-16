# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: b46ebf8
- Run id dẫn chứng: R-workflow-C-002-s55 (ticket nói trễ 5 ngày, order row 2 ngày → workflow `denied`; swarm cùng claim cùng seed R-swarm-C-002-s55 trả `resolved`), R-workflow-C-014-s11 (T14, ledger 120000), src/reports/benchmark.json
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (70 trial, 14 claim × seed 11,22,33,44,55)
- Cost per success (mô phỏng, VND): 28.80 (single 40.24, orchestrator 57.85, swarm 49.57)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên bộ public (ma trận student T01–T14 248/248, `tests/test_workflow_extra.py`)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

Số liệu benchmark (`src/reports/benchmark.json`, commit b46ebf8, MockLLM, 14 claim public × 5 seed, SQLite mới cho mỗi trial):

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Steps TB | Model calls TB |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 28.80 | 4.43 | 1.00 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 40.24 | 11.57 | 5.64 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 57.85 | 2.79 | 2.79 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 | 3.00 |

## Vì sao shape này

Trên cùng 14 claim public × 5 seed (11, 22, 33, 44, 55) và cùng bảng giá, ba shape nhóm viết đều đạt pass rate 1.000, pass^5 1.000 và variance 0. Độ chính xác vì vậy không phân biệt được chúng, nên tiêu chí quyết định là mức tự chủ và chi phí. Workflow rẻ nhất: 28.80 VND mỗi lần thành công, so với 40.24 của single (gấp khoảng 1,4 lần), 57.85 của orchestrator (khoảng 2,0 lần) và 49.57 của swarm (khoảng 1,7 lần). Swarm còn là shape duy nhất có lỗi (T02 ở seed 55). Workflow cũng là shape ít tự chủ nhất: mọi quyết định tiền đều nằm ở `compute_compensation` và cổng `durability.issue_refund`, MockLLM chỉ soạn câu trả lời từ một chuỗi trạng thái cố định (1 model call mỗi claim). Luật nghiệp vụ của LogiX-VN là luật cứng (ngưỡng 3 ngày, `is_current`, trần theo đơn), không có bước nào cần suy luận mở, nên thêm tự chủ chỉ thêm chi phí và chỗ có thể biến thiên.

## Có đáng đổi lấy multi-agent không

Không, với dữ liệu hiện có. Trên bộ public, single và orchestrator không thắng workflow ở claim nào mà tốn hơn 1,4–2,0 lần. Swarm thua đúng ở chỗ nó tin số ngày trễ ghi trong ticket (T02, seed 55) thay vì dòng order, tức là thêm tự chủ đã tạo ra lỗi chứ không sửa lỗi. Kể cả nếu một shape multi-agent nhỉnh hơn vài phần trăm pass rate, nhóm vẫn giữ workflow nếu shape đó có cost cao hơn và variance > 0, vì một lần refund sai là mất tiền thật. Quyết định sẽ đảo lại khi: (1) claim có dữ kiện phi cấu trúc mà code không đọc được (ảnh hàng hỏng, hội thoại nhiều lượt, policy viết bằng văn xuôi cần diễn giải); (2) số loại tình huống tăng tới mức nhánh `if` không còn bảo trì nổi; hoặc (3) bộ hidden cho thấy workflow fail một nhóm claim mà agent đọc tool linh hoạt xử lý được, với cost/success vẫn chấp nhận được.

## Trace và bằng chứng

Trace của workflow (`src/traces/R-workflow-<claim>-s<seed>.json`, ghi bằng `lab8.trace.Trace`) có các event: `claim` (chỉ `found` và `has_order_id`), `lookup_order` (view đã allowlist: order_id, status, delay_days, shipping_fee_vnd, paid_vnd, damage_verified, carrier), `quote` (amount, reason, clause_ids, parts), `issue_refund` (ok, reason, conflict), `crash` khi bị inject crash, và `decision` (status, proposal_amount, reason). Cố ý **không** ghi: nội dung ticket (dữ liệu người dùng, có thể chứa lệnh giả hoặc PII), `parent_secret` và `raw_headers` (chỉ có trong claim row, mà shape không bao giờ `SELECT *`), principal_id, SĐT, địa chỉ, tên hàng, ghi chú nội bộ (đã bị `lookup_order` loại). Prompt gửi MockLLM chỉ là `status=<...>`, test `test_model_never_sees_ticket_text` kiểm điều này. Trace luôn nằm trong `traces/` với tên bắt đầu bằng `run_id`, đúng chỗ scanner quét; shape không ghi gì ra stdout. Nếu trace nằm ngoài chỗ scanner quét được thì không chứng minh được là sạch, vì vậy nhóm không ghi log ở nơi nào khác.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75. Corpus public chỉ có 14 claim nên pass rate 1.000 không chứng minh workflow đúng trên mọi trường hợp; bộ hidden 40 claim mới là thước đo chính. Cost là VND mô phỏng theo `config/pricing.yaml`, không phải hóa đơn API thật. Ưu thế của workflow phụ thuộc vào việc luật nghiệp vụ được mã hóa đầy đủ trong `compute_compensation`; nếu luật đổi mà code không đổi theo thì workflow sai một cách nhất quán trên mọi seed.
