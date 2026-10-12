import sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import firewall


@pytest.mark.parametrize('host', ['127.0.0.1', '127.1.2.3', '::1', 'localhost'])
def test_loopback_never_changes_firewall(host):
    with patch.object(firewall, 'run_ps') as run:
        assert firewall.ensure_firewall(host, 5000) == 'skipped'
        run.assert_not_called()


def test_existing_rule_never_elevates():
    with patch.object(firewall, 'run_ps', return_value=0) as run:
        assert firewall.ensure_firewall('0.0.0.0', 5000) == 'ready'
        assert run.call_count == 1


def test_install_verified_and_only_helper_elevated():
    with patch.object(firewall, 'run_ps', side_effect=[10, 0, 0]) as run:
        assert firewall.ensure_firewall('0.0.0.0', 5000) == 'configured'
        assert '-Verb RunAs' in run.call_args_list[1].args[0]
        assert run.call_count == 3


@pytest.mark.parametrize('results', [[10, 1], [10, 0, 10], [1]])
def test_denial_or_failure_does_not_claim_success(results):
    with patch.object(firewall, 'run_ps', side_effect=results):
        assert firewall.ensure_firewall('0.0.0.0', 5000) == 'unavailable'


def test_timeout_is_nonfatal():
    with patch.object(firewall, 'run_ps', side_effect=firewall.subprocess.TimeoutExpired('ps', 20)):
        assert firewall.ensure_firewall('0.0.0.0', 5000) == 'unavailable'


def test_safe_rule_scope_and_path_escaping():
    script = firewall.rule_script("C:\\Bob's folder\\VRCChatbox.exe", 8123, True)
    assert "$program = 'C:\\Bob''s folder\\VRCChatbox.exe'" in script
    assert "$port = '8123'" in script
    assert "$rule.RemoteAddresses = 'LocalSubnet'" in script
    assert '$rule.ApplicationName = $program' in script
    assert '$rule.Protocol = 6' in script
    assert '$rule.EdgeTraversal = $false' in script
    assert '$rule.Profiles = 2147483647' in script
    with pytest.raises(ValueError):
        firewall.rule_script('app.exe', 0, True)
