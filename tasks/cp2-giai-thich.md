# Giải thích code CP2

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

`tests/test_serve.py` kiểm tra startup, prediction, dữ liệu sai và lỗi download bằng GCS giả lập. `tests/test_workflow.py` thực thi đúng đoạn Python Quality Gate trong YAML với các giá trị biên. Bộ test local hiện có 17 trường hợp; tất cả đã qua. Workflow đã qua actionlint và script setup đã qua `bash -n`.

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
- [Run kiểm chứng Train/Gate](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37654884696) đã qua Unit Test, Train và Quality Gate; Release bản cũ gặp mismatch SSH host key. Bản sửa pin ECDSA fingerprint đã sẵn sàng local. GitHub đang trả HTTP 500 khi push/cập nhật variable/rerun; chưa có run bốn jobs xanh của bản sửa.
- [Run từ push](https://github.com/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems/actions/runs/37655400811) chứng minh trigger tự động đã hoạt động sau khi bật Actions trên repo fork.

Để chụp ảnh 04, mở Git Bash và chạy hai lệnh thật dưới đây rồi chụp cả lệnh lẫn kết quả:

```bash
curl http://34.60.239.144:8080/healthz
curl -X POST http://34.60.239.144:8080/score -H 'Content-Type: application/json' -d '{"features": [60, 2, 5, 2, 4, 0, 1, 0, 0, 45]}'
```

Ảnh 05 chụp [GCS Console của bucket](https://console.cloud.google.com/storage/browser/income-lab-2a202602891?project=project-cd10db9a-96d8-4227-8ab), hiển thị `dvc/` và `artifacts/current/model.joblib`; có thể tách 05a/05b. Ảnh 02 cần chờ run bốn jobs xanh. Ảnh trình duyệt phải có thanh địa chỉ; chưa tạo được ảnh 02/04/05 vì công cụ Windows/browser lỗi sandbox. Kết quả CLI không thay thế các ảnh này.
