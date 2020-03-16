""" Hisense Television Integration as switch device. """
from datetime import timedelta
from hisensetv import HisenseTv
from homeassistant.components.switch import PLATFORM_SCHEMA, DOMAIN, SwitchDevice
from homeassistant.core import callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.typing import HomeAssistantType
from typing import Callable
from typing import Optional
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.core import ServiceCall

import logging
import platform
import subprocess as sp
import socket
import voluptuous as vol
import wakeonlan

from . import HisenseTvDevice

from homeassistant.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    CONF_BROADCAST_ADDRESS,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    STATE_OFF,
    STATE_ON,
)

from . import const
from .const import (
    COMMANDS,
    CONF_MODEL,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_PING_TIMEOUT,
    DOMAIN,
    DOMAIN_DATA,
    SERVICE_SEND_COMMAND,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }
)

SCHEMA_SEND_COMMAND = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_COMMAND): vol.In(list(COMMANDS)),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Hisense TV platform."""
    if DOMAIN_DATA not in hass.data:
        hass.data[DOMAIN_DATA] = []

    """Setup Hisense TV on/off as switch."""
    broadcast_address = config.get(CONF_BROADCAST_ADDRESS)
    host = config.get(CONF_HOST)
    mac = config.get(CONF_MAC)
    model = config.get(CONF_MODEL)
    name = config.get(CONF_NAME)
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()

    async_add_entities(
        [
           HisenseTvSwitch(
                host=host,
                mac=mac,
                model=model,
                name=name,
                broadcast_address=broadcast_address,
                scan_interval=scan_interval,
           )
        ],
        update_before_add=True,
    )

    async def async_service_handler(service_call: ServiceCall):
        """Handle for services."""
        _LOGGER.debug("service_handle, service=%s", service_call.service)
        if service_call.service == SERVICE_SEND_COMMAND:
           entity_ids = service_call.data[ATTR_ENTITY_ID]
           command = service_call.data[ATTR_COMMAND]
           _LOGGER.debug("service_handle, command=%s entity(s)=%s", command, entity_ids)
           for device in hass.data[DOMAIN_DATA].devices:
              if device.entity_id in entity_ids:
                 device.send_command(command)
                 device.async_schedule_update_ha_state(True)
           if not entity_found:
              _LOGGER.error("Invalid entity provided in service: %s entity: %s", service_call.service, entity_ids)
        else:
           """Service has not been defined"""
           _LOGGER.error("Service definition not created, service=%s", service_call.service)


    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        async_service_handler,
        schema=SCHEMA_SEND_COMMAND,
    )

    _LOGGER.debug("setup_platform, SUCCESS, config=%s", config)

    return True

class HisenseTvSwitch(HisenseTvDevice, SwitchDevice):
    """Representation of a HiSense TV as Switch."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str, scan_interval: int):
        """Initialize the switch"""
        HisenseTvDevice.__init__(self, host, mac, model, name, broadcast_address, scan_interval)


    def _update(self):
        """ Retrieve the latest data without interval enforcing."""
        _LOGGER.debug("_update - starting...")
        try:
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
           if bool(status):
              self._state = STATE_OFF
           else:
              self._state = STATE_ON

        except Exception as exception_instance:
            _LOGGER.error(exception_instance)
            self._state = STATE_OFF


