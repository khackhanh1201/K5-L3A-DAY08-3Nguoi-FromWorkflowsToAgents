# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R2 · Failure taxonomy |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Cemri et al., *Why Do Multi-Agent LLM Systems Fail?* (MAST), NeurIPS 2025 Datasets & Benchmarks, arXiv:2503.13657. Loại bằng chứng: benchmark + phân loại lỗi có người gán nhãn trên trace của nhiều framework multi-agent |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Lỗi của hệ multi-agent gom được vào 3 nhóm: (1) đặc tả / thiết kế hệ thống, (2) lệch nhau giữa các agent, (3) kiểm chứng và kết thúc task; nhiều lỗi đến từ thiết kế hệ thống chứ không chỉ do model yếu |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Taxonomy rút từ trace của LLM thật trên task lập trình/toán/hỏi đáp và vài framework cụ thể. Không đo hệ có host kiểm tiền bằng code, không dùng MockLLM, không có task ghi tiền như claim LogiX |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Trial fail của swarm ở seed 55 (C-002) thuộc nhóm (3) kiểm chứng: số ngày trễ trong ticket không được đối chiếu với order row. Đổi swarm → single (agent chỉ lấy delay từ `lookup_order`, tiền từ `compute_compensation`) thì lỗi nhóm (3) về 0: pass rate tăng từ ~0.986 lên 1.000, pass^5 từ ~0.93 lên 1.00, seed variance về 0; cost/success giảm vì bỏ được lời gọi peer |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định: MockLLM, bộ tool đọc + host `durability.issue_refund`, seed 11,22,33,44,55, corpus `data/public_claims.jsonl` (14 claim), `config/pricing.yaml`, evaluator `lab8.metrics.trial_pass`, SQLite mới cho mỗi trial. Biến duy nhất thay đổi: topology (swarm peers ↔ một agent ReAct `single`, tối đa 8 bước) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: agent tin số ngày trễ khách tự ghi → trả tiền cho claim phải `denied` (lỗi kiểm chứng, MAST nhóm 3). Đo bằng pass rate, pass^5, seed variance, cost/success, và đếm trial lý do `status resolved != denied`; kèm bypass/leak qua test `tests/test_single_extra.py` |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn, trong `src/`):

  ```bash
  python -m lab8.benchmark --shapes single,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out <scratchpad>/ablation_single_vs_swarm.json
  ```

  File ablation để ở thư mục tạm, không ghi đè `src/reports/benchmark.json` (file đó do nhóm trưởng sinh cho 4 shape).
- Run id / file report: mỗi trial có run id dạng `R-<shape>-<claim>-s<seed>`; trial fail duy nhất là `R-swarm-C-002-s55`. Trial tương ứng của single là `R-single-C-002-s55` (pass, `denied`, proposal 0). Số liệu 4 shape đầy đủ nằm trong `src/reports/benchmark.json`.
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **đúng** trên bộ public.

  | Shape | Trial | Pass rate | pass^5 | Seed variance | Cost/success (VND mô phỏng) | Model calls TB | Tool calls TB |
  | --- | --: | --: | --: | --: | --: | --: | --: |
  | single | 70 | 1.000 | 1.000 | 0.000000 | 40.24 | 5.64 | 3.64 |
  | swarm | 70 | 0.986 | 0.929 | 0.000816 | 49.57 | 3.00 | 4.66 |

  Swarm chỉ fail 1/70 trial: C-002 seed 55, lý do `status resolved != denied` (ticket ghi trễ 5 ngày, order row 2 ngày). Đây đúng là lỗi kiểm chứng (MAST nhóm 3): không bước nào đối chiếu số khách viết với nguồn sự thật. Single không có lỗi này vì decide() không đọc ticket; số ngày trễ chỉ lấy từ `lookup_order`. Lưu ý: single tốn nhiều model call hơn (một "thought" mỗi bước ReAct) nhưng cost/success vẫn thấp hơn vì prompt của nó ngắn (chỉ trạng thái có cấu trúc) và không có lần fail nào kéo mẫu số xuống.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. Lỗi của swarm là điểm yếu được cài sẵn (`REFERENCE_WEAKNESS`, seed % 5 == 0), nên ablation chỉ cho thấy topology có bước kiểm chứng bằng code chặn được lỗi loại này, chứ không ước lượng được tần suất lỗi của LLM thật. 14 claim × 5 seed là mẫu nhỏ; chênh 0.014 pass rate tương ứng đúng một trial.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
