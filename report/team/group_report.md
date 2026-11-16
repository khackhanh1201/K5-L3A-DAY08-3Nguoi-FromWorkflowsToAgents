# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: 3Nguoi
- Thành viên: xem `TEAM.md` (Nguyễn Khắc Khánh — nhóm trưởng, Mai Văn Thanh, Kiều Văn Thắng)
- Commit chốt (trùng `report/team/decision_adr.md`): b46ebf8

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc có cùng chữ ký `run_claim`, rồi dùng số đo để chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc**. Cách nhóm hiểu ranh giới: số tiền, approval, trần theo đơn và chống ghi trùng là việc của **code** (`compute_compensation` và host `durability.issue_refund`); model chỉ được đọc và soạn chữ. Chữ trong ticket là dữ liệu người dùng, không phải nguồn sự thật và không phải lệnh.

Chia việc (chi tiết trong `TEAM.md`): mỗi người một shape, cộng thêm một phần việc chung.

| Người | Shape | Việc chung |
| --- | --- | --- |
| Khánh | A `workflow` | Integration và merge, crash suite, benchmark 4 shape, ADR |
| Thanh | B `single` | Rà các nhánh approval và policy (T01–T14), research card và ablation |
| Thắng | C `orchestrator` | Handoff theo allowlist, an toàn trace và secret |

Thứ tự làm: (1) cả nhóm đọc `docs/business_rules.md`, `docs/contracts.md` và `swarm_reference.py`; (2) workflow làm trước vì đơn giản nhất, làm mẫu cho cách gọi host và ghi trace; (3) single và orchestrator làm song song trên branch riêng; (4) nhóm trưởng merge, chạy lại toàn bộ test, crash suite và benchmark trên commit tích hợp.

## 3. Giải pháp

Ba shape có chung khung: đọc claim qua `get_claim_view` (không `SELECT *`, nên `parent_secret` và `raw_headers` không bao giờ vào bộ nhớ của shape); thiếu `order_id` → `needs_info`; `lookup_order` không thấy đơn hoặc sai principal → `escalated`; quote bằng `compute_compensation` từ order row và policy hiện hành; quote 0 → `denied` mà không gọi host; quote > 0 → gọi `durability.issue_refund` với **quote đầy đủ** và truyền `crash_at`. Host tự kiểm approval của chính claim đó, trừ phần đơn đã được hoàn và chống ghi trùng bằng khóa `refund:{claim_id}`. Kết quả host quyết định status: `ok` → `resolved`, từ chối → `denied` (host ghi audit `policy_denied`), conflict → `failed`. Khi bị `InjectedCrash`, cả ba shape ghi trace rồi ném lỗi tiếp, không nuốt lỗi. Mọi nhánh return đều đi qua `lab8.shapes.common.finish()`.

| | A `workflow` | B `single` | C `orchestrator` |
| --- | --- | --- | --- |
| Ai chọn bước tiếp theo | Code, thứ tự cố định | Agent ReAct qua `run_react`, tối đa 8 bước | Orchestrator giao việc cho investigator |
| Tool model được dùng | Không có | 4 tool đọc: `get_claim_view`, `lookup_order`, `lookup_refund_history`, `compute_compensation`; tool khác → `ToolRejected` → `failed` | Investigator: `lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation` (đều chỉ đọc) |
| Model nhìn thấy gì | Chuỗi `status=<...>` để soạn trả lời | Trạng thái có cấu trúc (`order_visible`, quote…), không có ticket | Tên task và claim_id để giao việc, rồi status để soạn trả lời |
| Ai gọi `issue_refund` | Code của shape | Code của shape, sau vòng lặp | Orchestrator |
| Model call trung bình | 1.00 | 5.64 | 2.79 |

**Handoff (shape C).** Orchestrator dựng handoff bằng `lab8.handoff.make_handoff` với `facts={}` và `allowed_tools` chỉ gồm tool đọc. Không có ticket, claim row, `parent_secret` hay header nào được đưa vào handoff; investigator tự tra đơn bằng `principal_id` mà orchestrator truyền thẳng vào `run_readonly_investigators` chứ không qua handoff. Nhóm không dùng tóm tắt bằng LLM để "làm sạch" parent context, vì tóm tắt không phải redaction: model vẫn có thể chép lại secret. Cách đúng là allowlist field. Test `test_orchestrator_handoff_is_readonly_and_trace_has_no_canary` kiểm tra handoff không có write tool và artifact không chứa `CANARY_SECRET_*`.

