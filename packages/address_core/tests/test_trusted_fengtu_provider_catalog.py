import json
from pathlib import Path


def _load_fengtu_source() -> dict:
    config_path = Path("config/trusted_data_sources.json")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return next(item for item in payload["trusted_sources"] if item.get("source_id") == "fengtu")


def test_fengtu_provider_catalog_covers_all_applied_services() -> None:
    fengtu = _load_fengtu_source()
    interfaces = {item["interface_id"]: item for item in fengtu.get("trusted_interfaces", [])}

    required = {
        "address_level_judge": ("group_a", "FENGTU_AK_GROUP_A"),
        "address_real_check": ("group_a", "FENGTU_AK_GROUP_A"),
        "address_resolve_l5": ("group_a", "FENGTU_AK_GROUP_A"),
        "geocode": ("group_b", "FENGTU_AK_GROUP_B"),
        "reverse_geocode": ("group_b", "FENGTU_AK_GROUP_B"),
        "address_type_identify": ("group_b", "FENGTU_AK_GROUP_B"),
        "address_standardize": ("group_b", "FENGTU_AK_GROUP_B"),
        "address_aoi_keyword": ("group_b", "FENGTU_AK_GROUP_B"),
        "address_search_service": ("group_b", "FENGTU_AK_GROUP_B"),
    }
    assert set(required).issubset(set(interfaces))

    for interface_id, (provider_group, key_env) in required.items():
        current = interfaces[interface_id]
        assert current["provider_group"] == provider_group
        assert current["api_key_env"] == key_env

