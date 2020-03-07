""" Hisense Television Integration. """
from hisensetv import HisenseTv
#from homeassistant.components.switch import SwitchDevice
from homeassistant.components.switch import DOMAIN, SwitchDevice
from homeassistant.core import callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.typing import HomeAssistantType
from typing import Callable
from typing import Optional
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.entity_component import EntityComponent
import logging
import platform
import subprocess as sp
import socket
import voluptuous as vol
import wakeonlan

from . import HisenseTvDevice

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
)

from . import const
from .const import (
    CONF_MODEL,
    DEFAULT_PING_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

def setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    add_entities: Callable,
    discovery_info: Optional[dict] = None,
):
    """Setup Hisense TV on/off as switch."""
    broadcast_address = config.get(CONF_BROADCAST_ADDRESS)
    host = config.get(CONF_HOST)
    mac = config.get(CONF_MAC)
    model = config.get(CONF_MODEL)
    name = config.get(CONF_NAME)

    add_entities(
        [
           HisenseTvSwitch(
                host=host,
                mac=mac,
                model=model,
                name=name,
                broadcast_address=broadcast_address,
           )
        ],
        True,
    )


class HisenseTvSwitch(HisenseTvDevice, SwitchDevice):
    """Representation of a HiSense TV as Switch."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str):
        """Initialize the switch"""
        HisenseTvDevice.__init__(self, host, mac, model, name, broadcast_address)
        self._name = name
        self._state = True

    def update(self):
        """Check if device is on and update the state."""
        if platform.system().lower() == "windows":
            ping_cmd = [
                "ping",
                "-n",
                "1",
                "-w",
                str(DEFAULT_PING_TIMEOUT * 1000),
                str(self._host),
            ]
        else:
            ping_cmd = [
                "ping",
                "-c",
                "1",
                "-W",
                str(DEFAULT_PING_TIMEOUT),
                str(self._host),
            ]

        status = sp.call(ping_cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        self._state = not bool(status)

