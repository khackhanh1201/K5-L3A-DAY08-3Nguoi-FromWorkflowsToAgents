# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt:

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Khắc Khánh | 2A202603472 | khackhanh120104@gmail.com | khackhanh1201 | Nhóm trưởng · Shape A `workflow` + integration, crash suite, benchmark, ADR |
|   2 | Mai Văn Thanh | 2A202603696 |       | MaiVanThanhDev | Shape B `single` + policy/approval (T01–T14), research card |
|   3 | Kiều Văn Thắng | 2A202603424 |26ai.thangkv@vinuni.edu.vn| katsu1154 | Shape C `orchestrator` + handoff, an toàn trace/secret, báo cáo nhóm |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.
- Nhóm 3 người (nhóm này): workflow + integration + crash/benchmark; single + policy; orchestrator + handoff + trace an toàn.

### Phân công chi tiết

| Người | File code phụ trách | Việc chung | Báo cáo | CP cần chốt |
| --- | --- | --- | --- | --- |
| Khánh | `src/lab8/shapes/workflow.py` | Tạo repo nhóm, giữ `python -m pytest -q` xanh, merge branch; chạy `lab8.crash_test` (`reports/crash.json`) và `lab8.benchmark` (`reports/benchmark.json`); chạy `lab8.check_submission` | `report/team/decision_adr.md` | Xong workflow sớm (~14:15) để B, C tham khảo; CP4 crash `20/20`; CP5 benchmark |
| Thanh | `src/lab8/shapes/single.py` | Rà nhánh approval hỏng, approval sai claim, đơn đã hoàn đủ, policy cũ/tương lai; ticket ghi sai số ngày trễ | `report/team/research_card.md` | CP2 single 62 passed; CP4 approval_bypass = 0 |
| Thắng | `src/lab8/shapes/orchestrator.py` | Handoff bằng `make_handoff` theo allowlist, investigator chỉ có tool đọc; rà trace/stdout không lộ `CANARY_SECRET_*` hay PII | `report/team/group_report.md` | CP3 handoff sạch; CP4 secret_leak = 0 |

Quy ước làm việc:

- Mỗi người làm trên branch riêng (`feat/workflow`, `feat/single`, `feat/orchestrator`), chỉ sửa file shape của mình; A merge vào `main`.
- Mỗi người tự viết ít nhất một test cho shape mình (ví dụ `src/tests/test_<shape>_extra.py`) và commit bằng tài khoản của mình (tính điểm C8).
- Không sửa `metrics.py`, `durability.py`, `policy.py`, `config/`, `data/`, JSON trong `src/reports/`.
- Mỗi người copy `report/team/MSSV_HoTen.md` thành file báo cáo cá nhân của mình.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| (Thành viên A) | workflow + integration + crash/benchmark | | |
| (Thành viên B) | single + policy | | |
| Kiều Văn Thắng | orchestrator + handoff + trace | Chưa commit (đang có trong working tree) | `src/tests/test_orchestrator_handoff.py` — kiểm tra handoff chỉ có tool đọc và artifact không lộ `CANARY_SECRET_*` |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-
