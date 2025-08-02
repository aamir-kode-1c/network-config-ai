from app.vendor import nokia, ericsson, openet, cisco, huawei
import shutil

def generate_config(vendor: str, nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    vendor = vendor.lower()
    if vendor == "nokia":
        return nokia.generate(nb_payload, format, product)
    elif vendor == "ericsson":
        return ericsson.generate(nb_payload, format, product)
    elif vendor == "openet":
        return openet.generate(nb_payload, format, product)
    elif vendor == "cisco":
        return cisco.generate(nb_payload, format, product)
    elif vendor == "huawei":
        return huawei.generate(nb_payload, format, product)
    else:
        raise ValueError(f"Unsupported vendor: {vendor}")
