import os
import pytest
from fastapi.testclient import TestClient

from tests.conftest import cli_commands, create_dummy_config_file

from suzieq.restServer.query import app, get_configured_api_key, API_KEY_NAME

ENDPOINT = "http://localhost:8000/api/v1"

VERBS = ['show', 'summarize', 'assert', 'lpm',
         'unique']  # add 'top' when it's supported

#
# The code logic is that you define all the filters you want to test in
# FILTERS. If a filter isn't in FILTERS, it isn't tested.
# Next:
#    * for every filter that has a good result against an object,
#      add it to the GOOD_FILTERS_FOR_SERVICE_VERB list
#    * for every filter that has a bad result against an object, such
#      as state=up in case of BGP, add it to the BAD_FILTERS list with
#      the appropriate error code.
#    * Any verb that doesn't work for an object such as assert for device,
#      add it to the BAD_VERBS list
#    * If a result is empty such as state=notConnected, add that object/verb
#      filter result to the GOOD_FILTER_EMPTY_RESULT_FILTER list. You can catch
#      an empty, but good result, because of the assertion error:
#      AssertionError: assert 2 > 10
#
FILTERS = ['', 'hostname=leaf01', 'namespace=ospf-ibgp',
           'hostname=leaf01%20spine01',
           'namespace=ospf-ibgp%20ospf-single',
           'address=10.0.0.11',
           'dest=172.16.2.104&src=172.16.1.101&namespace=ospf-ibgp',
           'columns=namespace',
           'view=latest',
           'address=10.0.0.11&view=all',
           'ipAddress=10.0.0.11',
           'vrf=default',
           'ipvers=v4',
           'macaddr=44:39:39:ff:40:95',
           'macaddr=44:39:39:FF:40:95',
           'macaddr=4439.39FF.4095',
           'macaddr=4439.39ff.4095',
           'macaddr=44:39:39:ff:00:13%2044:39:39:ff:00:24',
           'peer=eth1.2',
           'vni=13',
           'vni=13%2024',
           'mountPoint=/',
           'ifname=swp1',
           'type=ethernet',
           'vlan=13',
           'remoteVtepIp=10.0.0.101',
           'bd=',
           'state=pass',
           'oif=eth1.4',
           'localOnly=True',
           'prefix=10.0.0.101/32',
           'protocol=bgp',
           'prefixlen=24',
           'service=device',
           'polled=True',
           'usedPercent=8',
           'column=prefixlen',
           'status=pass',
           'status=fail',
           'status=all',
           'status=whatever',
           'vlanName=vlan13',
           'state=up',
           'via=lldp',
           'via=arpnd',
           'state=down',
           'state=notConnected',
           'state=active',
           'priVtepIp=10.0.0.112',
           'query_str=hostname%20==%20"leaf01"',
           'query_str=hostname=="leaf01"%20and%201000<mtu<2000'
           ]

# these should only succeed for the specific service/verb tuples
GOOD_FILTERS_FOR_SERVICE_VERB = {
    'address=10.0.0.11': ['route/lpm'],
    'address=10.0.0.11&view=all': ['route/lpm'],
    'bd=': ['mac/show'],
    'dest=172.16.2.104&src=172.16.1.101&namespace=ospf-ibgp':
    ['path/show', 'path/summarize'],
    'ifname=swp1': ['interface/show', 'interface/assert',
                    'lldp/show', 'ospf/show', 'ospf/assert'],
    'ipAddress=10.0.0.11': ['arpnd/show'],
    'ipvers=v4': ['address/show'],
    'localOnly=True': ['mac/show'],
    'macaddr=44:39:39:ff:00:13': ['arpnd/show', 'mac/show'],
    'mountPoint=/': ['fs/show'],
    'oif=eth1.4': ['arpnd/show'],
    'peer=eth1.2': ['bgp/show'],
    'polled=True': ['topology/show'],
    'prefix=10.0.0.101/32': ['route/show'],
    'prefixlen=24': ['route/show'],
    'priVtepIp=10.0.0.112': ['evpnVni/show'],
    'protocol=bgp%20ospf': ['route/show'],
    'service=device': ['sqPoller'],
    'remoteVtepIp=10.0.0.101': ['mac/show'],
    'state=up': ['interface/show'],
    'state=down': ['interface/show'],
    'state=notConnected': ['interface/show'],
    'state=Established': ['bgp/show'],
    'state=NotEstd': ['bgp/show'],
    'state=all': ['ospf/show'],
    'state=full': ['ospf/show'],
    'state=other': ['ospf/show'],
    'state=passive': ['ospf/show'],
    'type=ethernet': ['interface/show'],
    'usedPercent=8': ['fs/show'],
    'vlan=13': ['mac/show', 'vlan/show'],
    'vni=13': ['evpnVni/show'],
    'vni=13%2024': ['evpnVni/show'],
    'column=prefixlen': ['route/unique'],
    'vrf=default': ['address/show', 'bgp/show', 'bgp/assert',
                    'ospf/assert', 'ospf/show',
                    'route/show', 'route/summarize', 'topology/show',
                    ],
    'status=pass': ['bgp/assert', 'evpnVni/assert', 'interfaces/assert',
                    'ospf/assert', 'sqpoller/show'],
    'status=fail': ['bgp/assert', 'evpnVni/assert', 'interfaces/assert',
                    'ospf/assert'],
    'status=all': ['bgp/assert', 'evpnVni/assert', 'interfaces/assert',
                   'ospf/assert'],
    'vlanName=vlan13': ['vlan/show'],
    'state=active': ['vlan/show'],
}

