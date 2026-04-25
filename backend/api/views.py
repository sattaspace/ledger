# backend/api/views.py (or more commonly api/api.py)

from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_extra.permissions import AllowAny

# 1. Initialize the API
api = NinjaExtraAPI(
    title="Satta Ledger API",
    version="1.0.0",
    description="Satta Ledger API for managing personal accounting and notifications",
    urls_namespace="sattaledger",
)

# 2. Register JWT Controller
# This adds /token and /refresh endpoints automatically
api.register_controllers(NinjaJWTDefaultController)

# 3. Auto-discover your custom controllers
# Ensure your custom controllers are in a file named `controllers.py`
# within your apps so this can find them.
api.auto_discover_controllers()
