"""Module to support Dummy BMS."""

# import asyncio
import logging
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.uuids import normalize_uuid_str

from custom_components.bms_ble.const import (
    ATTR_BATTERY_CHARGING,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_CHARGING,
    ATTR_CURRENT,
    ATTR_CYCLE_CAP,
    ATTR_CYCLE_CHRG,
    # ATTR_CYCLES,
    # ATTR_DELTA_VOLTAGE,
    ATTR_POWER,
    ATTR_RUNTIME,
    ATTR_TEMPERATURE,
    ATTR_VOLTAGE,
)

from .basebms import BaseBMS, BMSsample

LOGGER = logging.getLogger(__name__)
BAT_TIMEOUT = 10


class BMS(BaseBMS):
    """Dummy battery class implementation."""
    check = {} 
    values = {}
    
    def __init__(self, ble_device: BLEDevice, reconnect: bool = False) -> None:
        """Initialize BMS."""
        LOGGER.debug("%s init(), BT address: %s", self.device_id(), ble_device.address)
#        super().__init__(LOGGER, self._notification_handler, ble_device, reconnect)
        super().__init__(__name__, ble_device, reconnect)
    @staticmethod
    def matcher_dict_list() -> list[dict[str, Any]]:
        """Provide BluetoothMatcher definition."""
        return [{"manufacturer_id": 43863, "connectable": True}]

    @staticmethod
    def device_info() -> dict[str, str]:
        """Return device information for the battery management system."""
        return {"manufacturer": "Yunctek", "model": "KG-F"}

    @staticmethod
    def uuid_services() -> list[str]:
        """Return list of 128-bit UUIDs of services required by BMS."""
        return [normalize_uuid_str("0000fff1-0000-1000-8000-00805f9b34fb")]  # change service UUID here!

    @staticmethod
    def uuid_rx() -> str:
        """Return 16-bit UUID of characteristic that provides notification/read property."""
        return "0000fff1-0000-1000-8000-00805f9b34fb"

    @staticmethod
    def uuid_tx() -> str:
        """Return 16-bit UUID of characteristic that provides write property."""
        return "#changeme"

    @staticmethod
    def _calc_values() -> set[str]:
        return {
            ATTR_POWER,
            ATTR_BATTERY_CHARGING,
        }  # calculate further values from BMS provided set ones

    def _notification_handler(self, _sender, data: bytearray) -> None:
        """Handle the RX characteristics notify event (new data arrives)."""
        bs = str(data.hex()).upper()
        params = {
            "voltage": "C0", # V
            "current": "C1", # A
            "dir_of_current": "D1", # binary
            "ah_remaining": "D2", # Ah
            "discharge": "D3",      # KWh
            "charge": "D4",         # KWh
            "mins_remaining": "D6", #  Min
            "impedance": "D7",           # mΩ
            "power": "D8", # W
            "temp": "D9", # C/F
            "battery_capacity": "B1" # A
        }
        params_keys = list(params.keys())
        params_values = list(params.values())

        # split bs into a list of all values and hex keys
        bs_list = [bs[i:i+2] for i in range(0, len(bs), 2)]

        # reverse the list so that values come after hex params
        bs_list_rev = list(reversed(bs_list))

        
        
                # iterate through the list and if a param is found,
        # add it as a key to the dict. The value for that key is a
        # concatenation of all following elements in the list
        # until a non-numeric element appears. This would either
        # be the next param or the beginning hex value.
        for i in range(len(bs_list_rev)-1):
            if bs_list_rev[i] in params_values:
                value_str = ''
                j = i + 1
                while j < len(bs_list_rev) and bs_list_rev[j].isdigit():
                    value_str = bs_list_rev[j] + value_str
                    j += 1

                position = params_values.index(bs_list_rev[i])

                key = params_keys[position]
                if key == "voltage":
                    val_int = int(value_str)
                    self.values[key] = val_int / 100
                elif key == "dir_of_current":
                    if key == "dir_of_current":
                        if value_str == "01":
                            self.check["charging"] = True
                        else:
                            self.check["charging"] = False                    
                elif key == "current":
                    val_int = int(value_str)
                    self.values[key] = val_int / 100
                    # Display current as negative numbers if discharging
                    if "charging" in self.check:
                        if self.check["charging"] == False:
                            self.values[key] *= -1
                elif key == "battery_capacity":
                    val_int = int(value_str)
                    self.values[key] = val_int / 10
                elif key == "temp":
                    val_int = int(value_str)
                    self.values[key] = val_int - 100                      
                elif key == "ah_remaining":
                    val_int = int(value_str)
                    self.values[key] = val_int / 1000
                elif key == "discharge":
                    val_int = int(value_str)
                    self.values[key] = val_int / 100000
                elif key == "charge":
                    val_int = int(value_str)
                    self.values[key] = val_int / 100000
                    
                elif key == "mins_remaining":
                    val_int = int(value_str)
                    self.values[key] = val_int*60 
                elif key == "power":
                    val_int = int(value_str)
                    self.values[key] = val_int / 100
                    # Display current as negative numbers if discharging
                    if "charging" in self.check:
                        if self.check["charging"] == False:
                            self.values[key] *= -1
                else:
                    self.values[key] = value_str
                
        # check if dir_of_current exist if not asign if charging or dischargin exist
        if "dir_of_current" not in self.values and "charging" not in self.check:
            if "discharge" in self.values and "charge" not in self.values:
                self.values["dir_of_current"] = "00"
            elif "charge" in self.values and "discharge" not in self.values:
                self.values["dir_of_current"] = "01"


        # Calculate percentage
        #if isinstance(battery_capacity_ah, int) and "ah_remaining" in values:
            #self.data.jt_soc = soc = values["ah_remaining"] / battery_capacity_ah * 100
            #if "soc" not in values or soc != values["soc"]:
                #self.data.jt_soc = values["soc"] = soc
        # Update old results with new values
        #result.update(values)


        
        #LOGGER.debug("%s: Received BLE data: %s", self.name, data.hex(' '))
        LOGGER.debug("%s: Received BLE data: %s", self.name, self.values)
        # 
        # # do things like checking correctness of frame here and
        # # store it into a instance variable, e.g. self._data
        #
       # self._data_event.set()

    async def _async_update(self) -> BMSsample:
        """Update battery status information."""
        LOGGER.debug("(%s) replace with command to UUID %s", self.name, BMS.uuid_tx())
        # await self._client.write_gatt_char(BMS.uuid_tx(), data=b"<some_command>")
        # await asyncio.wait_for(self._wait_event(), timeout=BAT_TIMEOUT) # wait for data update
        # #
        # # parse data from self._data here
        data: BMSsample = {}
        if("voltage" in self.values):
            data[ATTR_VOLTAGE]=self.values["voltage"]
        if("temp" in self.values):
            data[ATTR_TEMPERATURE]=self.values["temp"]            
        if("current" in self.values):
            data[ATTR_CURRENT]=self.values["current"]
        if("ah_remaining" in self.values):
            data[ATTR_BATTERY_LEVEL]=self.values["ah_remaining"]
        if("ah_remaining" in self.values and "voltage" in self.values):
            data[ATTR_CYCLE_CAP]=self.values["ah_remaining"]*self.values["voltage"]
        if("power" in self.values):
            data[ATTR_POWER]=self.values["power"]  
        if("mins_remaining" in self.values):
            data[ATTR_RUNTIME]=self.values["mins_remaining"]
        if "charging" in self.check:
            data[ATTR_BATTERY_CHARGING]=self.check["charging"] 
#        return {
#            ATTR_VOLTAGE: self.values["voltage"],
#            ATTR_CURRENT: 1.5,
#        }  #
        return data;