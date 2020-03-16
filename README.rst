README
######

Installation
************
Place the ``custom_components`` folder into your configuration directory
(or add its contents to an existing ``custom_components`` folder).

Authentication
**************
You will need to perform a one-time authentication for the API to work.
  NOTE: The second command line must be performed for each TV, if control of 
  multiple Hisense TVs is desired.

.. code:: bash

    pip install hisensetv
    hisensetv 10.0.0.28 --authorize

See `newAM/hisensetv <https://github.com/newAM/hisensetv>`_ for more details.

Configuration
*************

host - IP address of TV
mac - MAC address of TV
name - unique entity name of TV
model - TBD
pause_resume - command to send to resume playback after a pause command has been sent
scan_interval - interval of device update in number of seconds

.. code:: yaml

    media_player:
      - platform: hisensetv
        host: 10.0.0.28
        mac: ab:cd:ef:12:34:56
        name: tv                [OPTIONAL]
        model: TBD              [OPTIONAL]
        pause_resume: ok        [OPTIONAL] ['ok' | 'play' | 'pause']
        scan_interval: 60       [OPTIONAL]
        
        
    switch:
      - platform: hisensetv
        host: 10.0.0.28
        mac: ab:cd:ef:12:34:56
        name: tv                [OPTIONAL]
        model: TBD              [OPTIONAL]
        scan_interval: 60       [OPTIONAL]

# NOTE: Either or both can be enabled for a single TV


Television Configuration
************************
-- The following settings must be enabled

*************

.. code:: yaml

 Model: H9 (2019)
 
 -- Setting: Wake Up : Wake On LAN
 NOTE: If using Wireless, then use:
 -- Setting: Wake Up : Wake On Wireless Network
   
Known Issues
************
- For the media_player, the current source is not known until an option is 
selected. Source selection changes performed outside of Home Assistant will 
not be reflected.


Advanced Commands
*****************

For advanced needs, additional commands, such as menu navigation, may be 
sent via the developer tools, under the 'Services' tab.

.. code:: bash

    select service 'hisensetv.send_command'
    click 'FILL EXAMPLE DATA' at bottom
    select Entity - must be HisenseTV device (media_player or switch)
    update command value, as desired
    

Furthermore, the media_player can request an updated list of connected input
sources, as physical changes will not be automatically reflected.

.. code:: bash

    select service 'hisensetv.update_sources'
    select Entity - must be HisenseTV device (media_player)
    
    
Warning
*******
This is provided **as-is**.
Please report any bugs or issues. Thanks!


Docker Issues
*************
- No compatibility issues are observed when running Home Assistant in a docker configuration.


Future
*******
- Determine if model functionality is necessary/valuable for future model expansion possibilities
