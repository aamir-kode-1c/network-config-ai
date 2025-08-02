def generate(nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    # Product-specific CLI config for Nokia
    if format == 'cli':
        if product == '7750 SR':
            lines = [
                f"configure router interface {nb_payload.get('interface', 'eth0')}",
                f"  address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f'  description "{nb_payload["description"]}"')
            if nb_payload.get('mtu'):
                lines.append(f"  mtu {nb_payload['mtu']}")
            if nb_payload.get('vrf'):
                lines.append(f"  vrf {nb_payload['vrf']}")
            if nb_payload.get('admin_state'):
                lines.append(f"  admin-state {nb_payload['admin_state']}")
            handled_keys = {'interface','ip','subnet','description','mtu','vrf','admin_state','shutdown'}
            for k, v in nb_payload.items():
                if k not in handled_keys:
                    lines.append(f"  {k} {v}")
            lines.append("exit")
            return '\n'.join(lines)
        elif product == '7250 IXR':
            lines = [
                f"set interface {nb_payload.get('interface', 'eth0')}",
                f"  ip {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            if nb_payload.get('description'):
                lines.append(f'  description "{nb_payload["description"]}"')
            lines.append("commit")
            return '\n'.join(lines)
        elif product == 'SROS':
            lines = [
                f"/configure port {nb_payload.get('interface', 'eth0')}",
                f"  ip-address {nb_payload.get('ip', '0.0.0.0')} {nb_payload.get('subnet', '255.255.255.0')}"
            ]
            if nb_payload.get('description'):
                lines.append(f'  description "{nb_payload["description"]}"')
            lines.append("exit")
            return '\n'.join(lines)
        elif product == 'Nuage VNS':
            lines = [
                f"vns interface {nb_payload.get('interface', 'eth0')}",
                f"  address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
            ]
            lines.append("exit")
            return '\n'.join(lines)
        # Default fallback
        lines = [
            f"interface {nb_payload.get('interface', 'eth0')}",
            f"  address {nb_payload.get('ip', '0.0.0.0')}/{nb_payload.get('subnet', '24')}"
        ]
        if nb_payload.get('description'):
            lines.append(f'  description "{nb_payload["description"]}"')
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
        if product == '7750 SR':
            intf = Element('nokia-7750-sr-interface')
        elif product == '7250 IXR':
            intf = Element('nokia-7250-ixr-interface')
        elif product == 'SROS':
            intf = Element('nokia-sros-interface')
        elif product == 'Nuage VNS':
            intf = Element('nokia-nuage-vns-interface')
        else:
            intf = Element('nokia-interface')
        intf.set('name', nb_payload.get('interface', 'eth0'))
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
            f"interface {nb_payload.get('interface', 'eth0')} {{",
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
