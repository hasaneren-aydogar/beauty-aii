import os
import tempfile

# Must be set before app modules are imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="beauty-test-"))
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "10000/minute")
os.environ.setdefault("RATE_LIMIT_TRY", "10000/minute")
os.environ.setdefault("RATE_LIMIT_AUTH", "10000/minute")
os.environ.setdefault("RATE_LIMIT_RAG", "10000/minute")
