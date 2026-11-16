# Báo cáo cá nhân — 2A202603696_MaiVanThanh

## 1. Thông tin thành viên

- Họ tên: Mai Văn Thanh
- MSSV: 2A202603696
- Email: 26ai.thanhmv2@vinuni.edu.vn
- GitHub: https://github.com/MaiVanThanhDev

## 2. Phần việc phụ trách

- Shape B `single`: [src/lab8/shapes/single.py](../../src/lab8/shapes/single.py), một agent ReAct, tối đa 8 bước.
- Policy / approval: rà các nhánh approval hỏng (thu hồi, hết hạn, không có), approval của claim khác, đơn đã hoàn đủ (T13), chỉ hoàn phần chênh (T14), policy cũ/tương lai, ticket ghi sai số ngày trễ.
- Báo cáo: [report/team/research_card.md](research_card.md) (R2 · MAST, ablation single vs swarm).

## 3. Đóng góp cụ thể

**Commit chính:** `0c56fac` — `feat(single): implement Shape B ReAct agent with read-only tools and host-gated refund` (branch `K5_L3A_Day8_MaiVanThanh_2A202603696`).

**Thiết kế shape single:**

- Vòng lặp dùng `lab8.runtime.run_react(..., max_steps=8, worker=True)`. Mỗi lần `decide()` là một lời gọi MockLLM (`purpose="react"`) được tính vào `Budget`, cộng một lời gọi `draft` cuối để soạn chữ trả lời.
- `decide()` chỉ được chọn 4 tool đọc: `get_claim_view → lookup_order → lookup_refund_history → compute_compensation`. Chọn tool khác thì ném `ToolRejected`, shape trả `failed / tool_rejected`; `worker=True` làm `dispatch` chặn thêm một lớp nữa.
- Ranh giới code / model: model không thấy ticket (prompt chỉ chứa trạng thái có cấu trúc như `order_visible`, `quote`), nên câu như "ignore policy" hay "trễ 9 ngày" không điều khiển được agent. Mã đơn lấy từ `get_claim_view`, số ngày trễ từ `lookup_order`, tiền từ `compute_compensation` (chỉ dùng policy `is_current` và `effective_date <= as_of`).
- Sau vòng lặp, **code** (không phải model) gọi `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)` và không bắt `InjectedCrash` (ghi trace rồi ném lại).
- **Vì sao truyền quote đầy đủ:** host tự trừ phần đơn đã được hoàn (`order_refunded_vnd`). Agent có đọc `lookup_refund_history` nhưng chỉ để ghi trace; nếu tự trừ thì T14 bị trừ hai lần (150.000 − 30.000 − 30.000), và ở T13 shape tự từ chối thì không có audit `policy_denied`.
- **Trace cố ý không ghi:** ticket, `principal_id`, claim row và order row thô, `parent_secret`, header, nội dung chữ do model soạn. Chỉ ghi field allowlist của order (`status`, `delay_days`, phí, `damage_verified`, `carrier`), quote, và kết quả host (`ok`, `reason`, `conflict`).

**Test đã thêm:** [src/tests/test_single_extra.py](../../src/tests/test_single_extra.py), 27 test:

| Test | Kiểm tra |
| --- | --- |
| `test_broken_approval_is_denied_by_host_with_audit` | approval `revoked` / hết hạn → `denied`, proposal = quote, có `policy_denied` |
| `test_approval_issued_for_another_claim_does_not_count` | claim trỏ tới approval của C-001 → `approval_claim_mismatch` |
| `test_missing_approval_row_is_denied` | claim không có approval → `missing_approval` |
| `test_order_already_refunded_passes_full_quote_and_gets_denied` | T13 trên 5 seed |
| `test_top_up_pays_only_the_difference` | T14: proposal 150.000, ledger 120.000 trên 5 seed |
| `test_ticket_that_overstates_delay_is_ignored_on_every_seed` | C-002 (lỗi của swarm ở seed 55) đúng trên cả 5 seed |
| `test_superseded_and_future_clauses_in_ticket_do_not_pay` | ticket dẫn `SHIP-LATE-OLD` / `SHIP-LATE-FUTURE` → `denied`, proposal 0 |
| `test_agent_cannot_pick_a_write_tool` | agent cố chọn `issue_refund` → `failed`, không có dòng ledger |
| `test_step_cap_stops_the_loop_without_writing` | agent lặp vô hạn → dừng ở 8 bước, `step_cap`, không ghi ledger |
| `test_trace_never_contains_ticket_secret_or_pii` | trace không chứa `CANARY_`, `parent_secret`, `principal_id`, ticket |

