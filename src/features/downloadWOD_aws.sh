#!/bin/bash

# Base URL of the AWS S3 bucket
bucket_url="s3://noaa-wod-pds/"

# Local download path
download_path="/datasets/work/soop-xbt/work/WOD/"

# Set AWS credentials to empty strings for anonymous access
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""

# Sync the S3 bucket to the local path
aws s3 sync $bucket_url $download_path --no-sign-request
