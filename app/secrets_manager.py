"""
Secrets Manager for Convertbot
Supports multiple backends: Environment, File, HashiCorp Vault, AWS Secrets Manager
"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from functools import lru_cache
from app.logger import setup_logger

logger = setup_logger(__name__)


class SecretsBackend(ABC):
    """Abstract base class for secrets backends"""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key"""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str) -> bool:
        """Set a secret (if supported)"""
        pass

    def get_secrets(self, keys: list) -> Dict[str, Optional[str]]:
        """Get multiple secrets"""
        return {key: self.get_secret(key) for key in keys}


class EnvironmentBackend(SecretsBackend):
    """Load secrets from environment variables"""

    def get_secret(self, key: str) -> Optional[str]:
        return os.environ.get(key)

    def set_secret(self, key: str, value: str) -> bool:
        os.environ[key] = value
        return True


class FileBackend(SecretsBackend):
    """
    Load secrets from a JSON file.
    File should be chmod 600 and owned by root.
    """

    def __init__(self, secrets_file: str = "/etc/convertbot/secrets.json"):
        self.secrets_file = secrets_file
        self._cache: Dict[str, str] = {}
        self._load_secrets()

    def _load_secrets(self):
        """Load secrets from file"""
        try:
            if os.path.exists(self.secrets_file):
                # Check file permissions
                mode = os.stat(self.secrets_file).st_mode
                if mode & 0o077:  # Group or others have access
                    logger.warning(f"⚠️ Secrets file has insecure permissions: {oct(mode)}")

                with open(self.secrets_file, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} secrets from {self.secrets_file}")
            else:
                logger.info(f"Secrets file not found: {self.secrets_file}")
        except Exception as e:
            logger.error(f"Failed to load secrets file: {e}")

    def get_secret(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    def set_secret(self, key: str, value: str) -> bool:
        self._cache[key] = value
        try:
            with open(self.secrets_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
            # Set secure permissions
            os.chmod(self.secrets_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save secret: {e}")
            return False


class VaultBackend(SecretsBackend):
    """
    HashiCorp Vault backend.
    Requires: pip install hvac
    """

    def __init__(
        self,
        vault_addr: str = None,
        vault_token: str = None,
        mount_point: str = "secret",
        path: str = "convertbot"
    ):
        self.mount_point = mount_point
        self.path = path
        self._client = None
        self._cache: Dict[str, str] = {}

        try:
            import hvac
            vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
            vault_token = vault_token or os.environ.get("VAULT_TOKEN")

            if vault_token:
                self._client = hvac.Client(url=vault_addr, token=vault_token)
                if self._client.is_authenticated():
                    logger.info(f"✅ Connected to Vault at {vault_addr}")
                    self._load_secrets()
                else:
                    logger.warning("Vault authentication failed")
                    self._client = None
            else:
                logger.info("No Vault token provided, skipping Vault backend")

        except ImportError:
            logger.info("hvac not installed, Vault backend unavailable")
        except Exception as e:
            logger.error(f"Vault connection error: {e}")

    def _load_secrets(self):
        """Load all secrets from Vault path"""
        if not self._client:
            return

        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=self.path
            )
            self._cache = response['data']['data']
            logger.info(f"Loaded {len(self._cache)} secrets from Vault")
        except Exception as e:
            logger.error(f"Failed to load secrets from Vault: {e}")

    def get_secret(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    def set_secret(self, key: str, value: str) -> bool:
        if not self._client:
            return False

        try:
            self._cache[key] = value
            self._client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.mount_point,
                path=self.path,
                secret=self._cache
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save secret to Vault: {e}")
            return False


class AWSSecretsBackend(SecretsBackend):
    """
    AWS Secrets Manager backend.
    Requires: pip install boto3
    """

    def __init__(self, secret_name: str = "convertbot/secrets", region: str = None):
        self.secret_name = secret_name
        self._client = None
        self._cache: Dict[str, str] = {}

        try:
            import boto3
            region = region or os.environ.get("AWS_REGION", "us-east-1")
            self._client = boto3.client("secretsmanager", region_name=region)
            self._load_secrets()
            logger.info(f"✅ Connected to AWS Secrets Manager")
        except ImportError:
            logger.info("boto3 not installed, AWS backend unavailable")
        except Exception as e:
            logger.error(f"AWS Secrets Manager error: {e}")

    def _load_secrets(self):
        """Load secrets from AWS"""
        if not self._client:
            return

        try:
            response = self._client.get_secret_value(SecretId=self.secret_name)
            self._cache = json.loads(response['SecretString'])
            logger.info(f"Loaded {len(self._cache)} secrets from AWS")
        except Exception as e:
            logger.error(f"Failed to load secrets from AWS: {e}")

    def get_secret(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    def set_secret(self, key: str, value: str) -> bool:
        if not self._client:
            return False

        try:
            self._cache[key] = value
            self._client.update_secret(
                SecretId=self.secret_name,
                SecretString=json.dumps(self._cache)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save secret to AWS: {e}")
            return False


class SecretsManager:
    """
    Main secrets manager with fallback chain.
    Tries backends in order: Vault -> AWS -> File -> Environment
    """

    def __init__(self):
        self.backends: list[SecretsBackend] = []
        self._init_backends()

    def _init_backends(self):
        """Initialize backends based on configuration"""
        backend_order = os.environ.get("SECRETS_BACKEND", "env").lower().split(",")

        for backend_name in backend_order:
            backend_name = backend_name.strip()

            if backend_name == "vault":
                backend = VaultBackend()
                if backend._client:
                    self.backends.append(backend)

            elif backend_name == "aws":
                backend = AWSSecretsBackend()
                if backend._client:
                    self.backends.append(backend)

            elif backend_name == "file":
                secrets_file = os.environ.get("SECRETS_FILE", "/etc/convertbot/secrets.json")
                self.backends.append(FileBackend(secrets_file))

            elif backend_name == "env":
                self.backends.append(EnvironmentBackend())

        # Always fallback to environment
        if not any(isinstance(b, EnvironmentBackend) for b in self.backends):
            self.backends.append(EnvironmentBackend())

        logger.info(f"Secrets backends: {[type(b).__name__ for b in self.backends]}")

    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        """Get secret from first backend that has it"""
        for backend in self.backends:
            value = backend.get_secret(key)
            if value is not None:
                return value
        return default

    def get_required_secret(self, key: str) -> str:
        """Get secret or raise error if not found"""
        value = self.get_secret(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value

    def mask_secret(self, value: str) -> str:
        """Mask a secret for logging (show first/last 2 chars)"""
        if not value or len(value) < 8:
            return "****"
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


# Global instance
@lru_cache()
def get_secrets_manager() -> SecretsManager:
    return SecretsManager()


secrets = get_secrets_manager()


# ==================== Key Rotation Support ====================

class KeyRotation:
    """
    Support for API key rotation without downtime.
    Keeps old key active for grace period during rotation.
    """

    def __init__(self, key_name: str, grace_period_seconds: int = 300):
        self.key_name = key_name
        self.grace_period = grace_period_seconds
        self._old_key: Optional[str] = None
        self._rotation_time: Optional[float] = None

    def rotate(self, new_key: str) -> bool:
        """
        Rotate to new key while keeping old one valid for grace period.
        """
        import time

        current = secrets.get_secret(self.key_name)
        if current:
            self._old_key = current
            self._rotation_time = time.time()

        # Update to new key (implementation depends on backend)
        for backend in secrets.backends:
            if backend.set_secret(self.key_name, new_key):
                logger.info(f"Rotated key: {self.key_name}")
                return True

        return False

    def is_valid_key(self, key: str) -> bool:
        """Check if key is valid (current or within grace period)"""
        import time

        current = secrets.get_secret(self.key_name)

        # Check current key
        if key == current:
            return True

        # Check old key within grace period
        if self._old_key and self._rotation_time:
            if key == self._old_key:
                elapsed = time.time() - self._rotation_time
                if elapsed < self.grace_period:
                    return True
                else:
                    # Grace period expired, clear old key
                    self._old_key = None
                    self._rotation_time = None

        return False
