# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash:
- Run id dẫn chứng:
- Pass rate / pass^5 / seed min-max / variance:
- Cost per success (mô phỏng, VND):
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên bộ public (test `tests/test_workflow_extra.py`, ma trận student T01–T14)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

<!-- NHÁP (Khánh): 4 dòng còn trống điền sau khi merge single + orchestrator và chạy lại
     python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
     Số sơ bộ (workflow vs swarm, 14 claim × 5 seed, chưa commit):
     workflow pass 1.000 / pass^5 1.000 / min-max 1.000–1.000 / var 0.000000 / cost/success 28.80
     swarm    pass 0.986 / pass^5 0.929 / min-max 0.929–1.000 / var 0.000816 / cost/success 49.57 -->

## Vì sao shape này

Trên cùng 14 claim public × 5 seed (11, 22, 33, 44, 55) và cùng bảng giá, workflow đạt pass rate 1.000, pass^5 1.000, variance 0 giữa các seed, với cost/success 28.80 VND mô phỏng. Swarm tham chiếu đạt 0.986, pass^5 0.929 và tốn 49.57 VND mỗi lần thành công (cao hơn khoảng 1,7 lần). Workflow là shape ít tự chủ nhất: mọi quyết định tiền đều nằm ở `compute_compensation` và cổng `durability.issue_refund`, MockLLM chỉ soạn câu trả lời từ một chuỗi trạng thái cố định. Luật nghiệp vụ của LogiX-VN là luật cứng (ngưỡng 3 ngày, `is_current`, trần theo đơn), không có bước nào cần suy luận mở, nên thêm tự chủ không mang lại gì mà chỉ thêm biến thiên. *(Bổ sung số của single và orchestrator sau benchmark đầy đủ.)*

## Có đáng đổi lấy multi-agent không

Không, với dữ liệu hiện có. Swarm thua đúng ở chỗ nó tin số ngày trễ ghi trong ticket (T02, seed 55) thay vì dòng order, tức là thêm tự chủ đã tạo ra lỗi chứ không sửa lỗi. Kể cả nếu một shape multi-agent nhỉnh hơn vài phần trăm pass rate, nhóm vẫn giữ workflow nếu shape đó có cost cao hơn và variance > 0, vì một lần refund sai là mất tiền thật. Quyết định sẽ đảo lại khi: (1) claim có dữ kiện phi cấu trúc mà code không đọc được (ảnh hàng hỏng, hội thoại nhiều lượt, policy viết bằng văn xuôi cần diễn giải); (2) số loại tình huống tăng tới mức nhánh `if` không còn bảo trì nổi; hoặc (3) bộ hidden cho thấy workflow fail một nhóm claim mà agent đọc tool linh hoạt xử lý được, với cost/success vẫn chấp nhận được.

## Trace và bằng chứng

Trace của workflow (`src/traces/R-workflow-<claim>-s<seed>.json`, ghi bằng `lab8.trace.Trace`) có các event: `claim` (chỉ `found` và `has_order_id`), `lookup_order` (view đã allowlist: order_id, status, delay_days, shipping_fee_vnd, paid_vnd, damage_verified, carrier), `quote` (amount, reason, clause_ids, parts), `issue_refund` (ok, reason, conflict), `crash` khi bị inject crash, và `decision` (status, proposal_amount, reason). Cố ý **không** ghi: nội dung ticket (dữ liệu người dùng, có thể chứa lệnh giả hoặc PII), `parent_secret` và `raw_headers` (chỉ có trong claim row, mà shape không bao giờ `SELECT *`), principal_id, SĐT, địa chỉ, tên hàng, ghi chú nội bộ (đã bị `lookup_order` loại). Prompt gửi MockLLM chỉ là `status=<...>`, test `test_model_never_sees_ticket_text` kiểm điều này. Trace luôn nằm trong `traces/` với tên bắt đầu bằng `run_id`, đúng chỗ scanner quét; shape không ghi gì ra stdout. Nếu trace nằm ngoài chỗ scanner quét được thì không chứng minh được là sạch, vì vậy nhóm không ghi log ở nơi nào khác.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75. Corpus public chỉ có 14 claim nên pass rate 1.000 không chứng minh workflow đúng trên mọi trường hợp; bộ hidden 40 claim mới là thước đo chính. Cost là VND mô phỏng theo `config/pricing.yaml`, không phải hóa đơn API thật. Ưu thế của workflow phụ thuộc vào việc luật nghiệp vụ được mã hóa đầy đủ trong `compute_compensation`; nếu luật đổi mà code không đổi theo thì workflow sai một cách nhất quán trên mọi seed.
