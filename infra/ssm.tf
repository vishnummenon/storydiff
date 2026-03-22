# SSM Parameter Store — secrets are stored here, never in code or Terraform state.
#
# Terraform creates the parameters with a placeholder value.
# After `terraform apply`, populate them manually:
#
#   aws ssm put-parameter \
#     --name "/storydiff/database-url" \
#     --value "postgresql+psycopg://user:pass@host:5432/storydiff" \
#     --type SecureString \
#     --overwrite

locals {
  ssm_params = [
    "database-url",
    "openai-api-key",
    "qdrant-url",
    "qdrant-api-key",
    "sqs-article-analyze-queue-url",
    "sqs-topic-refresh-queue-url",
  ]
}

resource "aws_ssm_parameter" "secrets" {
  for_each = toset(local.ssm_params)

  name  = "/storydiff/${each.key}"
  type  = "SecureString"
  value = "REPLACE_ME"

  lifecycle {
    # Prevent Terraform from overwriting values populated manually after provisioning
    ignore_changes = [value]
  }
}
