# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Nguyễn Đức Minh |
| MSSV | 2A202602891 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems |
| Ngày nộp | 08/10/2026 |

---

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.8780 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.8460 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.8740 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Ba lần chạy dùng cùng train, holdout 500 mẫu và seed 42. Lần 3 có F1 cao nhất, vượt 0.65 nên được chọn; lần 1 có accuracy cao nhất nhưng F1 thấp hơn. Nhiều tham số thay đổi đồng thời nên chưa thể tách ảnh hưởng riêng. Các snapshot CP1 đã lưu; `params.yaml` giữ bộ tham số lần 3.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Adult có khoảng 24.8% mẫu thu nhập cao. Luôn đoán thấp vẫn đạt accuracy 75.2% nhưng bỏ sót toàn bộ lớp dương, F1 bằng 0. F1 kết hợp precision và recall của lớp thu nhập cao nên phù hợp ngưỡng 0.65. `weighted` và `macro` đo đại lượng khác F1 lớp dương. Holdout chỉ đánh giá, không huấn luyện. Với mục tiêu tìm người thu nhập cao, 42 false negatives gây bỏ sót cơ hội; 17 false positives tốn công tiếp cận nhầm. Vì vậy recall thấp đáng lo hơn trong mục tiêu này.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| GCP chặn tạo JSON key. | Policy của project không cho tạo khóa service account. | Đã dùng WIF cho GitHub và service account gắn trên VM, giữ quyền chỉ trên bucket lab. |
| Kiểm chứng model yếu. | Bộ 50 cây, learning rate 0.05, depth 2 đạt F1 0.5907 trên CP3. | Gate đã chặn Release; model GCS không đổi, sau đó khôi phục tham số tốt. |

Bonus quét ngưỡng chọn 0.30, F1 0.7537 so với 0.7354 tại 0.5; đây là kết quả thăm dò trên holdout. Tỷ lệ lớp dương 24.784% không vượt ngưỡng cảnh báo 5 điểm phần trăm. Release so F1 mới với bản đang chạy và hủy upload nếu giảm. Remote tracking DagsHub kết nối tại `minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems`.

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.8740 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.8820 |

**Nhận xét:** Khi tăng train từ 22.361 lên 44.722 mẫu, F1 tăng 0.0205 và accuracy tăng 0.0080. Cùng tham số và holdout 500 mẫu cho thấy batch 2 giúp mô hình trên holdout này; thêm dữ liệu không bảo đảm cải thiện trong mọi tình huống.
