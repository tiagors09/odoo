# Implementing a Native Firebase-Like Token Auth System in Odoo 16

This guide provides a comprehensive, step-by-step implementation blueprint for building a secure, stateless, native token-authentication architecture (Access Token + Refresh Token with TTL and Token Rotation) inside an Odoo 16 custom addon (`curso_odoo`), without any external third-party identity providers like Firebase.

---

## 1. Understanding the Security Foundation: `ir.model.access.csv`

Before writing token logic, you must understand how Odoo's Access Control Lists (`ir.model.access.csv`) interact with API requests.

### Role of `ir.model.access.csv`

In `security/ir.model.access.csv`, you define rules like:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_lesson_odoo_user,lesson.odoo user,model_lesson_odoo,base.group_user,1,1,1,1
```

* **What it does:** It dictates what operations a user belonging to a specific group (`base.group_user`) can perform on a specific model (`lesson.odoo`).
* **The API Trap:** Many developers make API controllers public (`auth="public"`) and bypass security entirely using `.sudo()`.
* **The Secure Way:** When implementing native token auth, your controller validates the token, identifies the corresponding Odoo `res.users` record, and executes ORM operations using `.with_user(user)` instead of `.sudo()`. By doing this, **Odoo's native ACLs (`ir.model.access.csv`) and Record Rules (`ir.rule`) are strictly enforced** for every API request based on the user's assigned groups!

---

## 2. Step 1: Extend `res.users` to Store Tokens and TTL

To support token management natively, you need to store tokens, expiration times (TTL), and rotation metadata. Create a model extension file `addons/curso_odoo/models/res_users.py`:

```python
from odoo import fields, models
import datetime


class ResUsers(models.Model):
    _inherit = "res.users"

    # Opaque tokens and TTL fields
    access_token = fields.Char(string="API Access Token", index=True, copy=False)
    access_token_expiry = fields.Datetime(string="Access Token Expiry", copy=False)
    
    refresh_token = fields.Char(string="API Refresh Token", index=True, copy=False)
    refresh_token_expiry = fields.Datetime(string="Refresh Token Expiry", copy=False)
```

---

## 3. Step 2: Build the Auth Controller (Login, Refresh, Logout)

Create an authentication controller file `addons/curso_odoo/controllers/auth_controller.py` to handle the Firebase-like authentication lifecycle (Sign-In, Token Refresh with Rotation, and Sign-Out).

```python
import logging
import secrets
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# TTL Configurations
ACCESS_TOKEN_LIFETIME_MINUTES = 15
REFRESH_TOKEN_LIFETIME_DAYS = 7


class NativeAuthAPI(http.Controller):

    @http.route("/api/v1/auth/login", type="json", auth="public", methods=["POST"], csrf=False)
    def login(self, **kw):
        """Authenticates user credentials and returns Access & Refresh tokens."""
        params = request.params or kw
        login = params.get("login")
        password = params.get("password")

        if not login or not password:
            return {"status": "error", "code": "MISSING_CREDENTIALS", "message": "Login and password are required."}

        try:
            # Native Odoo authentication validation
            uid = request.session.authenticate(request.db, login, password)
            if not uid:
                return {"status": "error", "code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}

            user = request.env["res.users"].sudo().browse(uid)

            # Generate high-entropy opaque tokens
            access_token = secrets.token_hex(32)
            refresh_token = secrets.token_hex(48)

            now = datetime.utcnow()
            access_expiry = now + timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES)
            refresh_expiry = now + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)

            # Save tokens and TTLs to the user record
            user.sudo().write({
                "access_token": access_token,
                "access_token_expiry": access_expiry.strftime('%Y-%m-%d %H:%M:%S'),
                "refresh_token": refresh_token,
                "refresh_token_expiry": refresh_expiry.strftime('%Y-%m-%d %H:%M:%S'),
            })

            return {
                "status": "success",
                "code": "LOGIN_SUCCESS",
                "access_token": access_token,
                "expires_in": ACCESS_TOKEN_LIFETIME_MINUTES * 60,
                "refresh_token": refresh_token,
            }
        except Exception as e:
            _logger.error("Login error: %s", str(e))
            return {"status": "error", "code": "SERVER_ERROR", "message": "Authentication process failed."}

    @http.route("/api/v1/auth/refresh", type="json", auth="public", methods=["POST"], csrf=False)
    def refresh_token(self, **kw):
        """Exchanges a valid Refresh Token for a new Access Token (Token Rotation)."""
        params = request.params or kw
        token = params.get("refresh_token")

        if not token:
            return {"status": "error", "code": "MISSING_TOKEN", "message": "Refresh token is required."}

        user = request.env["res.users"].sudo().search([("refresh_token", "=", token)], limit=1)
        
        if not user:
            return {"status": "error", "code": "INVALID_TOKEN", "message": "Invalid refresh token."}

        # Check TTL expiration
        now = datetime.utcnow()
        if user.refresh_token_expiry and datetime.strptime(str(user.refresh_token_expiry), '%Y-%m-%d %H:%M:%S') < now:
            return {"status": "error", "code": "TOKEN_EXPIRED", "message": "Refresh token has expired. Please log in again."}

        # Token Rotation: Issue new access token and rotate refresh token for enhanced security
        new_access_token = secrets.token_hex(32)
        new_refresh_token = secrets.token_hex(48)
        
        access_expiry = now + timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES)
        refresh_expiry = now + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)

        user.sudo().write({
            "access_token": new_access_token,
            "access_token_expiry": access_expiry.strftime('%Y-%m-%d %H:%M:%S'),
            "refresh_token": new_refresh_token,
            "refresh_token_expiry": refresh_expiry.strftime('%Y-%m-%d %H:%M:%S'),
        })

        return {
            "status": "success",
            "code": "TOKEN_REFRESHED",
            "access_token": new_access_token,
            "expires_in": ACCESS_TOKEN_LIFETIME_MINUTES * 60,
            "refresh_token": new_refresh_token,
        }

    @http.route("/api/v1/auth/logout", type="json", auth="public", methods=["POST"], csrf=False)
    def logout(self, **kw):
        """Invalidates tokens on sign-out."""
        params = request.params or kw
        token = params.get("refresh_token") or params.get("access_token")
        
        if token:
            user = request.env["res.users"].sudo().search([
                "|", ("refresh_token", "=", token), ("access_token", "=", token)
            ], limit=1)
            if user:
                user.sudo().write({
                    "access_token": False,
                    "access_token_expiry": False,
                    "refresh_token": False,
                    "refresh_token_expiry": False,
                })

        return {"status": "success", "code": "LOGOUT_SUCCESS", "message": "Successfully logged out."}
