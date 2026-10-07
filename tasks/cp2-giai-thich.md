# Giải thích code CP2, CP3 và bonus

CP2 biến kết quả huấn luyện của CP1 thành pipeline tự động và API dự đoán trên GCP.

```text
Git push / Run workflow
        ↓
Unit Test → Train → Quality Gate → Release
              ↑                       ↓
        DVC pull từ GCS       Publish model vào GCS
                                      ↓
                            Copy serve.py, restart VM
                                      ↓
                              /healthz và /score
```

## 1. Theo dõi dữ liệu bằng DVC

Git lưu ba file `data/*.csv.dvc`; mỗi file chứa đường dẫn, kích thước và hash của CSV tương ứng. Dữ liệu thật được lưu trong DVC cache và remote `gs://income-lab-2a202602891/dvc`. `.dvc/config` lưu URL remote; credentials cá nhân được ghi bằng `--local` vào `.dvc/config.local`, đã được Git ignore.

Train job chỉ pull `train_batch1.csv` và `holdout.csv`. Batch 2 đã được theo dõi nhưng dành cho CP3. Không dùng holdout để huấn luyện.

## 2. Kiểm thử trong `tests/test_train.py`

`_make_temp_data()` sinh 200 mẫu có cùng 10 cột với Adult, chia 160 mẫu để học và 40 mẫu để đánh giá. Fixture chạy mô hình nhỏ 10 cây để kiểm tra ba yêu cầu: hàm trả về F1 hợp lệ, report có đúng metrics và model đã lưu có thể tải lại để dự đoán.

Mỗi test đổi thư mục làm việc và MLflow URI sang thư mục tạm. Vì vậy, chạy tests không ghi đè model, report hoặc lịch sử thí nghiệm CP1. Dữ liệu ngẫu nhiên chỉ dùng kiểm tra chức năng, không dùng chứng minh mô hình đạt F1 0.65.

## 3. Pipeline `.github/workflows/cicd.yml`

- **Unit Test:** cài dependencies và chạy toàn bộ tests, không cần tài khoản cloud.
- **Train:** đổi OIDC token của GitHub thành credentials GCP tạm qua Workload Identity Federation (WIF), DVC pull dữ liệu, chạy `src/train.py`, ghi F1 vào job output và lưu model/report dưới dạng GitHub artifact.
- **Quality Gate:** đọc F1, chuyển thành float và chỉ cho qua nếu điểm hữu hạn thuộc `[0.65, 1.0]`. F1 thấp, NaN, infinity hoặc giá trị rỗng làm job thất bại.
- **Release:** chỉ chạy khi gate thành công; tải artifact của chính workflow, upload model/report lên GCS, copy code serving tới VM, restart systemd và gọi health check cùng một yêu cầu dự đoán.

`needs` quy định thứ tự và chặn job phía sau khi job trước thất bại. Artifact chuyển file giữa các runner; job output chuyển giá trị F1. Model chỉ được publish vào `artifacts/current/model.joblib` ở Release, nên mô hình trượt gate không thay thế bản đang phục vụ.

Workflow được kích hoạt khi push code, tests, cấu hình, con trỏ dữ liệu lên `main`, hoặc chọn Run workflow. Concurrency giới hạn một workflow đang chạy để tránh hai bản release ghi đè model cùng lúc. Repo dùng bốn secrets: `ARTIFACT_BUCKET`, `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`. Ba variables công khai là `GCP_PROJECT_ID`, `WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`. Fingerprint ECDSA của VM được pin trong environment của job Release để xác minh đúng SSH host; ba biến GCP chọn project, WIF provider và service account.

## 4. API `src/serve.py`

`lifespan()` chạy khi FastAPI khởi động: tải model từ GCS, đọc file bằng joblib và giữ model trong `app.state.model`. Nếu download hoặc đọc model lỗi, ứng dụng không khởi động thành công.

`GET /healthz` trả về `{"status": "ok"}` khi API đã sẵn sàng. `POST /score` nhận `{"features": [...]}`, kiểm tra đủ 10 giá trị hữu hạn, tạo DataFrame với đúng thứ tự cột và gọi `model.predict()`. Nhãn 0 trả về `thu_nhap_thap`; nhãn 1 trả về `thu_nhap_cao`. Sai số lượng hoặc giá trị NaN/infinity trả HTTP 400; JSON/schema không hợp lệ do FastAPI/Pydantic xử lý.

