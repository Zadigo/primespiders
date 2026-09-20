import asyncio


async def something():
    await asyncio.sleep(6)
    print("Finished sleeping for 6 seconds")

async def something_else():
    await asyncio.sleep(3)
    print("Finished sleeping for 3 seconds")


async def main():
    # await something()
    # await something_else()

    t1 = asyncio.create_task(something())
    t2 = asyncio.create_task(something_else())
    
    await t1
    await t2

if __name__ == "__main__":
    asyncio.run(main())
