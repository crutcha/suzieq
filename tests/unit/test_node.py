from suzieq.poller.nodes.node import Node
import pytest
import asyncssh


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

    mock_connect = mocker.patch.object(asyncssh, "connect")

    test_node = await Node()._init(**mock_kwargs)
    await test_node._init_ssh()

    breakpoint()
    assert mock_connect.call_count == 1
    print("here")
