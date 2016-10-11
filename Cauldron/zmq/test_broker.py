# -*- coding: utf-8 -*-
"""Tests for the ZMQ Broker"""

import pytest
import six
from .broker import ZMQBroker
from .protocol import ZMQCauldronMessage
from ..conftest import fail_if_not_teardown, available_backends

import time

pytestmark = pytest.mark.skipif("zmq" not in available_backends, reason="requires zmq")

@pytest.fixture
def timeout():
    """Length of timeouts."""
    return 0.01

@pytest.fixture
def dispatcher_name(request):
    """The name of dispatcher A"""
    return "dispatcher_name"
    
@pytest.fixture
def dispatcher_alt_name(request):
    """The name of dispatcher A"""
    return "dispatcher_alt_name"
    
@pytest.fixture
def address():
    """A random broker address."""
    return "inproc://broker"

@pytest.fixture
def pub_address():
    """A broker publication address."""
    return "inproc://publish"

@pytest.fixture
def sub_address():
    """A broker subscription address."""
    return "inproc://subscribe"

@pytest.fixture
def broker(request, address, pub_address, sub_address):
    """A broker object."""
    b = ZMQBroker("Test-Broker", address, pub_address, sub_address, sub_address)
    b.prepare()
    request.addfinalizer(b.close)
    return b
    
@pytest.fixture
def broker_quick_expire(request, address, pub_address, sub_address, timeout):
    """docstring for broker_quick_expire"""
    b = ZMQBroker("Test-Broker", address, pub_address, sub_address, sub_address, timeout=timeout)
    b.prepare()
    request.addfinalizer(b.close)
    return b
    
def socket(address, identity):
    """docstring for socket"""
    import zmq
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REQ)
    socket.IDENTITY = six.text_type(identity).encode('utf-8')
    socket.connect(address)
    return socket

@pytest.fixture
def dsocket(address, dispatcher_name):
    """The REQ socket to talk to the broker."""
    return socket(address, dispatcher_name)

@pytest.fixture
def dasocket(address, dispatcher_alt_name):
    return socket(address, dispatcher_alt_name)

@pytest.fixture
def csocket(address):
    """Client socket address."""
    return socket(address, "client")
    
@pytest.fixture
def message(servicename, dispatcher_name):
    """docstring for message"""
    return ZMQCauldronMessage(command="", service=servicename, direction="CDQ")
    
@pytest.fixture
def dispatcher_alt(broker, dasocket, servicename, dispatcher_alt_name, message, timeout):
    """docstring for dispatcher_alt"""
    dispatcher(broker, dasocket, servicename, dispatcher_alt_name, message, timeout)
    
@pytest.fixture
def dispatcher(broker, dsocket, servicename, dispatcher_name, message, timeout):
    """Register a dispatcher with the broker."""
    welcome = message.copy()
    welcome.dispatcher = dispatcher_name
    welcome.direction = "DBQ"
    welcome.command = "welcome"
    dsocket.send_multipart(welcome.data)
    
    broker.respond()
    
    assert dsocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    assert response.payload == "confirmed"
    
    b_dispatcher = broker.services[servicename.upper()].dispatchers[dispatcher_name]
    assert b_dispatcher.active == 1
    
    welcome.command = "ready"
    welcome.dispatcher = dispatcher_name
    dsocket.send_multipart(welcome.data)
    
    broker.respond()
    assert dsocket.poll(timeout) == 0, "Messages were ready!"
    assert b_dispatcher.active == 0
    return dispatcher_name

def test_broker_register_dispatcher(broker, dsocket, servicename, dispatcher_name, message, timeout):
    """Test registering a dispatcher."""
    dispatcher(broker, dsocket, servicename, dispatcher_name, message, timeout)
    
def test_broker_register_two_dispatchers(broker, dsocket, dasocket, servicename, dispatcher_name, dispatcher_alt_name, message, timeout):
    """Test registering two dispatchers."""
    dispatcher(broker, dsocket, servicename, dispatcher_name, message, timeout)
    dispatcher(broker, dasocket, servicename, dispatcher_alt_name, message, timeout)
    assert len(broker.services[servicename.upper()].dispatchers) == 2
    
def test_broker_check(address, pub_address, sub_address, waittime):
    """Test broker check."""
    assert not ZMQBroker.check(address=address, timeout=waittime)
    broker = ZMQBroker("Test-Broker", address, pub_address, sub_address, sub_address)
    broker.start()
    broker.running.wait()
    try:
        assert broker.check(address=address, timeout=waittime), "Broker wasn't alive!"
    finally:
        broker.stop()
        
