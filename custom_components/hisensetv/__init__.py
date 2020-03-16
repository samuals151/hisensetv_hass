""" Hisense Television Integration. """
from hisensetv import HisenseTv

from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv

from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.loader import bind_hass

import logging
import platform
import subprocess as sp
import socket
import time
import voluptuous as vol
import wakeonlan
import sys

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_HOST, 
    CONF_MAC,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
)

from . import const
from .const import (
    CONF_MODEL,
    DATA_TV_STATUS,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DOMAIN,
    DOMAIN_DATA,
    ICON_TV,
    PING_RESPONSE_WAIT_SEC,
)

_LOGGER = logging.getLogger(__name__)

#SCAN_INTERVAL = timedelta(seconds=60)


class HisenseData:
    """Init Data Class."""

    def __init__(self):
        """Init Class."""
        self.devices = []


async def async_setup(hass: HomeAssistantType, base_config: ConfigType) -> bool:
#def setup(hass: HomeAssistantType, base_config: ConfigType) -> bool:
    """Set up a hisense tv."""
    hass.data[DOMAIN_DATA] = HisenseData()
#    component = hass.data[DOMAIN] = EntityComponent(_LOGGER, DOMAIN, hass, SCAN_INTERVAL)
#    await component.async_setup(base_config)
    _LOGGER.info("Setting up %s", DOMAIN)
    return True


#class HisenseTvDevice(Entity):
class HisenseTvDevice(ToggleEntity):
    """Representation of a generic HiSense TV entity."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str, scan_interval: int):
        self._name = name
        self._host = host
        self._mac = mac
        self._model = model
        self._broadcast_address = broadcast_address
        self._icon = ICON_TV
        self._state = STATE_OFF
        self._scan_interval = scan_interval
        self._updatets = time.monotonic()

    def turn_on(self, **kwargs):
        self._state = STATE_ON
        if self._broadcast_address:
            wakeonlan.send_magic_packet(
               self._mac, ip_address=self._broadcast_address
            )
        else:
            wakeonlan.send_magic_packet(self._mac)
        # the sleep is needed to allow for ping response time
        time.sleep(PING_RESPONSE_WAIT_SEC)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        try:
            self._state = STATE_OFF
            _LOGGER.debug("Sending Power Off to HisenseTV at %s", self._host)
            with HisenseTv(self._host) as tv:
               tv.send_key_power()
            time.sleep(PING_RESPONSE_WAIT_SEC)
            self.schedule_update_ha_state()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            raise

    def update(self):
        """ Retrieve the latest data, but only after interval."""
        # Only update every update_interval
        if (time.monotonic() - self._updatets) >= self._scan_interval:
           #_LOGGER.debug("Updating...")
           self._updatets = time.monotonic()
           self._update()
        else:
           _LOGGER.debug("Skipping update...")

    async def async_added_to_hass(self):
        """Maintain list of devices."""
        self.hass.data[DOMAIN_DATA].devices.append(self)

    async def async_will_remove_from_hass(self):
        """Remove Entity from Hass."""
        self.hass.data[DOMAIN_DATA].devices.remove(self)

    def send_command(self, command_value: str):
        """Send command to TV."""
        try:
            with HisenseTv(self._host) as tv:
               _LOGGER.debug("send_command - Command='%s'", command_value)
               if command_value == 'power':
                  if not tv.send_key_power():
                     _LOGGER.error("ERROR - send_key - Command 'power' failure.")
               elif command_value == 'up':
                  if not tv.send_key_up():
                     _LOGGER.error("ERROR - send_key - Command 'up' failure.")
               elif command_value == 'down':
                  if not tv.send_key_down():
                     _LOGGER.error("ERROR - send_key - Command 'down' failure.")
               elif command_value == 'left':
                  if not tv.send_key_left():
                     _LOGGER.error("ERROR - send_key - Command 'left' failure.")
               elif command_value == 'right':
                  if not tv.send_key_right():
                     _LOGGER.error("ERROR - send_key - Command 'right' failure.")
               elif command_value == 'menu':
                  if not tv.send_key_menu():
                     _LOGGER.error("ERROR - send_key - Command 'menu' failure.")
               elif command_value == 'back':
                  if not tv.send_key_back():
                     _LOGGER.error("ERROR - send_key - Command 'back' failure.")
               elif command_value == 'exit':
                  if not tv.send_key_exit():
                     _LOGGER.error("ERROR - send_key - Command 'exit' failure.")
               elif command_value == 'ok':
                  if not tv.send_key_ok():
                     _LOGGER.error("ERROR - send_key - Command 'ok' failure.")
               elif command_value == 'volume_up':
                  if not tv.send_key_volume_up():
                     _LOGGER.error("ERROR - send_key - Command 'volume up' failure.")
               elif command_value == 'volume_down':
                  if not tv.send_key_volume_down():
                     _LOGGER.error("ERROR - send_key - Command 'volume down' failure.")
               elif command_value == 'forwards':
                  if not tv.send_key_forwards():
                     _LOGGER.error("ERROR - send_key - Command 'forwards' failure.")
               elif command_value == 'backs':
                  if not tv.send_key_backs():
                     _LOGGER.error("ERROR - send_key - Command 'backs' failure.")
               elif command_value == 'stop':
                  if not tv.send_key_stop():
                     _LOGGER.error("ERROR - send_key - Command 'stop' failure.")
               elif command_value == 'play':
                  if not tv.send_key_play():
                     _LOGGER.error("ERROR - send_key - Command 'play' failure.")
               elif command_value == 'pause':
                  if not tv.send_key_pause():
                     _LOGGER.error("ERROR - send_key - Command 'pause' failure.")
               else:
                  _LOGGER.error("Invalid HisenseTV send_command input parmater: %s", command_value)
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
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
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

