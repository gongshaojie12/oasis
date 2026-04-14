from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger("engine.callback")

_DEFAULT_TIMEOUT = 10.0
_MAX_RETRIES = 3


class CallbackClient:
    """HTTP client that posts updates back to the Nuxt API.

    Endpoints:
        POST {base_url}/api/internal/progress   - step progress
        POST {base_url}/api/internal/complete    - simulation done
        POST {base_url}/api/internal/error       - simulation failed
    """

    def __init__(
        self,
        base_url: str,
        internal_api_key: str,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "X-Internal-Key": internal_api_key,
        }
        self._timeout = timeout
        self._max_retries = max_retries

    async def _post(self, path: str, body: dict[str, Any]) -> bool:
        """POST to the given path with retry logic.

        Returns True if any attempt succeeded, False if all attempts failed.
        """
        url = f"{self._base_url}{path}"
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        url, json=body, headers=self._headers
                    )
                    if resp.status_code < 400:
                        logger.debug(
                            "Callback %s succeeded (attempt %d)", path, attempt
                        )
                        return True
                    logger.warning(
                        "Callback %s returned %d (attempt %d/%d)",
                        path,
                        resp.status_code,
                        attempt,
                        self._max_retries,
                    )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Callback %s failed (attempt %d/%d): %s",
                    path,
                    attempt,
                    self._max_retries,
                    exc,
                )
        logger.error(
            "Callback %s failed after %d attempts", path, self._max_retries
        )
        return False

    async def send_progress(
        self,
        task_id: str,
        current_step: int,
        total_steps: int,
        progress: float,
        data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Report step-level progress to Nuxt."""
        body: dict[str, Any] = {
            "task_id": task_id,
            "current_step": current_step,
            "total_steps": total_steps,
            "progress": round(progress, 4),
        }
        if data:
            body["data"] = data
        return await self._post("/api/internal/progress", body)

    async def send_complete(
        self,
        task_id: str,
        result: dict[str, Any],
    ) -> bool:
        """Report successful simulation completion to Nuxt."""
        body = {
            "task_id": task_id,
            "result": result,
        }
        return await self._post("/api/internal/complete", body)

    async def send_error(
        self,
        task_id: str,
        error: str,
    ) -> bool:
        """Report simulation failure to Nuxt."""
        body = {
            "task_id": task_id,
            "error": error,
        }
        return await self._post("/api/internal/error", body)