GOOD_VERB_FILTERS = {
    'unique': ['columns=namespace'],
}

GOOD_SERVICE_VERB_FILTER = {
    'path/show': ['dest=172.16.2.104&src=172.16.1.101&namespace=ospf-ibgp'],
    'path/summarize': ['dest=172.16.2.104&src=172.16.1.101&namespace=ospf-ibgp'],
    'route/lpm': ['address=10.0.0.11', 'address=10.0.0.11&view=all'],

}

GOOD_FILTER_EMPTY_RESULT_FILTER = [
    'sqpoller/show?status=fail',
    'ospf/assert?status=fail',
    'evpnVni/assert?status=fail',
    'interface/show?state=notConnected',
]

# these service/verb pairs should return errors
BAD_VERBS = {'address/assert': 422, 'address/lpm': 422,
             'arpnd/assert': 422, 'arpnd/lpm': 422,
             'bgp/lpm': 422,
             'device/assert': 422, 'device/lpm': 422,
             'devconfig/assert': 422, 'devconfig/lpm': 422,
             'evpnVni/lpm': 422,
             'fs/assert': 422, 'fs/lpm': 422,
             'interface/lpm': 422,
             'lldp/assert': 422, 'lldp/lpm': 422,
             'mac/assert': 422, 'mac/lpm': 422,
             'mlag/assert': 422, 'mlag/lpm': 422,
             'ospf/lpm': 422,
             'path/assert': 422, 'path/unique': 422,
             'path/lpm': 422,
             'sqpoller/assert': 422, 'sqpoller/lpm': 422,
             'route/assert': 422,
             'topology/assert': 422,
             'topology/lpm': 422,
             'topology/unique': 422,
             'vlan/assert': 422, 'vlan/lpm': 422,
             }

# these are always bad filters for these verbs no matter the service
BAD_VERB_FILTERS = {'assert?address=10.0.0.1': 405,
                    'summarize?columns=namespace': 405,
                    'unique?': 405,
                    'unique?namespace=ospf-ibgp': 405,
                    'unique?view=latest': 405,
                    'assert?query_str=hostname%20==%20"leaf01"': 405,
                    'assert?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 405,
                    }

