def generate(nb_payload: dict, format: str = 'cli', product: str = None) -> str:
    """
    Generate simulated Huawei device configuration in the requested format.

    Args:
        nb_payload (dict): Northbound API payload with interface, ip, subnet, description, admin_state, etc.
        format (str): Output format ('cli', 'json', 'xml', 'yang').
        product (str): Huawei product name.

    Returns:
        str: Simulated configuration in the requested format.
    """
    if format == 'cli':
        # Product-specific CLI simulation for Huawei
        if product in ['CloudEngine S Series', 'AR G3', 'NE40E']:
            lines = [
                # Add standard Huawei CLI config lines here, e.g.:
                f"interface {nb_payload.get('interface', 'GigabitEthernet0/0/0')}"
            ]
            if nb_payload.get('ip') and nb_payload.get('subnet'):
                lines.append(f"  ip address {nb_payload['ip']} {nb_payload['subnet']}")
            if nb_payload.get('description'):
                lines.append(f"  description {nb_payload['description']}")
            if nb_payload.get('mtu'):
                lines.append(f"  mtu {nb_payload['mtu']}")
            if nb_payload.get('vrf'):
                lines.append(f"  vrf-binding {nb_payload['vrf']}")
            if nb_payload.get('admin_state'):
                lines.append(f"  shutdown" if nb_payload['admin_state'] == 'down' else "  undo shutdown")
            # Add any additional fields not already handled
            handled_keys = {'interface','ip','subnet','description','mtu','vrf','admin_state','shutdown'}
            for k, v in nb_payload.items():
                if k not in handled_keys:
                    lines.append(f"  {k} {v}")
            lines.append("quit")
            return '\n'.join(lines)
        # Default fallback for unknown or generic Huawei products
        lines = [
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0/1')}",
            f"  ip address {nb_payload.get('ip', '0.0.0.0')} {nb_payload.get('subnet', '255.255.255.0')}"
        ]
        if nb_payload.get('description'):
            lines.append(f'  description "{nb_payload["description"]}"')
        if nb_payload.get('admin_state'):
            lines.append(f"  admin-state {nb_payload['admin_state']}")
        lines.append("quit")
        return '\n'.join(lines)
    elif format == 'json':
        import json
        return json.dumps(nb_payload, indent=2)
    elif format == 'xml':
        from xml.etree.ElementTree import Element, tostring
        intf = Element('huawei-interface')
        intf.set('name', nb_payload.get('interface', 'GigabitEthernet0/0/1'))
        for k, v in nb_payload.items():
            if k != 'interface':
                child = Element(k)
                child.text = str(v)
                intf.append(child)
        return tostring(intf, encoding='unicode')
    elif format == 'yang':
        return (
            f"interface {nb_payload.get('interface', 'GigabitEthernet0/0/1')} {{\n"
            f"  ip-address {nb_payload.get('ip', '0.0.0.0')};\n"
            f"  subnet {nb_payload.get('subnet', '255.255.255.0')};\n"
            f"  description {nb_payload.get('description', '')};\n"
            f"  admin-state {nb_payload.get('admin_state', 'up')};\n"
            f"}}"
        )
    else:
        return str(nb_payload)