**Trace.** Cả ba shape dùng `lab8.trace.Trace`, ghi vào `src/traces/<run_id>.json`. Các event chính:

- `claim`: chỉ ghi `found` và `has_order_id`.
- `lookup_order` / `observe` / `investigator`: chỉ ghi view đã allowlist của order (order_id, status, delay_days, phí, paid, damage_verified, carrier), hoặc `visible` và `reason`.
- `handoff` (C): handoff đã sanitize.
- `quote`: amount, reason, clause_ids.
- Kết quả host: `ok`, `reason`, `conflict`.
- `crash`, `decision`.

Cố ý **không** ghi: nội dung ticket, `principal_id`, claim row và order row thô, `parent_secret`, header, SĐT, địa chỉ, tên hàng, ghi chú nội bộ, chữ do model soạn.

## 4. Kết quả

Benchmark trên bộ public (`src/reports/benchmark.json`, commit b46ebf8): 14 claim × seed 11, 22, 33, 44, 55 = 70 trial mỗi shape, MockLLM, bảng giá `config/pricing.yaml`, SQLite mới cho mỗi trial.

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Steps TB | Steps p95 | Model calls TB | Tool calls TB |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 28.80 | 4.43 | 5 | 1.00 | 2.79 |
| B single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 40.24 | 11.57 | 13 | 5.64 | 3.64 |
| C orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 57.85 | 2.79 | 3 | 2.79 | 5.57 |
| D swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 | 3 | 3.00 | 4.66 |

*Steps là số event trong trace (metric `steps` của grader), không phải số bước ReAct.*

- Swarm fail đúng 1/70 trial: `R-swarm-C-002-s55`, lý do `status resolved != denied`. Ticket ghi trễ 5 ngày, order row ghi 2 ngày; ở seed % 5 == 0 swarm tin ticket và trả 20.000 cho một claim phải `denied`. Cả ba shape nhóm viết đều `denied` claim này trên mọi seed.
- Crash safety: **20/20** (`src/reports/crash.json`).
- Ma trận student T01–T14: **248/248 passed** (62 test mỗi shape × 4). Cổng host `python -m pytest -q`: **100 passed** (54 test gốc và 46 test nhóm thêm).
- Secret leak / approval bypass trên bộ public: 0 / 0. Test của từng shape kiểm trace không chứa `CANARY_SECRET_*`, ticket hay PII; các nhánh approval hỏng, hết hạn, sai claim và đơn đã hoàn đủ đều bị host từ chối, có audit `policy_denied`.
- Chưa có kết quả tự kiểm trên `student_drop/` trong repo.

**Quyết định:** chọn **workflow**. Ba shape nhóm viết đều đúng 100% nên độ chính xác không phân biệt được chúng; workflow rẻ nhất (28.80 VND, so với 40.24 của single và 57.85 của orchestrator) và ít tự chủ nhất. Lý do đầy đủ và điều kiện làm quyết định đảo lại nằm trong `report/team/decision_adr.md`. Phiếu nghiên cứu (R2 · MAST) và ablation single vs swarm nằm trong `report/team/research_card.md`: lỗi của swarm thuộc nhóm lỗi kiểm chứng, và đổi sang topology chỉ lấy delay từ `lookup_order` thì lỗi này về 0.

## 5. Khó khăn và cách xử lý

