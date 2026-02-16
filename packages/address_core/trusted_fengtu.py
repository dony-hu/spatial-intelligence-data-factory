from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_config_path() -> Path:
    return _project_root() / "config" / "trusted_data_sources.json"


def _deep_find_string(payload: Any, keys: set[str]) -> Optional[str]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in keys and isinstance(value, str) and value.strip():
                return value.strip()
            hit = _deep_find_string(value, keys)
            if hit:
                return hit
        return None
    if isinstance(payload, list):
        for item in payload:
            hit = _deep_find_string(item, keys)
            if hit:
                return hit
    return None


class FengtuTrustedClient:
    _network_confirmation_required: bool = False
    _last_network_error: str = ""
    _network_confirmed_once: bool = False
    _last_confirm_by: str = ""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = Path(config_path) if config_path else _default_config_path()
        self._config = self._load_config()

    def enabled(self) -> bool:
        return os.getenv("ADDRESS_TRUSTED_FENGTU_ENABLED", "1") == "1"

    @classmethod
    def _network_confirmed_by_user(cls) -> bool:
        return cls._network_confirmed_once or os.getenv("ADDRESS_TRUSTED_FENGTU_NETWORK_CONFIRM", "0") == "1"

    @classmethod
    def network_confirmation_state(cls) -> Dict[str, Any]:
        return {
            "confirmation_required": cls._network_confirmation_required,
            "last_network_error": cls._last_network_error,
            "last_confirm_by": cls._last_confirm_by,
        }

    @classmethod
    def confirm_network_resume(cls, operator: str) -> Dict[str, Any]:
        cls._network_confirmed_once = True
        cls._last_confirm_by = str(operator or "").strip() or "unknown"
        return cls.network_confirmation_state()

    def _load_config(self) -> Dict[str, Any]:
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _find_interface(self, interface_id: str) -> Optional[Dict[str, Any]]:
        for src in list(self._config.get("trusted_sources") or []):
            if str(src.get("source_id")) != "fengtu":
                continue
            for item in list(src.get("trusted_interfaces") or []):
                if str(item.get("interface_id")) == interface_id:
                    return item
        return None

    @staticmethod
    def _render_template(template_obj: Any, values: Dict[str, Any]) -> Any:
        if isinstance(template_obj, str):
            rendered = template_obj
            for key, value in values.items():
                rendered = rendered.replace("{" + key + "}", str(value or ""))
            return rendered
        if isinstance(template_obj, dict):
            return {key: FengtuTrustedClient._render_template(value, values) for key, value in template_obj.items()}
        if isinstance(template_obj, list):
            return [FengtuTrustedClient._render_template(value, values) for value in template_obj]
        return template_obj

    @staticmethod
    def _compact_empty(data: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in data.items() if v not in ("", None)}

    def _auth_headers(self, interface: Dict[str, Any]) -> Dict[str, str]:
        headers = {str(k): str(v) for k, v in dict(interface.get("headers") or {}).items()}
        env_name = str(interface.get("api_key_env") or "")
        env_key = os.getenv(env_name, "")
        if str(interface.get("ak_in", "header")) == "header" and env_key:
            headers["ak"] = env_key
        return headers

    def call(self, interface_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        interface = self._find_interface(interface_id)
        if not interface:
            return {"ok": False, "reason": "interface_not_found", "interface_id": interface_id}

        if not self.enabled():
            return {"ok": False, "reason": "disabled"}
        if FengtuTrustedClient._network_confirmation_required:
            if not FengtuTrustedClient._network_confirmed_by_user():
                return {
                    "ok": False,
                    "reason": f"await_user_confirmation:{FengtuTrustedClient._last_network_error or 'network_error'}",
                }
            FengtuTrustedClient._network_confirmation_required = False
            FengtuTrustedClient._last_network_error = ""
            FengtuTrustedClient._network_confirmed_once = False

        method = str(interface.get("method") or "GET").upper()
        base_url = str(interface.get("base_url") or "")
        request_template = dict(interface.get("request_template") or {})
        headers = self._auth_headers(interface)
        env_name = str(interface.get("api_key_env") or "")
        env_key = os.getenv(env_name, "")

        query = self._compact_empty(
            self._render_template(dict(request_template.get("query") or {}), payload)
            if isinstance(request_template.get("query"), dict)
            else {}
        )
        body = (
            self._render_template(dict(request_template.get("body") or {}), payload)
            if isinstance(request_template.get("body"), dict)
            else None
        )
        if str(interface.get("ak_in", "header")) == "query" and env_key and "ak" not in query:
            query["ak"] = env_key
        if query:
            base_url = f"{base_url}?{urlencode(query)}"

        body_bytes = None
        if method == "POST" and body is not None:
            body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        try:
            request = Request(base_url, data=body_bytes, headers=headers, method=method)
            with urlopen(request, timeout=float(os.getenv("ADDRESS_TRUSTED_FENGTU_TIMEOUT_SEC", "0.8"))) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return {"ok": True, "interface_id": interface_id, "data": data}
        except Exception as exc:
            FengtuTrustedClient._network_confirmation_required = True
            FengtuTrustedClient._last_network_error = exc.__class__.__name__
            FengtuTrustedClient._network_confirmed_once = False
            return {"ok": False, "reason": exc.__class__.__name__, "interface_id": interface_id}

    def standardize(self, address: str, province: str = "", city: str = "", county: str = "") -> Optional[str]:
        response = self.call(
            "address_standardize",
            {
                "address": address,
                "province": province,
                "city": city,
                "county": county,
            },
        )
        if not response.get("ok"):
            return None
        data = response.get("data")
        return _deep_find_string(data, {"stdAddress", "standardizedAddress", "fullAddress", "address", "result"})

    def is_real_address(self, address: str, province: str = "", city: str = "", county: str = "") -> Optional[bool]:
        response = self.call(
            "address_real_check",
            {
                "address": address,
                "province": province,
                "city": city,
                "county": county,
            },
        )
        if not response.get("ok"):
            return None
        data = response.get("data")
        marker = _deep_find_string(
            data,
            {
                "isReal",
                "real",
                "realFlag",
                "result",
                "conclusion",
                "status",
            },
        )
        if marker is None:
            return None
        text = marker.lower()
        if any(token in text for token in ("false", "not", "invalid", "fake", "否", "无效", "不存在")):
            return False
        if any(token in text for token in ("true", "valid", "real", "是", "有效", "存在")):
            return True
        return None
