"""Token-based authentication system for database API access.

This module provides token generation, validation, and management for
securing database operations.
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path


class TokenManager:
    """Manages API tokens for database access."""
    
    def __init__(self, tokens_file: str = "database_tokens.json"):
        """Initialize the token manager.
        
        Args:
            tokens_file: Path to the JSON file storing tokens
        """
        self.tokens_file = Path(tokens_file)
        self.tokens: Dict[str, Dict] = {}
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from file."""
        if self.tokens_file.exists():
            try:
                with open(self.tokens_file, 'r') as f:
                    self.tokens = json.load(f)
                print(f"[AUTH] Loaded {len(self.tokens)} tokens from {self.tokens_file}")
            except Exception as e:
                print(f"[AUTH] Error loading tokens: {e}")
                self.tokens = {}
        else:
            self.tokens = {}
    
    def _save_tokens(self):
        """Save tokens to file."""
        try:
            with open(self.tokens_file, 'w') as f:
                json.dump(self.tokens, f, indent=2)
            print(f"[AUTH] Saved {len(self.tokens)} tokens to {self.tokens_file}")
        except Exception as e:
            print(f"[AUTH] Error saving tokens: {e}")
    
    def generate_token(
        self,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_days: Optional[int] = None
    ) -> str:
        """Generate a new API token.
        
        Args:
            name: Descriptive name for the token (e.g., "Admin Dashboard", "Moderator Bot")
            permissions: List of permissions (e.g., ["read", "write", "delete"])
            expires_days: Number of days until token expires (None for no expiration)
        
        Returns:
            str: The generated token
        """
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        # Hash the token for storage
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_days is not None:
            expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        
        # Store token metadata
        self.tokens[token_hash] = {
            'name': name,
            'permissions': permissions or ['read', 'write'],
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at,
            'last_used': None
        }
        
        self._save_tokens()
        print(f"[AUTH] Generated new token for '{name}'")
        
        return token
    
    def validate_token(
        self,
        token: str,
        required_permission: Optional[str] = None
    ) -> bool:
        """Validate an API token.
        
        Args:
            token: The token to validate
            required_permission: Optional permission to check (e.g., "write")
        
        Returns:
            bool: True if token is valid and has required permission
        """
        if not token:
            return False
        
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check if token exists
        if token_hash not in self.tokens:
            print(f"[AUTH] Invalid token attempt")
            return False
        
        token_data = self.tokens[token_hash]
        
        # Check expiration
        if token_data['expires_at']:
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            if datetime.utcnow() > expires_at:
                print(f"[AUTH] Expired token for '{token_data['name']}'")
                return False
        
        # Check permission
        if required_permission:
            if required_permission not in token_data['permissions']:
                print(f"[AUTH] Token '{token_data['name']}' lacks '{required_permission}' permission")
                return False
        
        # Update last used timestamp
        token_data['last_used'] = datetime.utcnow().isoformat()
        self._save_tokens()
        
        return True
    
    def revoke_token(self, token: str) -> bool:
        """Revoke an API token.
        
        Args:
            token: The token to revoke
        
        Returns:
            bool: True if token was revoked, False if not found
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_hash in self.tokens:
            name = self.tokens[token_hash]['name']
            del self.tokens[token_hash]
            self._save_tokens()
            print(f"[AUTH] Revoked token for '{name}'")
            return True

        return False

    def list_tokens(self) -> List[Dict]:
        """List all tokens with their metadata (excluding the actual token).

        Returns:
            List[Dict]: List of token metadata
        """
        tokens_list = []
        for token_hash, data in self.tokens.items():
            tokens_list.append({
                'name': data['name'],
                'permissions': data['permissions'],
                'created_at': data['created_at'],
                'expires_at': data['expires_at'],
                'last_used': data['last_used'],
                'is_expired': self._is_expired(data)
            })
        return tokens_list

    def _is_expired(self, token_data: Dict) -> bool:
        """Check if a token is expired.

        Args:
            token_data: Token metadata dictionary

        Returns:
            bool: True if expired
        """
        if token_data['expires_at']:
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            return datetime.utcnow() > expires_at
        return False

    def cleanup_expired(self) -> int:
        """Remove all expired tokens.

        Returns:
            int: Number of tokens removed
        """
        expired_hashes = [
            token_hash for token_hash, data in self.tokens.items()
            if self._is_expired(data)
        ]

        for token_hash in expired_hashes:
            del self.tokens[token_hash]

        if expired_hashes:
            self._save_tokens()
            print(f"[AUTH] Cleaned up {len(expired_hashes)} expired tokens")

        return len(expired_hashes)


# Global token manager instance
_token_manager = None


def get_token_manager() -> TokenManager:
    """Get the global token manager instance.

    Returns:
        TokenManager: The global token manager
    """
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def require_auth(permission: str = 'read'):
    """Decorator to require authentication for database operations.

    Args:
        permission: Required permission level ('read', 'write', 'delete')

    Usage:
        @require_auth('write')
        def create_sanction(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract token from kwargs
            token = kwargs.pop('auth_token', None)

            # Validate token
            token_manager = get_token_manager()
            if not token_manager.validate_token(token, permission):
                print(f"[AUTH] Unauthorized access attempt to {func.__name__}")
                return None

            # Call the original function
            return func(*args, **kwargs)

        return wrapper
    return decorator