## 4. Bằng chứng

Chạy trong `src/`:

- `python -m pytest -q` → `54 passed, 248 deselected` (cổng host xanh, gồm test mới).
- `python -m pytest -q -m student -o addopts= -k "single] or [single"` → `62 passed` (CP2 single đạt, gồm T11 gọi lại và T12 crash rồi resume).
- `python -m pytest -q tests/test_single_extra.py` → `27 passed`.
- Ablation `python -m lab8.benchmark --shapes single,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out <tmp>/ablation_single_vs_swarm.json`:

  | Shape | Pass rate | pass^5 | Variance | Cost/success (VND mô phỏng) |
  | --- | --: | --: | --: | --: |
  | single | 1.000 | 1.000 | 0.000000 | 40.24 |
  | swarm | 0.986 | 0.929 | 0.000816 | 49.57 |

  Trial fail duy nhất: `R-swarm-C-002-s55` (`status resolved != denied`). `R-single-C-002-s55` pass.
- CP4 approval: mọi nhánh approval hỏng / sai claim / thiếu đều cho 0 dòng ledger và có audit `policy_denied` (các test ở mục 3). Số `approval_bypass_count` chính thức do giảng viên chấm trên bộ hidden.

## 5. Công cụ AI đã dùng

- **Claude Code (Claude Opus 5.5)**: đọc đề và code starter, gợi ý cài đặt `single.py`, viết test bổ sung, chạy benchmark và soạn nháp research card + báo cáo này.
- **Cách tự kiểm tra:**
  - Chạy lại cổng host, ma trận student của single (62/62) và 27 test mới; tất cả số trong báo cáo lấy từ output thật của các lệnh ở mục 4, không tự gõ.
  - Đọc lại `durability.issue_refund` và `policy.authorize` để chắc shape truyền quote đầy đủ, và host (không phải shape) mới là bên trừ phần đã hoàn và ghi `policy_denied`.
  - Quét trace của C-001, C-004, C-005, C-009, C-013 bằng `test_trace_never_contains_ticket_secret_or_pii` (dùng `lab8.metrics.artifact_blob`, giống grader) để xác nhận không có ticket, `principal_id` hay `CANARY_*`.
  - Tự mở lại paper MAST (arXiv:2503.13657) để đối chiếu phần CLAIM / BOUNDARY trong research card.

## 6. Tự đánh giá

- Đạt: shape single qua 62/62 test public, T11/T12 xanh, không có nhánh nào ghi tiền khi thiếu approval hợp lệ, trace không lộ secret; research card đã điền đủ kèm ablation có số liệu.
- Hạn chế: `decide()` là policy cố định nên single đúng tuyệt đối trên MockLLM; với LLM thật, rủi ro chuyển sang việc model chọn sai thứ tự tool hoặc dừng sớm. Đã chặn ở mức code (chỉ tool đọc, trần 8 bước, quote do code tính) nhưng chưa đo được với model thật.
- Single tốn trung bình 5.64 model call/trial (một "thought" mỗi bước) trong khi các bước của nó là cố định; nếu workflow đạt cùng pass rate với ít model call hơn thì số liệu ủng hộ ADR chọn shape ít tự chủ nhất làm được việc.