# these service/verb/filter tuples should return errors
#  because they are invalid filters for the service/verb combos
BAD_FILTERS = {
    'address/summarize?address=10.0.0.11': 405,
    'address/summarize?address=10.0.0.11&view=all': 405,
    'address/summarize?ipvers=v4': 405,
    'address/summarize?vrf=default': 405,
    'address/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'address/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'arpnd/summarize?macaddr=44:39:39:ff:40:95': 405,
    'arpnd/summarize?macaddr=44:39:39:FF:40:95': 405,
    'arpnd/summarize?macaddr=4439.39FF.4095': 405,
    'arpnd/summarize?macaddr=4439.39ff.4095': 405,
    'arpnd/summarize?macaddr=44:39:39:ff:00:13%2044:39:39:ff:00:24': 405,
    'arpnd/summarize?ipAddress=10.0.0.11': 405,
    'arpnd/summarize?oif=eth1.4': 405,
    'arpnd/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'arpnd/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'bgp/show?state=pass': 405,
    'bgp/show?status=pass': 405,
    'bgp/show?status=fail': 405,
    'bgp/show?status=all': 405,
    'bgp/show?status=whatever': 405,
    'bgp/show?state=active': 405,
    'bgp/show?state=up': 405,
    'bgp/show?state=down': 405,
    'bgp/show?state=notConnected': 405,
    'bgp/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'bgp/assert?peer=eth1.2': 405,
    'bgp/assert?state=pass': 405,
    'bgp/assert?state=whatever': 405,
    'bgp/assert?state=active': 405,
    'bgp/assert?state=up': 405,
    'bgp/assert?state=down': 405,
    'bgp/assert?state=notConnected': 405,
    'bgp/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'bgp/summarize?peer=eth1.2': 405,
    'bgp/summarize?state=pass': 405,
    'bgp/summarize?state=Established': 405,
    'bgp/summarize?state=NotEstd': 405,
    'bgp/summarize?state=active': 405,
    'bgp/summarize?vrf=default': 405,
    'bgp/summarize?status=pass': 405,
    'bgp/summarize?status=fail': 405,
    'bgp/summarize?status=all': 405,
    'bgp/summarize?status=whatever': 405,
    'bgp/summarize?state=up': 405,
    'bgp/summarize?state=down': 405,
    'bgp/summarize?state=notConnected': 405,
    'device/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'device/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'devconfig/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'devconfig/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'evpnVni/show?status=pass': 405,
    'evpnVni/show?status=fail': 405,
    'evpnVni/show?status=all': 405,
    'evpnVni/show?status=whatever': 405,
    'evpnVni/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'evpnVni/assert?vni=13': 405,
    'evpnVni/assert?vni=13%2024': 405,
    'evpnVni/assert?priVtepIp=10.0.0.112': 405,
    'evpnVni/summarize?vni=13': 405,
    'evpnVni/summarize?vni=13%2024': 405,
    'evpnVni/summarize?status=pass': 405,
    'evpnVni/summarize?status=fail': 405,
    'evpnVni/summarize?status=all': 405,
    'evpnVni/summarize?status=whatever': 405,
    'evpnVni/summarize?priVtepIp=10.0.0.112': 405,
    'evpnVni/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'fs/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'fs/summarize?usedPercent=8': 405,
    'fs/summarize?mountPoint=/': 405,
    'fs/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'interface/assert?state=active': 405,
    'interface/assert?state=up': 405,
    'interface/assert?state=down': 405,
    'interface/assert?state=notConnected': 405,
    'interface/show?state=pass': 405,
    'interface/show?status=pass': 405,
    'interface/show?status=fail': 405,
    'interface/show?state=active': 405,
    'interface/show?status=all': 405,
    'interface/show?status=whatever': 405,
    'interface/assert?type=ethernet': 405,
    'interface/assert?state=pass': 405,
    'interface/summarize?ifname=swp1': 405,
    'interface/summarize?state=pass': 405,
    'interface/summarize?type=ethernet': 405,
    'interface/summarize?status=pass': 405,
    'interface/summarize?status=fail': 405,
    'interface/summarize?status=all': 405,
    'interface/summarize?status=whatever': 405,
    'interface/summarize?state=active': 405,
    'interface/summarize?state=up': 405,
    'interface/summarize?state=down': 405,
    'interface/summarize?state=notConnected': 405,
    'lldp/summarize?ifname=swp1': 405,
    'lldp/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'lldp/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'mac/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'mac/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'mac/summarize?bd=': 405,
    'mac/summarize?macaddr=44:39:39:ff:40:95': 405,
    'mac/summarize?macaddr=44:39:39:FF:40:95': 405,
    'mac/summarize?macaddr=4439.39FF.4095': 405,
    'mac/summarize?macaddr=4439.39ff.4095': 405,
    'mac/summarize?macaddr=44:39:39:ff:00:13%2044:39:39:ff:00:24': 405,
    'mac/summarize?localOnly=True': 405,
    'mac/summarize?remoteVtepIp=10.0.0.101': 405,
    'mac/summarize?vlan=13': 405,
    'mlag/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'mlag/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'ospf/show?state=pass': 405,
    'ospf/show?state=up': 405,
    'ospf/show?state=down': 405,
    'ospf/show?state=notConnected': 405,
    'ospf/show?status=pass': 405,
    'ospf/show?status=fail': 405,
    'ospf/show?status=all': 405,
    'ospf/show?state=active': 405,
    'ospf/show?status=whatever': 405,
    'ospf/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'ospf/assert?hostname=leaf01': 405,
    'ospf/assert?hostname=leaf01%20spine01': 405,
    'ospf/assert?state=pass': 405,
    'ospf/assert?state=active': 405,
    'ospf/assert?ifname=swp1': 405,
    'ospf/assert?state=notConnected': 405,
    'ospf/assert?state=up': 405,
    'ospf/assert?state=down': 405,
    'ospf/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'ospf/summarize?ifname=swp1': 405,
    'ospf/summarize?state=pass': 405,
    'ospf/summarize?vrf=default': 405,
    'ospf/summarize?state=up': 405,
    'ospf/summarize?state=down': 405,
    'ospf/summarize?state=notConnected': 405,
    'ospf/summarize?status=pass': 405,
    'ospf/summarize?status=fail': 405,
    'ospf/summarize?status=all': 405,
    'ospf/summarize?status=whatever': 405,
    'ospf/summarize?state=active': 405,
    'ospf/show?status=all': 405,
    'path/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 404,
    'path/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 404,
    'path/unique?columns=namespace': 404,
    'route/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'route/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'route/lpm?': 404,
    'route/lpm?columns=namespace': 404,
    'route/lpm?hostname=leaf01': 404,
    'route/lpm?namespace=ospf-ibgp': 404,
    'route/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'route/summarize?address=10.0.0.11': 405,
    'route/summarize?address=10.0.0.11&view=all': 405,
    'route/summarize?ipvers=v4': 405,
    'route/summarize?prefix=10.0.0.101/32': 405,
    'route/summarize?prefixlen=24': 405,
    'route/summarize?protocol=bgp': 405,
    'route/show?ipvers=v4': 405,
    'route/lpm?view=latest': 404,
    'sqpoller/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'sqpoller/show?status=whatever': 405,
    'sqpoller/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'sqpoller/summarize?status=pass': 405,
    'sqpoller/summarize?status=fail': 405,
    'sqpoller/summarize?status=all': 405,
    'sqpoller/summarize?status=whatever': 405,
    'sqpoller/summarize?service=device': 405,
    'topology/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'topology/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'topology/summarize?polled=True': 405,
    'topology/summarize?ifname=swp1': 405,
    'vlan/show?state=pass': 405,
    'vlan/show?state=up': 405,
    'vlan/show?state=down': 405,
    'vlan/show?state=notConnected': 405,
    'vlan/show?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'vlan/summarize?query_str=hostname=="leaf01"%20and%201000<mtu<2000': 500,
    'vlan/summarize?vlan=13': 405,
    'vlan/summarize?state=pass': 405,
    'vlan/summarize?state=active': 405,
    'vlan/summarize?vlanName=vlan13': 405,
    'vlan/summarize?state=up': 405,
    'vlan/summarize?state=down': 405,
    'vlan/summarize?state=notConnected': 405,
}