- **Conflict khi merge `TEAM.md`.** Cả ba người cùng sửa bảng đóng góp trên branch riêng, nên merge branch của Thanh và của Thắng đều conflict ở `TEAM.md`. Nhóm trưởng gộp tay thành một bảng đủ 3 dòng kèm hash commit của từng người. Code không conflict, vì quy ước mỗi người chỉ sửa file shape của mình.
- **Trình định dạng Markdown làm hỏng nội dung.** Branch của Thanh chạy formatter trên `TEAM.md`, biến `approval_bypass` thành `approval\*bypass` và `` `CANARY_SECRET_*` `` thành `` `CANARY_SECRET*\*` ``. Nhóm sửa lại lúc merge và kiểm tra `check_submission` vẫn đọc được bảng đóng góp.
- **Khác phiên bản Python.** Thắng chạy test trên Python 3.14, ngoài dải 3.11–3.13 mà repo hỗ trợ. Sau khi merge, nhóm chạy lại toàn bộ test trên Python 3.12.3: 100/100 test host và 248/248 test student đều xanh.
- **Xuống dòng CRLF trên Windows.** Chạy lại `lab8.crash_test` làm git báo `crash.json` thay đổi. Kiểm tra bằng `git diff --ignore-cr-at-eol` thì nội dung không đổi; `.gitattributes` (`eol=lf`) chuẩn hóa khi commit.
- **Cám dỗ tự trừ phần đã hoàn.** Ở T13 và T14, cách tự nhiên là shape tự trừ phần đơn đã được hoàn rồi mới gọi host. Như vậy T14 bị trừ hai lần, còn T13 bị shape tự từ chối nên không có audit `policy_denied`. Cả ba shape đều truyền quote đầy đủ; `lookup_refund_history` chỉ dùng để ghi trace.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

| Người | Commit chính | Test đã thêm | Báo cáo cá nhân |
| --- | --- | --- | --- |
| Nguyễn Khắc Khánh | `37a7215`; các merge `0ba70b3`, `cdbcd4c`, `b46ebf8` | `src/tests/test_workflow_extra.py` (18 test) | `report/team/2A202603472_NguyenKhacKhanh.md` |
| Mai Văn Thanh | `0c56fac`, `0d2436e` | `src/tests/test_single_extra.py` (27 test) | `report/team/2A202603696_MaiVanThanh.md` |
| Kiều Văn Thắng | `3677756` | `src/tests/test_orchestrator_handoff.py` | `report/team/2A202603424_KieuVanThang.md` |

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Ngoài ra:

- **Mẫu nhỏ.** Bộ public chỉ có 14 claim; chênh 0.014 pass rate giữa swarm và các shape khác tương ứng đúng một trial. Pass rate 1.000 không chứng minh shape đúng trên mọi trường hợp; bộ hidden 40 claim × 5 seed mới là thước đo chính.
- **Single và orchestrator đúng tuyệt đối vì `decide()` là policy cố định.** Với LLM thật, rủi ro chuyển sang việc model chọn sai thứ tự tool, dừng sớm hoặc hết 8 bước. Nhóm đã chặn bằng code (chỉ tool đọc, trần bước, tiền do code tính) nhưng chưa đo được.
- **Lỗi của swarm là điểm yếu cài sẵn** (`REFERENCE_WEAKNESS`), nên so sánh chỉ cho thấy topology có bước kiểm chứng bằng code chặn được lỗi loại này, không ước lượng được tần suất lỗi của model thật.
- **Cost là VND mô phỏng** theo `pricing.yaml`. Thứ tự cost giữa các shape phụ thuộc số model call và độ dài prompt; với giá token thật, khoảng cách có thể khác.
- **Workflow phụ thuộc vào việc luật được mã hóa đủ** trong `compute_compensation`. Nếu luật đổi mà code không đổi theo, workflow sai giống nhau trên mọi seed.

Kết luận đổi khi: claim có dữ kiện phi cấu trúc (ảnh, hội thoại nhiều lượt, policy viết bằng văn xuôi); số loại tình huống tăng tới mức nhánh `if` không bảo trì được; hoặc bộ hidden cho thấy workflow fail một nhóm claim mà agent đọc tool linh hoạt xử lý được với cost chấp nhận được.

Hướng cải thiện: chạy tự kiểm trên `student_drop/` để có số liệu ngoài bộ public; thêm metamorphic test (đổi thứ tự claim, nhân đôi claim, đổi chữ trong ticket) cho cả ba shape; thử một bonus topic trong `docs/bonus_topics.md`, ví dụ swarm có bước kiểm chứng delay bằng order row.

## 8. Tài liệu tham khảo

- Đề bài và contract của lab: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
- Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* (MAST), NeurIPS 2025 Datasets & Benchmarks, arXiv:2503.13657. Dùng cho research card (R2).
- Code tham chiếu: `src/lab8/shapes/swarm_reference.py`.
- Bằng chứng: `src/reports/benchmark.json`, `src/reports/crash.json`, `report/team/decision_adr.md`, `report/team/research_card.md`.
