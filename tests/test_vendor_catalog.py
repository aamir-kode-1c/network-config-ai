import json

from app.core.vendor_catalog import (
    catalog_as_product_mapping,
    get_payload_templates,
)


def test_catalog_keeps_legacy_product_names():
    catalog = {
        "cisco": ["ASR 9000"],
    }
    assert catalog_as_product_mapping(
        {"cisco": [{"name": "ASR 9000", "formats": ["cli"], "payloads": {}}]}
    ) == catalog


def test_payload_templates_include_all_supported_formats():
    templates = get_payload_templates("cisco", "ASR 9000")

    assert templates["formats"] == ["cli", "json", "xml", "yang"]
    assert set(templates["payloads"]) == {"cli", "json", "xml", "yang"}
    assert json.loads(json.dumps(templates["payloads"]["json"]))["interface"]
