# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

<!--
HƯỚNG DẪN - đọc rồi XÓA TOÀN BỘ các khối chú thích này sau khi điền xong:

  - Giới hạn: KHÔNG QUÁ 1 TRANG A4, tương đương khoảng 450 - 550 từ nội dung.
  - Chỉ điền vào các chỗ ___ và các ô trong bảng. Không thêm mục mới.
  - Viết bằng câu hoàn chỉnh, không gạch đầu dòng cụt lủn.
  - Kiểm tra độ dài sau khi đã xóa hết chú thích:
        wc -w nop-bai/bao-cao.md
    và xem trước bản in bằng cách mở file trên GitHub rồi Ctrl+P / Cmd+P.
-->

| | |
|---|---|
| Họ và tên | Nguyễn Đức Minh |
| MSSV | 2A202602891 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems |
| Ngày nộp | ___ |

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
| Python mặc định thiếu thư viện ML. | Python hệ thống khác môi trường dự án. | Đã dùng Python trong `.venv` để chạy cả ba thí nghiệm. |
| Một cấu hình không đạt ngưỡng F1. | Bộ 50 cây, learning rate 0.05, depth 2 chỉ đạt F1 0.6051. | Đã chọn bộ 200 cây đạt F1 0.7149. |

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

<!-- Lấy số liệu từ bảng ở mục 3.6 của tasks/buoc-3.md. -->

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | ___ | ___ |
| Bước 3 (thêm `train_batch2`) | ___ | ___ |

**Nhận xét:** ___

<!--
Một câu trả lời trung thực kiểu "f1 giảm 0,01 vì dữ liệu mới cùng phân phối, không mang
thêm thông tin mới" được đánh giá cao hơn kết luận sai rằng thêm dữ liệu luôn tốt hơn.
-->
