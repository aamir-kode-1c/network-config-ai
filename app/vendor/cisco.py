def generate(nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    # Product-specific CLI config for Cisco
    if format == 'cli':
        if product == 'ASR 9000':
            lines = [
                f"interface {nb_payload.get('interface', 'GigabitEthernet0/1')}",
                f"  ip address {nb_payload.get('ip', '0.0.0.0')} {nb_payload.get('subnet', '255.255.255.0')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            if nb_payload.get('admin_state'):
                lines.append(f"  shutdown" if nb_payload['admin_state'] == 'down' else "  no shutdown")
            lines.append("exit")
            return '\n'.join(lines)
        elif product == 'Catalyst 9000':
            lines = [
                f"interface {nb_payload.get('interface', 'GigabitEthernet1/0/1')}",
                f"  switchport mode access",
                f"  switchport access vlan {nb_payload.get('vlan', '1')}"
            ]
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            lines.append("exit")
            return '\n'.join(lines)
        elif product == 'Nexus 7000':
            lines = [
                f"interface {nb_payload.get('interface', 'Ethernet1/1')}",
                f"  no shutdown"
            ]
            if nb_payload.get('ip') and nb_payload.get('subnet'):
                lines.append(f"  ip address {nb_payload['ip']} {nb_payload['subnet']}")
            if nb_payload.get('description'):
                lines.append(f"  description '{nb_payload['description']}'")
            lines.append("exit")
            return '\n'.join(lines)
        # Default fallback
        lines = [
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0')}"
        ]
        if nb_payload.get('ip') and nb_payload.get('subnet'):
            lines.append(f" ip address {nb_payload['ip']} {nb_payload['subnet']}")
        if nb_payload.get('description'):
            lines.append(f" description {nb_payload['description']}")
        if nb_payload.get('admin_state'):
            lines.append(f" shutdown" if nb_payload['admin_state'] == 'down' else " no shutdown")
        lines.append('exit')
        return '\n'.join(lines)
    # Other formats
    elif format == 'json':
        import json
        return json.dumps(nb_payload, indent=2)
    elif format == 'xml':
        from xml.etree.ElementTree import Element, tostring
        intf = Element('cisco-interface')
        intf.set('name', nb_payload.get('interface', 'GigabitEthernet0/0'))
        if product:
            intf.set('product', product)
        for k, v in nb_payload.items():
            if k != 'interface':
                child = Element(k)
                child.text = str(v)
                intf.append(child)
        return tostring(intf, encoding='unicode')
    elif format == 'yang':
        return (
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0')} {{\n"
            f"  ip-address {nb_payload.get('ip', '0.0.0.0')};\n"
            f"  subnet {nb_payload.get('subnet', '255.255.255.0')};\n"
            f"  description '{nb_payload.get('description', '')}';\n"
            f"  admin-state {nb_payload.get('admin_state', 'up')};\n"
            f"  product {product or ''};\n"
            f"}}"
        )
    else:
        return str(nb_payload)

    if format == 'cli':
        lines = [
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0')}"
        ]
        if nb_payload.get('ip') and nb_payload.get('subnet'):
            lines.append(f" ip address {nb_payload['ip']} {nb_payload['subnet']}")
        if nb_payload.get('description'):
            lines.append(f" description {nb_payload['description']}")
        if nb_payload.get('admin_state'):
            lines.append(f" shutdown" if nb_payload['admin_state'] == 'down' else " no shutdown")
        lines.append('exit')
        return '\n'.join(lines)
    elif format == 'json':
        import json
        return json.dumps(nb_payload, indent=2)
    elif format == 'xml':
        from xml.etree.ElementTree import Element, tostring
        intf = Element('cisco-interface')
        intf.set('name', nb_payload.get('interface', 'GigabitEthernet0/0'))
        for k, v in nb_payload.items():
            if k != 'interface':
                child = Element(k)
                child.text = str(v)
                intf.append(child)
        return tostring(intf, encoding='unicode')
    elif format == 'yang':
        return (
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0')} {{\n"
            f"  ip-address {nb_payload.get('ip', '0.0.0.0')};\n"
            f"  subnet {nb_payload.get('subnet', '255.255.255.0')};\n"
            f"  description '{nb_payload.get('description', '')}';\n"
            f"  admin-state {nb_payload.get('admin_state', 'up')};\n"
            f"}}"
        )
    else:
        return str(nb_payload)
