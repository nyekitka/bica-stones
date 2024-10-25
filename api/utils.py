import asyncio

class VariableWaiter:
    def __init__(self):
        self.var = None
        self.cond = asyncio.Condition()
        
    async def wait_for_value(self, value):
        async with self.cond:
            while self.var != value:
                await self.cond.wait()
            
    async def set_value(self, value):
        async with self.cond:
            self.var = value
            self.cond.notify_all()