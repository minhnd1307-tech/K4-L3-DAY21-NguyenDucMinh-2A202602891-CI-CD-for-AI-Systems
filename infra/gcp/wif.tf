# Trust only this repository's main branch; no service account JSON key.
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "income-github"
  display_name              = "Income GitHub Actions"
  depends_on                = [google_project_service.lab]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "Income repo main branch"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository_id == '1408233512' && assertion.repository_owner_id == '327333586' && assertion.ref == 'refs/heads/main'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github" {
  service_account_id = google_service_account.lab.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/minhnd1307-tech/K4-L3-DAY21-NguyenDucMinh-2A202602891-CI-CD-for-AI-Systems"
}

output "workload_identity_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}
