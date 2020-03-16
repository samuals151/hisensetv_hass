""" Hisense Television Integration as media_player device. """
from datetime import timedelta 
from hisensetv import HisenseTv

import logging
import platform
import socket
import subprocess as sp
import sys
import time
import wakeonlan
import voluptuous as vol

from homeassistant.core import ServiceCall
from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerDevice
from homeassistant.components.media_player.const import (
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK,
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
    CONF_SCAN_INTERVAL,
    STATE_OFF,
    STATE_ON
)

from . import HisenseTvDevice
from . import const
from .const import (
    COMMANDS,
    CONF_MODEL,
    CONF_PAUSE_RESUME,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_PAUSE_RESUME,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_MAX_VOLUME,
    DEFAULT_MIN_VOLUME,
    DOMAIN,
    DOMAIN_DATA,
    SERVICE_SEND_COMMAND,
    SERVICE_UPDATE_SOURCES,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)

SUPPORT_HISENSE_TV = (
   SUPPORT_NEXT_TRACK
   | SUPPORT_PAUSE
   | SUPPORT_PLAY
   | SUPPORT_PREVIOUS_TRACK
   | SUPPORT_SELECT_SOURCE
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

SCHEMA_UPDATE_SOURCES = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    }
)
 
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
        vol.Optional(CONF_PAUSE_RESUME, default=DEFAULT_PAUSE_RESUME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Hisense TV platform."""
    if DOMAIN_DATA not in hass.data:
        hass.data[DOMAIN_DATA] = []

    broadcast_address = config.get(CONF_BROADCAST_ADDRESS)
    host = config.get(CONF_HOST)
    mac = config.get(CONF_MAC)
    model = config.get(CONF_MODEL).lower()
    name = config.get(CONF_NAME)
    pause_resume = config.get(CONF_PAUSE_RESUME).lower()
    scan_interval = config.get(CONF_SCAN_INTERVAL).total_seconds()

    async_add_entities(
        [
           HisenseTvMediaPlayer(
                name=name,
                host=host,
                mac=mac,
                model=model,
                broadcast_address=broadcast_address,
                scan_interval=scan_interval,
                pause_resume=pause_resume,
           )
        ],
        update_before_add=True,
    )

    async def async_service_handler(service_call: ServiceCall):
        """Handle for services."""
        _LOGGER.debug("service_handle, service=%s", service_call.service)
        if service_call.service == SERVICE_UPDATE_SOURCES:
           entity_ids = service_call.data[ATTR_ENTITY_ID]
           _LOGGER.debug("service_handle, entity(s)=%s", entity_ids)
           for device in hass.data[DOMAIN_DATA].devices:
              if device.entity_id in entity_ids:
                 device.refresh_sources()
                 device.async_schedule_update_ha_state(True)
        elif service_call.service == SERVICE_SEND_COMMAND:
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

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SOURCES,
        async_service_handler,
        schema=SCHEMA_UPDATE_SOURCES,
    )

    _LOGGER.debug("setup_platform, SUCCESS, config=%s", config)

    return True



class HisenseTvMediaPlayer(HisenseTvDevice, MediaPlayerDevice):
    """Representation of a HiSense TV as Media Player."""

    def __init__(self, host: str, mac: str, model: str, name: str, broadcast_address: str, scan_interval: int, pause_resume: str):
        HisenseTvDevice.__init__(self, host, mac, model, name, broadcast_address, scan_interval)
        self._volume = None
        self._min_volume = DEFAULT_MIN_VOLUME
        self._max_volume = DEFAULT_MAX_VOLUME
        self._source = None
        self._source_list = []
        self._state = STATE_OFF
        self._source_map_dict = {}
        self._pause_resume = pause_resume

    @property
    def state(self):
        """Return the state of the device."""
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
        _LOGGER.debug("_refresh_sources - starting...")
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
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def _refresh_volume(self):
        """Refresh volume information."""
        #_LOGGER.debug("_refresh_volume - starting...")
        try:
           with HisenseTv(self._host) as tv:
              volume_info = tv.get_volume()
           if volume_info is not None:
              volume_value =  volume_info.get("volume_value") 
              self._volume = (volume_value / self._max_volume)
              _LOGGER.debug("_refresh_volume - Volume='%s'", volume_value)
        except socket.error as e:
           if "host is unreachable" in str(e).lower():
              _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
           else:
              _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
              raise

    def refresh_sources(self):
        """Refresh source list"""
        self._refresh_sources()

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
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
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
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def volume_up(self):
        """Increase volume by one."""
        try:
            if self._volume is None:
                  self._volume = 0
            else:
               if ((self._volume * self._max_volume) + 1) >= self._max_volume :
                  self._volume = 1
               else:
                  self._volume = self._volume  + (1 / self._max_volume) 
            with HisenseTv(self._host) as tv:
               tv.set_volume( int(self._volume * self._max_volume) )
            _LOGGER.debug("volume_up - Volume='%.3f'", self._volume)
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def volume_down(self):
        """Decrease volume by one."""
        try:
            if self._volume is None:
                  self._volume = 0
            else:
               if ((self._volume * self._max_volume) - 1) <= self._min_volume :
                  self._volume = 0 
               else:
                  self._volume = self._volume  - (1 / self._max_volume)                  
            with HisenseTv(self._host) as tv:
               tv.set_volume( int(self._volume * self._max_volume) )
            _LOGGER.debug("volume_down - Volume='%.3f'", self._volume)
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def media_play(self):
        """Play."""
        try:
            with HisenseTv(self._host) as tv:
               if self._pause_resume == 'ok':
                  tv.send_key_ok()
               elif self._pause_resume == 'pause':
                  tv.send_key_pause()
               else:
                  tv.send_key_play()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def media_pause(self):
        """Pause."""
        try:
            with HisenseTv(self._host) as tv:
               tv.send_key_pause()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def media_next_track(self):
        """Send next track command."""
        try:
            with HisenseTv(self._host) as tv:
               tv.send_key_forwards()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

    def media_previous_track(self):
        """Send previous track command."""
        try:
            with HisenseTv(self._host) as tv:
               tv.send_key_backs()
        except socket.error as e:
            if "host is unreachable" in str(e).lower():
               _LOGGER.error("Unable to reach HisenseTV, likely powered off already")
            else:
               _LOGGER.error("Unexpected error: %s", sys.exc_info()[0])
               raise

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

              # refresh volume
              self._refresh_volume()

              # refresh source list, if empty list (not init yet)
              if not self._source_list:
                 self._refresh_sources()

        except Exception as exception_instance:
            _LOGGER.error(exception_instance)
            self._state = STATE_OFF

