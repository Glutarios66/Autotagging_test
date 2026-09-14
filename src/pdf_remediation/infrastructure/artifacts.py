from __future__ import annotations

from pathlib import Path

import boto3


class FileSystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def put(self, key: str, content: bytes, media_type: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"file://{path.resolve()}"

    def get(self, uri: str) -> bytes:
        if not uri.startswith("file://"):
            raise ValueError("unsupported uri")
        return Path(uri.removeprefix("file://")).read_bytes()


class S3ArtifactStore:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def put(self, key: str, content: bytes, media_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=media_type,
        )
        return f"s3://{self.bucket}/{key}"

    def get(self, uri: str) -> bytes:
        prefix = f"s3://{self.bucket}/"
        if not uri.startswith(prefix):
            raise ValueError("artifact is outside configured bucket")
        key = uri.removeprefix(prefix)
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()