def test_broker_run_and_stop(address, pub_address, sub_address, waittime):
    """Test broker run and stop."""
    broker = ZMQBroker("Test-Broker", address, pub_address, sub_address, sub_address)
    broker.start()
    broker.running.wait(timeout=waittime)
    broker.stop()
    
def test_broker_register_unknown_command(broker, dsocket, message, timeout, dispatcher_name):
    """Send a bogus command."""
    welcome = message.copy()
    welcome.direction = "DBQ"
    welcome.dispatcher = dispatcher_name
    welcome.command = "junk"
    dsocket.send_multipart(welcome.data)
    
    broker.respond()
    
    assert dsocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    assert response.payload == "unknown command"
    assert response.direction == "DBE"
    
def test_client_broker_query(broker, csocket, pub_address, sub_address, message, timeout):
    """Test a client asking for the broker publication address."""
    lookup = message.copy()
    lookup.direction = "CBQ"
    lookup.command = "lookup"
    
    csocket.send_multipart(lookup.data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(csocket.recv_multipart())
    
    assert response.payload == sub_address
    assert response.direction == "CBP"
    
def test_client_broker_query_error(broker, csocket, message, timeout):
    """Test a client broker query error."""
    error = message.copy()
    error.direction = "CBQ"
    error.command = "junk"
    
    csocket.send_multipart(error.data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(csocket.recv_multipart())
    
    assert response.payload == "unknown command"
    assert response.direction == "CBE"
    
def test_client_locate_success(broker, dispatcher, csocket, message, timeout):
    """Test client locate success."""
    lookup = message.copy()
    lookup.direction = "CBQ"
    lookup.command = "locate"
    
    csocket.send_multipart(lookup.data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert response.direction == "CBP"
    assert response.payload == "yes"
    
def test_client_locate_fail(broker, csocket, message, timeout):
    """Test client locate success."""
    lookup = message.copy()
    lookup.direction = "CBQ"
    lookup.command = "locate"
    
    csocket.send_multipart(lookup.data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No messages were ready!"
    response = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert response.direction == "CBP"
    assert response.payload == "no"
    
def test_client_dispatcher_messaging(broker, csocket, dsocket, dispatcher, message, timeout):
    """Test messages passed from client to dispatcher and back."""
    message = message.copy()
    message.direction = "CDQ"
    message.command = "test"
    message.payload = "data"
    message.dispatcher = dispatcher
    
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) != 0, "No dispatcher messages were ready"
    
    dmessage = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    assert dmessage.direction == message.direction
    assert dmessage.command == message.command
    assert dmessage.payload == message.payload
    assert dmessage.prefix[0] == csocket.IDENTITY
    dmessage.dispatcher = dispatcher
    
    dsocket.send_multipart(dmessage.response(dmessage.payload + "-response").data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    
    assert cmessage.direction == "CDP"
    assert cmessage.command == "test"
    assert cmessage.payload == "data-response"
    
def test_client_dispatcher_messaging_error(broker, csocket, dsocket, dispatcher, message, timeout):
    """Test messages passed from client to dispatcher and back."""
    message = message.copy()
    message.direction = "CDQ"
    message.command = "test"
    message.payload = "data"
    message.dispatcher = dispatcher
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) != 0, "No dispatcher messages were ready"
    
    dmessage = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    assert dmessage.direction == message.direction
    assert dmessage.command == message.command
    assert dmessage.payload == message.payload
    assert dmessage.prefix[0] == csocket.IDENTITY
    dmessage.dispatcher = dispatcher
    dsocket.send_multipart(dmessage.error_response(dmessage.payload + "-error").data)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    
    assert cmessage.direction == "CDE"
    assert cmessage.command == "test"
    assert cmessage.payload == "data-error"
    
def test_client_identify(broker, csocket, dsocket, dasocket, dispatcher, dispatcher_alt, message, timeout):
    """Test a client identify fan-out."""
    message = message.copy()
    message.direction = "CSQ"
    message.command = "test"
    message.payload = "data"
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) != 0, "No dispatcher messages were ready"
    assert dasocket.poll(timeout) != 0, "No dispatcher messages were ready"
    
    dmessage = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    damessage = ZMQCauldronMessage.parse(dasocket.recv_multipart())
    
    assert dmessage.direction == "SDQ"
    assert dmessage.command == "test"
    assert dmessage.payload == "data"
    dmessage.dispatcher = dispatcher
    
    assert damessage.direction == "SDQ"
    assert damessage.command == "test"
    assert damessage.payload == "data"
    damessage.dispatcher = dispatcher_alt
    
    dsocket.send_multipart(dmessage.response("reply"))
    dasocket.send_multipart(damessage.response("replya"))
    
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    assert dasocket.poll(timeout) == 0, "Dispatcher messages were ready"
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "Client messages were not ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    assert dasocket.poll(timeout) == 0, "Dispatcher messages were ready"
    
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "CSP"
    assert cmessage.command == "test"
    assert set(cmessage.payload.split(":")) == set(("reply", "replya"))
    
def test_client_identify_single_error(broker, csocket, dsocket, dasocket, dispatcher, dispatcher_alt, message, timeout):
    """Test a client identify with a single error."""
    message = message.copy()
    message.direction = "CSQ"
    message.command = "test"
    message.payload = "data"
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) != 0, "No dispatcher messages were ready"
    assert dasocket.poll(timeout) != 0, "No dispatcher messages were ready"
    
    dmessage = ZMQCauldronMessage.parse(dsocket.recv_multipart())
    damessage = ZMQCauldronMessage.parse(dasocket.recv_multipart())
    
    assert dmessage.direction == "SDQ"
    assert dmessage.command == "test"
    assert dmessage.payload == "data"
    dmessage.dispatcher = dispatcher
    
    assert damessage.direction == "SDQ"
    assert damessage.command == "test"
    assert damessage.payload == "data"
    damessage.dispatcher = dispatcher_alt
    
    dsocket.send_multipart(dmessage.response("reply"))
    dasocket.send_multipart(damessage.error_response("replya"))
    
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    assert dasocket.poll(timeout) == 0, "Dispatcher messages were ready"
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "Client messages were not ready"
    assert dsocket.poll(timeout) == 0, "Dispatcher messages were ready"
    assert dasocket.poll(timeout) == 0, "Dispatcher messages were ready"
    
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "CSP"
    assert cmessage.command == "test"
    assert set(cmessage.payload.split(":")) == set(["reply"])
    
def test_no_dispatcher_available(broker, csocket, dispatcher_name, servicename, message, timeout):
    """Test for when no dispatcher is available"""
    message = message.copy()
    message.direction = "CDQ"
    message.command = "test"
    message.payload = "data"
    message.dispatcher = dispatcher_name
    message.service = servicename
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "CDE"
    assert cmessage.command == "test"
    assert cmessage.payload == "No dispatcher is available for '{0}'".format(servicename)
    
def test_no_dispatcher_available(broker, csocket, dispatcher_name, servicename, message, timeout):
    """Test for when no dispatcher is available"""
    message = message.copy()
    message.direction = "CDQ"
    message.command = "test"
    message.payload = "data"
    message.dispatcher = dispatcher_name
    message.service = servicename
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "CDE"
    assert cmessage.command == "test"
    assert cmessage.payload == "Dispatcher '{0}' is not available for '{1}'".format(dispatcher_name, servicename)
    
def test_no_dispatcher_available_service_query(broker, csocket, dispatcher_name, servicename, message, timeout):
    """Test for when no dispatcher is available"""
    message = message.copy()
    message.direction = "CSQ"
    message.command = "test"
    message.payload = "data"
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "CSE"
    assert cmessage.command == "test"
    assert cmessage.payload == "No dispatchers for '{0}'".format(servicename)
    
def test_broker_alive_call(broker, csocket, dispatcher_name, servicename, message, timeout):
    """Test for when no dispatcher is available"""
    message = message.copy()
    message.direction = "UBQ"
    message.command = "check"
    message.payload = "data"
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    assert cmessage.direction == "UBP"
    assert cmessage.command == "check"
    assert cmessage.payload == "Broker Alive"
    
def test_dispatcher_expiration(broker_quick_expire, csocket, dsocket, servicename, dispatcher_name, message, timeout):
    """Test messages passed from client to dispatcher and back."""
    
    broker = broker_quick_expire
    dispatcher(broker, dsocket, servicename, dispatcher_name, message, timeout)
    
    message = message.copy()
    message.direction = "CDQ"
    message.command = "test"
    message.payload = "data"
    message.dispatcher = dispatcher_name
    
    csocket.send_multipart(message.data)
    broker.respond()
    assert csocket.poll(timeout) == 0, "Client messages were ready"
    assert dsocket.poll(timeout) != 0, "No dispatcher messages were ready"
    
    time.sleep(5 * timeout)
    
    broker.respond()
    assert csocket.poll(timeout) != 0, "No client messages were ready"
    
    assert dsocket.poll(timeout) != 0, "Dispatcher messages were ready"
    cmessage = ZMQCauldronMessage.parse(csocket.recv_multipart())
    
    assert cmessage.direction == "CDE"
    assert cmessage.command == "test"
    assert cmessage.payload == "Dispatcher Timed Out"
    