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

**Lý do:** Cả ba thí nghiệm dùng cùng tập huấn luyện, holdout 500 mẫu và `random_state=42`. Lần 3 có F1 cao nhất, đạt ngưỡng 0.65 và cao hơn lần 1 khoảng 0.0040. Lần 1 có accuracy cao nhất nhưng F1 thấp hơn, cho thấy hai chỉ số không chọn cùng mô hình. Lần 2 có learning rate nhỏ, ít cây và cây nông nên F1 thấp nhất. Giảm learning rate thường cần tăng số cây; tuy nhiên, các thí nghiệm này thay đổi nhiều tham số nên chưa tách được ảnh hưởng riêng của từng tham số. `params.yaml`, model và report đã giữ kết quả lần 3. Bằng chứng nằm trong [ảnh MLflow](anh-chup-man-hinh/01-mlflow-ui.png).

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Dữ liệu Adult có khoảng 24.8% mẫu thu nhập cao. Mô hình luôn đoán thu nhập thấp vẫn đạt accuracy khoảng 75.2%, nhưng bỏ sót toàn bộ lớp dương và có F1 bằng 0. F1 kết hợp precision và recall của lớp thu nhập cao, phản ánh cả dự đoán nhầm và bỏ sót. Vì vậy, lab dùng `f1_score(y_eval, preds)` cho `target=1` và đặt ngưỡng 0.65. `weighted` ưu tiên lớp đông mẫu, còn `macro` trung bình hai lớp; cả hai đo đại lượng khác F1 lớp dương nên không phù hợp với ngưỡng đã chọn. Accuracy được ghi để tham khảo. Holdout chỉ dùng đánh giá, không đưa vào huấn luyện.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| GCP chặn tạo JSON key. | Policy của project không cho tạo khóa service account. | Đã dùng WIF cho GitHub và service account gắn trên VM, giữ quyền chỉ trên bucket lab. |
| Một cấu hình không đạt ngưỡng F1. | Bộ 50 cây, learning rate 0.05, depth 2 chỉ đạt F1 0.6051. | Đã chọn bộ 200 cây đạt F1 0.7149. |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | 0.7149 | 0.8740 |
| Bước 3 (thêm `train_batch2`) | 0.7354 | 0.8820 |

**Nhận xét:** Khi tăng train từ 22.361 lên 44.722 mẫu, F1 tăng 0.0205 và accuracy tăng 0.0080. Cùng tham số và holdout 500 mẫu cho thấy batch 2 giúp mô hình trên holdout này; thêm dữ liệu không bảo đảm cải thiện trong mọi tình huống.

