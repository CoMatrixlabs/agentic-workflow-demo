# Bucket the reconciliation partner reads the exported unified context from.
resource "aws_s3_bucket" "ops_exports" {
  bucket = "customer-ops-context-exports"
  acl    = "public-read"
}

resource "aws_s3_bucket_public_access_block" "ops_exports" {
  bucket                  = aws_s3_bucket.ops_exports.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
