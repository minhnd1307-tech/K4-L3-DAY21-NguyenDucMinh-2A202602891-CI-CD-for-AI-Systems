# Hạ tầng CP2 bằng Terraform

Project: `project-cd10db9a-96d8-4227-8ab`.

## Tài nguyên và danh tính

`main.tf` quản lý năm API GCP, bucket `income-lab-2a202602891`, service account `income-lab-sa`, quyền `roles/storage.objectAdmin` chỉ trên bucket, VM Ubuntu 22.04 `income-api` loại `e2-small` ở `us-central1-a` và firewall TCP/8080 công khai. VM có disk 10 GB, user SSH `income`; private SSH key không nằm trong Terraform.

VM dùng service account gắn trực tiếp với scope storage chỉ đọc. `wif.tf` tạo pool `income-github` và provider `github`, chỉ cho repo ID `1408233512`, owner ID `327333586`, nhánh `main` đổi OIDC token và impersonate service account. Project chặn JSON key; cấu hình này không cần JSON key.

State, plan, credentials và `.terraform` được Git ignore. Commit file `.tf` và `.terraform.lock.hcl` để giữ cấu hình cùng phiên bản provider đã kiểm chứng.

## Plan và apply

Trong PowerShell ở root repo, sau khi tạo SSH key và đăng nhập gcloud đúng tài khoản:

```powershell
$env:TF_VAR_ssh_public_key = (Get-Content .secrets/income_deploy.pub -Raw).Trim()
$env:GOOGLE_OAUTH_ACCESS_TOKEN = (gcloud auth print-access-token --account=nhh000003@gmail.com)
try {
    terraform '-chdir=infra/gcp' init
    terraform '-chdir=infra/gcp' validate
    terraform '-chdir=infra/gcp' plan '-out=../../.secrets/cp2.tfplan'
    # Review plan trước khi apply: VM/storage tính phí, API lab công khai.
    terraform '-chdir=infra/gcp' apply '../../.secrets/cp2.tfplan'
} finally {
    Remove-Item Env:GOOGLE_OAUTH_ACCESS_TOKEN
}
terraform '-chdir=infra/gcp' output
```

Token chỉ truyền qua environment. Tài khoản phải có quyền trên project và billing đã bật. Lần triển khai đầu tạo 8 tài nguyên; plan WIF bổ sung 5 tài nguyên và cập nhật VM (dừng/khởi động lại để gắn service account).

## Cấu hình ứng dụng

Local DVC dùng Application Default Credentials của tài khoản sở hữu project: `gcloud auth application-default login`, rồi `dvc push`. Copy `src/serve.py` và `scripts/setup-vm.sh` lên VM; chạy `bash setup-vm.sh income-lab-2a202602891` dưới user `income`.

GitHub Secrets: `ARTIFACT_BUCKET`, `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`. Variables: `GCP_PROJECT_ID`, `WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`. Provider và service account lấy từ Terraform outputs. Fingerprint ECDSA của VM đã xác minh được pin trong job Release; cần cập nhật nếu tạo VM mới với host key khác. Không tắt kiểm tra host key.

Push `main` kích hoạt Unit Test → Train → Quality Gate → Release. Terraform quản lý hạ tầng; Actions huấn luyện và release; systemd giữ API chạy trên VM. Xem [giải thích CP2](../../tasks/cp2-giai-thich.md).
