"""Add support for the Hisense TVs."""
from hisensetv import HisenseTv

import logging
import platform
import subprocess as sp
import socket
import voluptuous as vol

from homeassistant.core import ServiceCall, callback
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerDevice
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType

from homeassistant.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    CONF_BROADCAST_ADDRESS,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    STATE_OFF,
    STATE_ON
)

from . import HisenseTvDevice
from . import const
from .const import (
    COMMANDS,
    CONF_MODEL,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_MAX_VOLUME,
    DEFAULT_MIN_VOLUME,
    DOMAIN,
    DOMAIN_DATA,
    SERVICE_SEND_COMMAND,
)

_LOGGER = logging.getLogger(__name__)


SUPPORT_HISENSE_TV = (
   SUPPORT_SELECT_SOURCE
   | SUPPORT_TURN_ON 
   | SUPPORT_TURN_OFF
   | SUPPORT_VOLUME_SET
   | SUPPORT_VOLUME_STEP 
)


SCHEMA_SEND_COMMAND = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_COMMAND): vol.In(list(COMMANDS)),
    }
)
 
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)

#async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Hisense TV platform."""

    broadcast_address = config.get(CONF_BROADCAST_ADDRESS)
    host = config.get(CONF_HOST)
    mac = config.get(CONF_MAC)
    model = config.get(CONF_MODEL)
    name = config.get(CONF_NAME)

#    async_add_entities(
    add_entities(
        [
           HisenseTvMediaPlayer(
                name=name,
                host=host,
                mac=mac,
                model=model,
                broadcast_address=broadcast_address,
           )
        ],
        True,
    )

    def service_handle(service_call: ServiceCall):
        """Handle for services."""
        _LOGGER.debug("service_handle, service=%s", service_call.service)
        if service_call.service == SERVICE_SEND_COMMAND:
           entity_ids = service_call.data[ATTR_ENTITY_ID]
           command = service_call.data[ATTR_COMMAND]
           _LOGGER.debug("service_handle, command=%s entity(s)=%s", command, entity_ids)
           entity_found = False
           for device in hass.data[DOMAIN_DATA].devices:
              if device.entity_id in entity_ids:
                 entity_found = True
                 device.send_command(command)
           if not entity_found:
              _LOGGER.error("Invalid entity provided in service: %s entity: %s", service_call.service, entity_ids)
        else:
           """Service has not been defined"""
           _LOGGER.error("Service definition not created, service=%s", service_call.service)


#    hass.services.register(
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        service_handle,
        schema=SCHEMA_SEND_COMMAND,
    )

    _LOGGER.debug("setup_platform, SUCCESS, config=%s", config)



#async def async_setup_entry(hass, config_entry, async_add_entities):
def setup_entry(hass, config_entry, add_entities):
    """Set up HisenseTV from a config entry."""

    config = hass.data[DOMAIN].get("media_player", {})
    _LOGGER.debug("Reached setup_entry, config=%s", config)



class HisenseTvMediaPlayer(HisenseTvDevice, MediaPlayerDevice):
    """Representation of a HiSense TV as Media Player."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str):
        HisenseTvDevice.__init__(self, host, mac, model, name, broadcast_address)
        self._name = name
        self._volume = None
        self._min_volume = DEFAULT_MIN_VOLUME
        self._max_volume = DEFAULT_MAX_VOLUME
        self._source = None
        self._source_list = []
        self._state = STATE_OFF
        self._source_map_dict = {}

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_HISENSE_TV

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume is not None:
            return self._volume
        return None

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    def _refresh_sources(self):
        """Refresh source list"""
        try:
            with HisenseTv(self._host) as tv:
               source_list = tv.get_sources()
            if source_list is not None:
               self._source_list = []
               self._source_dict_map = {}
               for source in source_list: 
                  id =  source.get("sourceid")
                  # Displayname and sourename appear to always be the same for me
                  #name =  source.get("displayname")
                  name =  source.get("sourcename")
                  self._source_map_dict[name] = id
                  self._source_list.append(name)
                  #_LOGGER.debug("_refresh_sources - Name='%s'", name)
 
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def _refresh_volume(self):
        """Refresh volume information."""
        try:
            with HisenseTv(self._host) as tv:
               volume_info = tv.get_volume()
            if volume_info is not None:
               volume_value =  volume_info.get("volume_value") 
               self._volume = (volume_value / self._max_volume)
               #_LOGGER.debug("_refresh_volume - Volume='%s'", volume_value)

        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

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
                  tv.send_key_power()
               elif command_value == 'up':
                  tv.send_key_up()
               elif command_value == 'down':
                  tv.send_key_down()
               elif command_value == 'left':
                  tv.send_key_left()
               elif command_value == 'right':
                  tv.send_key_right()
               elif command_value == 'menu':
                  tv.send_key_menu()
               elif command_value == 'back':
                  tv.send_key_back()
               elif command_value == 'exit':
                  tv.send_key_exit()
               elif command_value == 'ok':
                  tv.send_key_ok()
               else:
                  _LOGGER.error("Invalid HisenseTV send_command input parmater: %s", command_value)
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def select_source(self, source):
        """Select input source."""
        try:
            source_int = self._source_map_dict.get(source)
            _LOGGER.debug("select_source - SourceInt='%s'", source_int)
            with HisenseTv(self._host) as tv:
               tv.set_source(source_int,source)
            self._source = source
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def set_volume_level(self, volume: float):
        """Set volume"""
        try:
            with HisenseTv(self._host) as tv:
               volume_int = int( volume * self._max_volume )
               tv.set_volume(volume_int)
               _LOGGER.debug("set_volume_level - Volume='%4.3f'", volume)
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def volume_up(self):
        """Increase volume by one."""
        try:
            with HisenseTv(self._host) as tv:
               tv.send_key_volume_up()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def volume_down(self):
        """Decrease volume by one."""
        try:
            with HisenseTv(self._host) as tv:
               tv.send_key_volume_down()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               raise

    def update(self):
        """ Retrieve the latest data."""
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

              # refresh volume
              self._refresh_volume()

              # refresh source list
              self._refresh_sources()

        except Exception as exception_instance:
            _LOGGER.error(exception_instance)
            self._state = STATE_OFF

