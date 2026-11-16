# Báo cáo cá nhân — 2A202603472_NguyenKhacKhanh

## 1. Thông tin thành viên

- Họ tên: Nguyễn Khắc Khánh
- MSSV: 2A202603472
- Email: khackhanh120104@gmail.com
- GitHub: khackhanh1201

## 2. Phần việc phụ trách

Nhóm trưởng. Shape A `workflow` (`src/lab8/shapes/workflow.py`), integration (giữ cổng host xanh, merge branch), crash suite (`src/reports/crash.json`), benchmark 4 shape (`src/reports/benchmark.json`), và `report/team/decision_adr.md`.

## 3. Đóng góp cụ thể

- Viết shape workflow theo 7 bước cố định: `get_claim_view` → `needs_info` nếu thiếu order_id → `lookup_order` (`escalated` nếu không thấy hoặc sai principal) → `compute_compensation` từ order row → `denied` nếu quote 0 → `durability.issue_refund` với **quote đầy đủ** → `resolved` / `denied` / `failed` theo kết quả host.
- Quyết định kỹ thuật:
  - Không đọc ticket để lấy số ngày trễ hay mã đơn; ticket không vào trace, không vào prompt model.
  - MockLLM chỉ được gọi một lần để soạn trả lời, prompt là chuỗi `status=<...>` cố định.
  - Không tự trừ phần đã hoàn trước đó (để host tính trần theo đơn, T13, T14).
  - Khi bị `InjectedCrash`: ghi trace rồi ném lại, không nuốt lỗi (T12).
- Thêm test `src/tests/test_workflow_extra.py` (18 test, chạy trong cổng host).
- Chạy crash suite: `crash_safety` 20/20.
- Commit chính: *(điền hash sau khi commit)*

## 4. Bằng chứng

- `python -m pytest -q -m student -o addopts= -k workflow` → 62 passed.
- `python -m pytest -q` → cổng host xanh (54 test gốc + 18 test mới).
- `python -m lab8.crash_test --count 20 --out reports/crash.json` → `crash_safety 20/20`.
- Benchmark sơ bộ workflow vs swarm (14 claim × 5 seed): workflow pass 1.000, pass^5 1.000, variance 0, cost/success 28.80; swarm 0.986 / 0.929 / 0.000816 / 49.57.
- Test đã thêm: `test_unknown_claim_fails_cleanly_with_trace`, `test_trace_has_no_secret_ticket_or_pii` (14 claim), `test_ticket_delay_is_ignored_on_every_seed`, `test_model_never_sees_ticket_text`, `test_same_seed_is_deterministic`.

## 5. Công cụ AI đã dùng

Claude Code: đọc đề và contract, gợi ý chia vai, viết bản đầu của `workflow.py`, test bổ sung và nháp ADR. Mình tự kiểm tra bằng cách chạy ma trận student (62/62), cổng host, crash suite và benchmark; đọc lại từng nhánh return đối chiếu với bảng trong `docs/contracts.md`; mở file trace để kiểm tra không có ticket, `CANARY_SECRET_*` hay PII.

## 6. Tự đánh giá

Workflow đạt đủ ma trận public và 3 must-pass trên bộ public. Còn phải làm: merge shape single và orchestrator, chạy benchmark 4 shape, điền commit hash và run id vào ADR, rồi chạy `check_submission` đến khi ra `0 FAIL`. Rủi ro: bộ hidden có thể có tình huống mà `compute_compensation` không bao phủ; khi đó workflow sẽ sai giống nhau trên mọi seed.