```

---

## 4. Step 3: Create the Token Validation Helper Middleware

Create a validation helper method (e.g., inside `addons/curso_odoo/utils/security.py`) to intercept requests, inspect the `Authorization: Bearer <TOKEN>` header, verify the TTL, and return the authorized Odoo user.

```python
from datetime import datetime
from odoo.http import request


def authenticate_native_token():
    """Validates Access Token header, checks TTL expiration, 
    and returns the authorized Odoo user respecting ACLs.
    """
    auth_header = request.httprequest.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Missing or malformed Authorization header."

    token = auth_header.split(" ")[1]

    user = request.env["res.users"].sudo().search([("access_token", "=", token)], limit=1)
    if not user:
        return None, "Invalid access token."

    # Verify Access Token TTL
    now = datetime.utcnow()
    if user.access_token_expiry and datetime.strptime(str(user.access_token_expiry), '%Y-%m-%d %H:%M:%S') < now:
        return None, "Access token has expired. Use your refresh token."

    return user, None
```

---

## 5. Step 4: Protect Business Endpoints with User Context

Update your business routes (e.g., in `addons/curso_odoo/controllers/lessons_api.py`) to enforce authentication and execute actions using `.with_user(user)` so `ir.model.access.csv` rules are properly validated:

```python
from odoo import http
from odoo.http import request
from .utils.security import authenticate_native_token


class LessonsAPI(http.Controller):

    @http.route("/lessons/create", type="json", auth="public", methods=["POST"], csrf=False)
    def create_lesson(self, **kw):
        # 1. Enforce native token authentication
        user, error_msg = authenticate_native_token()
        if not user:
            return {"status": "error", "code": "UNAUTHORIZED", "message": error_msg}

        try:
            params = request.params or kw
            name = params.get("name")
            desc = params.get("desc")
            duration = params.get("duration", "ten_minutes")

            if not name:
                return {"status": "error", "code": "MISSING_REQUIRED_FIELD", "field": "name"}

            # 2. Execute with the user's context (strictly enforcing ir.model.access.csv rules)
            new_lesson = request.env["lesson.odoo"].with_user(user).create({
                "name": name,
                "desc": desc,
                "duration": duration,
            })

            return {
                "status": "success",
                "code": "LESSON_CREATED",
                "lesson": {
                    "id": new_lesson.id,
                    "name": new_lesson.name,
                    "desc": new_lesson.desc,
                    "duration": new_lesson.duration,
                }
            }
        except Exception as e:
            return {"status": "error", "code": "DATABASE_ERROR", "message": str(e)}
```

---

## Summary Checklist

1. **`ir.model.access.csv`**: Defines permissions for user groups. By using `.with_user(user)`, Odoo automatically applies these permissions to API requests.
2. **Access Token + TTL**: Short-lived (e.g., 15 minutes) secure token sent in the `Authorization` header.
3. **Refresh Token + Rotation**: Long-lived token used to acquire new access tokens securely while invalidating old credentials.