def get(endpoint, service, verb, args):
    api_key = get_configured_api_key()
    #url = f"{endpoint}/{service}/{verb}?access_token={api_key}&{args}"
    url = f"{endpoint}/{service}/{verb}?{args}"

    client = TestClient(app)
    response = client.get(url, headers={API_KEY_NAME: api_key})

    c_v = f"{service}/{verb}"
    c_v_f = f"{c_v}?{args}"
    v_f = f"{verb}?{args}"
    if response.status_code != 200:
        if c_v in BAD_VERBS:
            assert BAD_VERBS[c_v] == response.status_code, response.content.decode(
                'utf8')
        elif c_v_f in BAD_FILTERS:
            assert BAD_FILTERS[c_v_f] == response.status_code, response.content.decode(
                'utf8')
        elif v_f in BAD_VERB_FILTERS:
            assert BAD_VERB_FILTERS[v_f] == response.status_code, response.content.decode(
                'utf8')
        # elif args in GOOD_FILTERS_FOR_SERVICE_VERB:

        #      assert c_v not in GOOD_FILTERS_FOR_SERVICE_VERB[args]
        #      assert response.status_code == 405 or response.status_code == 404
        elif verb in GOOD_VERB_FILTERS:
            assert args not in GOOD_VERB_FILTERS[verb]
        elif c_v in GOOD_SERVICE_VERB_FILTER:
            assert args not in GOOD_SERVICE_VERB_FILTER[c_v]
        else:
            print(
                f" RESPONSE {response.status_code} {response.content.decode('utf8')}")
            response.raise_for_status()
    else:  # you've gotten a 200, need to make sure that's what we expect
        assert c_v not in BAD_VERBS
        assert c_v_f not in BAD_FILTERS
        assert v_f not in BAD_VERB_FILTERS
        if verb in GOOD_VERB_FILTERS:
            assert args in GOOD_VERB_FILTERS[verb]
        if c_v in GOOD_SERVICE_VERB_FILTER:
            assert args in GOOD_SERVICE_VERB_FILTER[c_v]

        # make sure it's not empty when it shouldn't be
        if c_v_f not in GOOD_FILTER_EMPTY_RESULT_FILTER:
            assert len(response.content.decode('utf8')) > 10
        else:
            assert len(response.content.decode('utf8')) == 2
    return response.status_code


@pytest.mark.parametrize("service, verb, arg", [
    (cmd, verb, filter) for cmd in cli_commands
    for verb in VERBS for filter in FILTERS
])
def test_rest_services(start_server, service, verb, arg):
    get(ENDPOINT, service, verb, arg)


@pytest.fixture(scope="session")
def start_server():

    from suzieq.restServer.query import app_init

    cfgfile = create_dummy_config_file(
        datadir='./tests/data/multidc/parquet-out')
    app_init(cfgfile)
    yield
    os.remove(cfgfile)