Thứ tự đầu vào: `age`, `workclass`, `education_num`, `marital_status`, `occupation`, `relationship`, `sex`, `capital_gain`, `capital_loss`, `hours_per_week`.

```json
{"features": [60, 2, 5, 2, 4, 0, 1, 0, 0, 45]}
```

Các trường phân loại đã được mã hóa thành số từ bước chuẩn bị dữ liệu; API không nhận trực tiếp tên nghề nghiệp hoặc tình trạng hôn nhân.

## 5. Terraform, VM và kiểm chứng

`infra/gcp/main.tf` mô tả tài nguyên cloud và dependency giữa chúng. `terraform plan` hiển thị thay đổi dự kiến; `terraform apply` thực hiện đúng plan được chấp thuận. Lock file giữ phiên bản provider, state giữ thông tin tài nguyên đã tạo. State và credentials không được commit. Policy của project chặn tạo JSON key. Vì vậy `wif.tf` thiết lập WIF chỉ tin repo này, owner ID `327333586`, repo ID `1408233512` và nhánh `main`. GitHub có quyền impersonate service account; service account chỉ có `storage.objectAdmin` trên bucket lab. VM được gắn cùng service account với scope storage chỉ đọc, lấy credentials từ metadata server. Không tạo hoặc lưu JSON key.


`scripts/setup-vm.sh` cài môi trường Python riêng, pin phiên bản thư viện giống quá trình train và tạo service `income-api`. Service đọc tên bucket từ environment và dùng danh tính service account gắn trên VM, tự khởi động khi VM reboot và khởi động lại nếu lỗi. Setup chỉ enable service; Release mới khởi động sau khi model đã được publish.

`tests/test_serve.py` kiểm tra startup, prediction, dữ liệu sai và lỗi download bằng GCS giả lập. `tests/test_workflow.py` thực thi đúng đoạn Python Quality Gate trong YAML với các giá trị biên. Bộ test local hiện có 25 trường hợp; tất cả đã qua, gồm kiểm tra model giảm F1 không được upload. Workflow đã qua actionlint và script setup đã qua `bash -n`.

Tests local không thay cho kiểm chứng cloud: CP2 chỉ hoàn thành khi bốn jobs xanh, DVC push/pull thành công, endpoint trên IP VM hoạt động và đủ ảnh 02/04/05 theo rubric.

## Tài liệu chính thức

- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [GitHub Actions artifacts](https://docs.github.com/en/actions/tutorials/store-and-share-data)
- [DVC Google Cloud Storage](https://doc.dvc.org/user-guide/data-management/remote-storage/google-cloud-storage)
- [GCP WIF cho deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)

## Kết quả triển khai đã kiểm chứng

- Project: `project-cd10db9a-96d8-4227-8ab`; bucket: `income-lab-2a202602891`; VM: `income-api` (`e2-small`, `us-central1-a`). Terraform plan sau apply báo **No changes**.
- DVC push đủ ba file. Runner GitHub đã DVC pull thành công bằng WIF.
- Train trên GitHub đạt **F1 0.7149321266968326**, **accuracy 0.874**; Quality Gate đã qua. Model GCS có SHA256 `0b4678d0fc940bee246dc72325fb937f384e2c8cf3dbe58565ea13ce9ae7a124`, trùng artifact đã qua gate.
- API [healthz](http://34.60.239.144:8080/healthz) trả `{"status":"ok"}`. Hai mẫu trong bài lab lần lượt trả nhãn thấp và cao. Thiếu đặc trưng trả HTTP 400.
- [CP2: bốn jobs xanh](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37655942567).
- [CP3: commit dữ liệu, bốn jobs xanh](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37656393751). Commit `2959e2b` chỉ sửa `data/train_batch1.csv.dvc`, tăng train lên 44.722 mẫu, giữ holdout nguyên vẹn. F1 = **0.7354260089686099**, accuracy = **0.882**.

Để chụp ảnh 04, mở Git Bash và chạy hai lệnh thật dưới đây rồi chụp cả lệnh lẫn kết quả:

```bash
curl http://34.60.239.144:8080/healthz
curl -X POST http://34.60.239.144:8080/score -H 'Content-Type: application/json' -d '{"features": [60, 2, 5, 2, 4, 0, 1, 0, 0, 45]}'
```

Ảnh 05 chụp [GCS Console của bucket](https://console.cloud.google.com/storage/browser/income-lab-2a202602891?project=project-cd10db9a-96d8-4227-8ab), hiển thị `dvc/` và `artifacts/current/model.joblib`; có thể tách 05a/05b. Ảnh 02 dùng run CP2 xanh ở trên; ảnh 03 dùng run CP3 từ commit dữ liệu. Ảnh trình duyệt phải có thanh địa chỉ; chưa tạo được ảnh 02/03/04/05 vì công cụ Windows/browser lỗi sandbox. Kết quả CLI không thay thế các ảnh này.

## Bonus hoạt động thế nào

`src/train.py` đo tỷ lệ lớp dương trước khi fit; lệch hơn 5 điểm phần trăm so với 24.8% sẽ in `WARNING: DATA DRIFT`. Giá trị `positive_ratio` được ghi vào JSON và MLflow. Sau fit, code quét 17 ngưỡng từ 0.10 đến 0.90, bước 0.05, lưu `best_threshold` và `best_threshold_f1`; nếu hòa F1, chọn ngưỡng gần 0.5 nhất. `f1_score` vẫn dùng nhãn mặc định để gate và API nhất quán. Ngưỡng tốt nhất trên holdout là phân tích thăm dò; muốn thay ngưỡng production cần tập validation riêng.

`outputs/detail.txt` chứa confusion matrix, precision/recall/F1 cho hai lớp; workflow in file này và upload cùng model/report. Với ứng dụng tìm khách hàng thu nhập cao, recall thấp làm mất cơ hội do bỏ sót; precision thấp tốn công tiếp cận nhầm. Chi phí cụ thể tùy ứng dụng, nên lab cân bằng bằng F1 lớp dương.

`src/release.py` đọc report hiện tại từ GCS trước khi upload. Nếu F1 mới thấp hơn, hoặc report cũ lỗi, code dừng và không upload. F1 bằng hoặc cao hơn được publish. Chỉ HTTP 404 được hiểu là chưa từng deploy; lỗi quyền/mạng không được bỏ qua. Pipeline được serialize để hai releases không so sánh/ghi đè cùng lúc.

Bonus DagsHub dùng MLflow sẵn có, không thêm SDK. Train đọc ba GitHub Secrets `MLFLOW_TRACKING_URI`, `MLFLOW_TRACKING_USERNAME`, `MLFLOW_TRACKING_PASSWORD`; URI dạng `https://dagshub.com/<user>/<repo>.mlflow`. Khi chưa cấu hình URI, CI dùng SQLite; đây chưa phải bằng chứng Bonus 1. Không đưa token vào chat, Git hoặc báo cáo. Xem [DagsHub Experiment Tracking](https://dagshub.com/docs/feature_guide/experiment_tracking/).

[Kiểm chứng Quality Gate thật](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37657213948): cấu hình 50 cây, learning rate 0.05, depth 2 đạt F1 0.5907; Gate thất bại, Release bị skipped. Generation của cả model và report trên GCS không đổi; VM giữ model CP3. Bộ tham số 200/0.1/5 đã được khôi phục.

Kết quả bonus trên GitHub: ngưỡng 0.30 đạt F1 **0.7537**, so với **0.7354** ở 0.5. Tỷ lệ lớp dương **24.7842%**. Confusion matrix mặc định: TN=359, FP=17, FN=42, TP=82; precision lớp cao=0.8283, recall=0.6613.

Ảnh 01 hiện có bảng MLflow đúng metrics/params nhưng thiếu thanh địa chỉ; cần chụp lại để đáp ứng quy ước chung của rubric.

[Kiểm chứng Bonus 4 thật](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37658506229): candidate F1 **0.701422** vượt 0.65 nên Quality Gate xanh, nhưng thấp hơn current F1 **0.735426** nên Release hủy trước upload. Generation của cả model và report GCS không đổi. Đây là lần thất bại có chủ ý để kiểm chứng bảo vệ chất lượng.
