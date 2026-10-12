"""Show addresses without opening a browser; serve source and packaged builds."""
import socket
import ipaddress
import ctypes
import os

def addresses(host, port):
    if host in ('127.0.0.1', 'localhost', '::1'):
        return [f'http://{host if host != "::1" else "[::1]"}:{port}/'], []
    if host not in ('0.0.0.0', '::', ''):
        return [f'http://{host}:{port}/'], [f'http://{host}:{port}/']
    candidates = set()
    try:
        candidates.update(item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1', 9))
            candidates.add(sock.getsockname()[0])
    except OSError:
        pass
    lan = [f'http://{ip}:{port}/' for ip in sorted(candidates)
           if not ipaddress.ip_address(ip).is_loopback and not ipaddress.ip_address(ip).is_unspecified]
    return [f'http://127.0.0.1:{port}/'], lan

def system_language():
    import locale
    try:
        name = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), 'en') if os.name == 'nt' else locale.getlocale()[0]
        code = (name or 'en').replace('_','-').split('-')[0]
        return {'zh':'zh-CN','ja':'ja','ko':'ko'}.get(code,'en')
    except Exception:
        return 'en'

def serve(app, config):
    from waitress import create_server
    server = create_server(app, host=config['WEB_IP'], port=int(config['WEB_PORT']))
    local, lan = addresses(config['WEB_IP'], config['WEB_PORT'])
    print('\nVRC Chatbox 1.4.1\n', flush=True)
    for url in local: print('本机 / This computer: '+url, flush=True)
    for url in lan: print('局域网 / LAN devices: '+url, flush=True)
    if not lan: print('LAN: unavailable (loopback binding or no network adapter).', flush=True)
    from firewall import ensure_firewall
    ensure_firewall(config['WEB_IP'], config['WEB_PORT'])
    print('Open an address manually. Use the same Wi-Fi/LAN.\nEnable OSC in VRChat. Ctrl+C to stop.\n', flush=True)
    try: server.run()
    finally: server.close()
