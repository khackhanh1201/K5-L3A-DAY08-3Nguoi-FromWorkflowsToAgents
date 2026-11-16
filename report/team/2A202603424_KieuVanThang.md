# Báo cáo cá nhân — Kiều Văn Thắng

## 1. Thông tin thành viên

- Họ tên: Kiều Văn Thắng
- MSSV: 2A202603424
- Email: 26ai.thangkv@vinuni.edu.vn
- GitHub: [katsu1154](https://github.com/katsu1154)

## 2. Phần việc phụ trách

Theo phân công trong [TEAM.md](../../TEAM.md), phụ trách Shape C `orchestrator`: triển khai `src/lab8/shapes/orchestrator.py`, tạo handoff bằng `make_handoff` theo allowlist, giới hạn investigator ở các công cụ chỉ đọc, và đảm bảo trace/handoff không làm lộ secret hoặc dữ liệu cá nhân. Phụ trách viết phần báo cáo nhóm trong `report/team/group_report.md`.

## 3. Đóng góp cụ thể

Hoàn thiện `src/lab8/shapes/orchestrator.py` với các quyết định sau:

- Đọc claim qua `get_claim_view`, nhưng không đưa ticket hoặc claim row vào trace/handoff.
- Dùng `make_handoff` với allowlist chỉ gồm các công cụ đọc; investigator tra cứu đơn, policy, lịch sử hoàn tiền và tính quote.
- Quote được lấy từ `compute_compensation`; chỉ chuyển quote đầy đủ cho `durability.issue_refund`, để host áp dụng approval, giới hạn theo đơn và idempotency.
- Dùng `finish()` cho kết quả và trace ở các nhánh kết thúc; ghi trace crash rồi để `InjectedCrash` truyền lên để có thể resume an toàn.
- Thêm `src/tests/test_orchestrator_handoff.py`, kiểm tra handoff không cấp write tool và artifact không chứa `CANARY_SECRET_*`.

Chưa có commit riêng cho phần triển khai trong working tree; commit hash sẽ được bổ sung sau khi commit.

## 4. Bằng chứng

- Phân công: mục “Phân công chi tiết” trong [TEAM.md](../../TEAM.md).
- Shape: [src/lab8/shapes/orchestrator.py](../../src/lab8/shapes/orchestrator.py).
- Test mới: [src/tests/test_orchestrator_handoff.py](../../src/tests/test_orchestrator_handoff.py); test liên quan có sẵn: `src/tests/test_handoff_secret.py`, `src/tests/test_trace_contract.py` và ma trận `src/tests/test_public_matrix.py`.
- Kiểm tra trong `src/`: `python -m pytest -q` — 55 passed; `python -m pytest -q -m student -o addopts= -k orchestrator` — 62 passed, gồm kiểm tra retry/crash T11–T12.
- Chưa có run ID benchmark hay kết quả hidden; hidden dataset không có trong working tree.
- Các test trên chạy bằng Python 3.14.10; repo hiện ghi hỗ trợ/test Python 3.11–3.13, nên cần chạy lại bằng phiên bản trong dải hỗ trợ trước khi nộp.

## 5. Công cụ AI đã dùng

Trong phiên làm việc này, dùng Copilot để đối chiếu contract, triển khai Shape C và tạo test tập trung. Tự kiểm tra bằng cách đọc các helper/contract hiện có và chạy các lệnh pytest đã nêu; không dùng AI để tạo số liệu benchmark, run ID hoặc kết quả test.

## 6. Tự đánh giá

Shape C hiện qua cổng host và 62 test student công khai, gồm các tình huống retry/crash. Chưa thể kết luận về bộ hidden hoặc khả năng tái lập trên Python 3.11–3.13 cho đến khi chạy lại trên phiên bản được khuyến nghị; cũng cần cập nhật commit hash sau khi commit.
