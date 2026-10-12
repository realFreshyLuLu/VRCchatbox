"""Configure a persistent Windows LAN rule; only the helper is elevated."""
import base64
import hashlib
import ipaddress
import os
from pathlib import Path
import subprocess
import sys


def needs_lan(host):
    if host.lower() == 'localhost':
        return False
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:
        return True


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def encoded(script):
    return base64.b64encode(script.encode('utf-16le')).decode('ascii')


def rule_script(program, port, install=False):
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError('Invalid web port')
    identity = hashlib.sha256(program.lower().encode('utf-8')).hexdigest()[:20]
    name = 'VRCChatbox-LAN-' + identity
    common = f"""
$ErrorActionPreference = 'Stop'
$name = {literal(name)}
$program = {literal(program)}
$port = {literal(port)}
$policy = New-Object -ComObject HNetCfg.FwPolicy2
"""
    if not install:
        return common + """
$rule = @($policy.Rules | Where-Object { $_.Name -eq $name })
if ($rule.Count -eq 1 -and $rule[0].Enabled -and
    $rule[0].Direction -eq 1 -and $rule[0].Action -eq 1 -and
    $rule[0].Protocol -eq 6 -and $rule[0].LocalPorts -eq $port -and
    $rule[0].ApplicationName -eq $program -and
    $rule[0].RemoteAddresses -eq 'LocalSubnet' -and
    $rule[0].Profiles -eq 2147483647 -and -not $rule[0].EdgeTraversal) { exit 0 }
exit 10
"""
    return common + """
$rule = New-Object -ComObject HNetCfg.FWRule
$rule.Name = $name
$rule.Description = 'VRCChatbox: current application and web port, local subnet only.'
$rule.ApplicationName = $program
$rule.Protocol = 6
$rule.LocalPorts = $port
$rule.RemoteAddresses = 'LocalSubnet'
$rule.Direction = 1
$rule.Action = 1
$rule.Profiles = 2147483647
$rule.EdgeTraversal = $false
$rule.Enabled = $true
$policy.Rules.Add($rule)
exit 0
"""


def run_ps(script, timeout=20):
    powershell = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) /
                     'System32/WindowsPowerShell/v1.0/powershell.exe')
    return subprocess.run(
        [powershell, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded(script)],
        capture_output=True, timeout=timeout,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=False,
    ).returncode


def ensure_firewall(host, port):
    if os.name != 'nt' or not needs_lan(host):
        return 'skipped'
    try:
        program = str(Path(sys.executable).resolve())
        check = rule_script(program, port)
        status = run_ps(check)
        if status == 0:
            print('防火墙 / Firewall: LAN rule ready.', flush=True)
            return 'ready'
        if status != 10:
            raise RuntimeError('Cannot inspect Windows Firewall')
        print(f'手机连接需要配置防火墙（TCP {int(port)}，仅本地局域网）。请在 Windows 管理员提示中选择“是”。\n'
              'LAN firewall setup requires Windows administrator approval.', flush=True)
        helper = encoded(rule_script(program, port, install=True))
        # Elevate only a fixed PowerShell command, never the web server.
        elevate = rf"""
$ErrorActionPreference = 'Stop'
try {{
    $p = Start-Process -FilePath "$PSHOME\powershell.exe" -Verb RunAs -WindowStyle Hidden -Wait -PassThru -ArgumentList '-NoProfile -NonInteractive -EncodedCommand {helper}'
    exit $p.ExitCode
}} catch {{ exit 1 }}
"""
        if run_ps(elevate, timeout=180) == 0 and run_ps(check) == 0:
            print('防火墙配置成功，以后启动无需重复授权。 / LAN firewall ready.', flush=True)
            return 'configured'
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
        pass
    print('防火墙配置未完成（可能取消授权或受系统策略限制）。本机仍可使用；手机可能无法连接。\n'
          'Firewall setup incomplete. Restart to retry; local access remains available.', flush=True)
    return 'unavailable'
