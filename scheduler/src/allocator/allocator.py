from datetime import datetime, timedelta
from .time_slot import TimeSlot
from typing import Optional

class Allocator:
    def __init__(self, slots_count: int, allocation_interval_minutes: int) -> None:
        self.__slots_count = slots_count
        self.__allocation_interval_minutes = allocation_interval_minutes
        self.__allocation_time = timedelta(minutes = self.__allocation_interval_minutes * self.__slots_count)
        self.__slots = self.__create_slots()
        
        self.__minimal_slot_index = 0
        self.__current_slot_index = 0
    
    def add_channel(self, channel_id: int) -> datetime:
        slot = self.__slots[self.__minimal_slot_index % self.__slots_count]
        slot.add_channel(channel_id)
        self.__minimal_slot_index += 1
        return slot.start_time

    def get_next_channels(self) -> Optional[list[int]]:
        slot = self.__slots[self.__current_slot_index % self.__slots_count]
        if slot.start_time <= datetime.now():
            self.__current_slot_index += 1
            slot.start_time += self.__allocation_time
            return [i for i in slot]
        return None
        
    def __create_slots(self) -> list[TimeSlot]:
        return [TimeSlot(datetime.now() + timedelta(minutes=self.__allocation_interval_minutes * i)) for i in range(self.__slots_count)]