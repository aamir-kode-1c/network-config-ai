import json
import os

VENDOR_DIR = os.path.join(os.path.dirname(__file__), "app", "vendor")
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "vendor_products.json")

# Marker for CLI config block in each vendor file
CLI_MARKER = "# Product-specific CLI config for"

def update_vendor_file(vendor, products):
    py_file = os.path.join(VENDOR_DIR, f"{vendor}.py")
    if not os.path.exists(py_file):
        print(f"Vendor file {py_file} not found.")
        return
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    updated = False
    for product in products:
        # Check if product already has a logic block
        if product in content:
            continue
        # Add a placeholder CLI logic for the new product
        marker = "# Product-specific CLI config for"
        insert_point = content.find(marker)
        if insert_point == -1:
            # Insert after function signature
            insert_point = content.find(":\n") + 2
        before = content[:insert_point]
        after = content[insert_point:]
        new_block = f"        elif product == '{product}':\n            lines = [\n                f\"# TODO: Implement CLI for {product}\"\n            ]\n            lines.append(\"# Add config lines here\")\n            return '\\n'.join(lines)\n"
        content = before + new_block + after
        updated = True
    if updated:
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {py_file} with new products.")

def main():
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        registry = json.load(f)
    for vendor, products in registry.items():
        update_vendor_file(vendor, products)

if __name__ == "__main__":
    main()
