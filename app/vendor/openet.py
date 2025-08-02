def generate(nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    # Product-specific CLI config for Openet
    if format == 'cli':
        if product == 'Policy Manager':
            lines = [
                f"pm-if {nb_payload.get('interface', 'pm0')}",
                f"  ip {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            if nb_payload.get('admin_state'):
                lines.append(f"  state {nb_payload['admin_state']}")
            lines.append("end")
            return '\n'.join(lines)
        elif product == 'Charging Gateway':
            lines = [
                f"cg-if {nb_payload.get('interface', 'cg0')}",
                f"  ip {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  note '{nb_payload['description']}'")
            if nb_payload.get('mtu'):
                lines.append(f"  mtu {nb_payload['mtu']}")
            if nb_payload.get('vrf'):
                lines.append(f"  vrf {nb_payload['vrf']}")
            if nb_payload.get('admin_state'):
                lines.append(f"  status {nb_payload['admin_state']}")
            handled_keys = {'interface','ip','subnet','description','mtu','vrf','admin_state'}
            for k, v in nb_payload.items():
                if k not in handled_keys:
                    lines.append(f"  {k} {v}")
            lines.append("end")
            return '\n'.join(lines)
        # Default fallback
        lines = [
            f"openet-interface {nb_payload.get('interface', 'ethX')}",
            f"  ip {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
        ]
        if nb_payload.get('description'):
            lines.append(f"  note \"{nb_payload['description']}\"")
        if nb_payload.get('mtu'):
            lines.append(f"  mtu {nb_payload['mtu']}")
        if nb_payload.get('vrf'):
            lines.append(f"  vrf {nb_payload['vrf']}")
        if nb_payload.get('admin_state'):
            lines.append(f"  state {nb_payload['admin_state']}")
        handled_keys = {'interface','ip','subnet','description','mtu','vrf','admin_state','shutdown'}
        for k, v in nb_payload.items():
            if k not in handled_keys:
                lines.append(f"  {k} {v}")
        lines.append("end")
        return '\n'.join(lines)
    elif format == 'json':
        import json
        obj = dict(nb_payload)
        if product:
            obj['product'] = product
        return json.dumps(obj, indent=2)
    elif format == 'xml':
        from xml.etree.ElementTree import Element, tostring
        if product == 'Policy Manager':
            intf = Element('openet-policy-manager-interface')
        elif product == 'Charging Gateway':
            intf = Element('openet-charging-gateway-interface')
        else:
            intf = Element('openet-interface')
        intf.set('name', nb_payload.get('interface', 'ethX'))
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
            f"openet-interface {nb_payload.get('interface', 'ethX')} {{",
            f"  ip-address {nb_payload.get('ip', '0.0.0.0')};",
            f"  subnet {nb_payload.get('subnet', '24')};",
            f"  note '{nb_payload.get('description', '')}';",
            f"  state {nb_payload.get('admin_state', 'up')};"
        ]
        if product:
            yang_lines.append(f"  product {product};")
        yang_lines.append("}")
        return '\n'.join(yang_lines)
    else:
        return str(nb_payload)

