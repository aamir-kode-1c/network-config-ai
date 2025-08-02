def generate(nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    # Product-specific CLI config for Ericsson
    if format == 'cli':
        if product == 'Router 6000':
            lines = [
                f"interface {nb_payload.get('interface', 'ge-0/0/1')}",
                f"  ip address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            if nb_payload.get('admin_state'):
                lines.append(f"  admin-state {nb_payload['admin_state']}")
            lines.append("exit")
            return '\n'.join(lines)
        elif product == 'MINI-LINK':
            lines = [
                f"minilink-if {nb_payload.get('interface', 'ml-if1')}",
                f"  ip {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  note '{nb_payload['description']}'")
            lines.append("end")
            return '\n'.join(lines)
        elif product == 'SSR 8000':
            lines = [
                f"set interface {nb_payload.get('interface', 'eth0')}",
                f"  address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            lines.append("commit")
            return '\n'.join(lines)
        # Default fallback
        lines = [
            f"interface {nb_payload.get('interface', 'ge-0/0/1')}",
            f"  address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
        ]
        if nb_payload.get('description'):
            lines.append(f"  description \"{nb_payload['description']}\"")
        if nb_payload.get('admin_state'):
            lines.append(f"  admin-state {nb_payload['admin_state']}")
        lines.append("exit")
        return '\n'.join(lines)
    elif format == 'json':
        import json
        obj = dict(nb_payload)
        if product:
            obj['product'] = product
        return json.dumps(obj, indent=2)
    elif format == 'xml':
        from xml.etree.ElementTree import Element, tostring
        if product == 'Router 6000':
            intf = Element('ericsson-router6000-interface')
        elif product == 'MINI-LINK':
            intf = Element('ericsson-minilink-interface')
        elif product == 'SSR 8000':
            intf = Element('ericsson-ssr8000-interface')
        else:
            intf = Element('ericsson-interface')
        intf.set('name', nb_payload.get('interface', 'ge-0/0/1'))
        if product:
            intf.set('product', product)
        for k, v in nb_payload.items():
            if k != 'interface':
                child = Element(k)
                child.text = str(v)
                intf.append(child)
        return tostring(intf, encoding='unicode')
    elif format == 'yang':
        yang_lines = [
            f"interface {nb_payload.get('interface', 'ge-0/0/1')} {{",
            f"  ip-address {nb_payload.get('ip', '0.0.0.0')};",
            f"  subnet {nb_payload.get('subnet', '24')};",
            f"  description '{nb_payload.get('description', '')}';",
            f"  admin-state {nb_payload.get('admin_state', 'up')};"
        ]
        if product:
            yang_lines.append(f"  product {product};")
        yang_lines.append("}")
        return '\n'.join(yang_lines)
    else:
        return str(nb_payload)
