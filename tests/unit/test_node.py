from suzieq.poller.nodes.node import Node
from unittest.mock import MagicMock
import pytest
import asyncssh
import asyncio


@pytest.mark.asyncio
async def test_node_stuff(mocker):
    mock_kwargs = {
        "address": "test-device",
        "username": "test-user",
        "port": None,
        "password": "vagrant",
        "passphrase": None,
        "transport": "ssh",
        "devtype": "eos",
        "ssh_keyfile": None,
        "ssh_config_file": "/Users/test-user/.ssh/config",
        "jump_host": "",
        "jump_host_key_file": "",
        "namespace": "eos",
        "ignore_known_hosts": None,
    }
    expected_connect_arguments = {
        "username": "test-user",
        "config": "/Users/test-user/.ssh/config",
        "port": 22,
    }

    asyncssh_mock = MagicMock(spec=asyncssh.SSHClientConnection)
    future = asyncio.Future()
    future.set_result(asyncssh_mock)
    mock_connect = mocker.patch.object(asyncssh, "connect", return_value=future)

    await Node()._init(**mock_kwargs)

    assert mock_connect.call_count == 1
    assert mock_connect.call_args[0][0] == "test-device"
    assert mock_connect.call_args[1] == expected_connect_arguments
