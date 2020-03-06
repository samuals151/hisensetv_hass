""" Hisense Television Integration. """
from hisensetv import HisenseTv

from datetime import timedelta
from typing import Sequence, TypeVar, Union

from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import (
    make_entity_service_schema,
)

#from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.loader import bind_hass

import logging
import platform
import subprocess as sp
import socket
import voluptuous as vol
import wakeonlan

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_HOST, 
    CONF_MAC,
    CONF_NAME,
)

from . import const
from .const import (
    CONF_MODEL,
    DATA_TV_STATUS,
    DEFAULT_COMMAND_PARAM,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DOMAIN,
    ICON_TV,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)

# Not sure why this is needed
ENTITY_ID_FORMAT = DOMAIN + ".{}"

HISENSETV_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: HISENSETV_CONFIG_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

HISENSETV_COMPONENTS = [
#    "binary_sensor",
    "media_player",
#    "sensor",
    "switch",
]


async def async_setup(hass: HomeAssistantType, base_config: ConfigType) -> bool:
    """Set up a hisense tv."""

    _LOGGER.info("Setting up %s", DOMAIN)

    component = hass.data[DOMAIN] = EntityComponent(_LOGGER, DOMAIN, hass, SCAN_INTERVAL)

    await component.async_setup(base_config)

    return True

async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)

class HisenseTvDevice(ToggleEntity):
    """Representation of a generic HiSense TV entity."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str):
        self._name = name
        self._host = host
        self._mac = mac
        self._model = model
        self._broadcast_address = broadcast_address
        self._is_on = False
        self._icon = ICON_TV
        self._state = False

    def turn_on(self, **kwargs):
        self._state = True
        if self._broadcast_address:
            wakeonlan.send_magic_packet(
                self._mac, ip_address=self._broadcast_address
            )
        else:
            wakeonlan.send_magic_packet(self._mac)

    def turn_off(self, **kwargs):
        try:
            self._state = False
            _LOGGER.debug("Sending Power Off to HisenseTV at %s", self._host)
            with HisenseTv(self._host) as tv:
                tv.send_key_power()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
                _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
                raise

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return 0

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon
