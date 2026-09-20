import asyncio
import time


async def fetch_data(task_id: int, semaphore: asyncio.Semaphore):
    # Acquire a slot; if 3 are already active, this pauses execution here
    async with semaphore:
        print(f"[Task {task_id}] Acquired slot at {time.strftime('%X')}")
        
        # Simulate an I/O network request (e.g., API call)
        await asyncio.sleep(2) 
        
        print(f"[Task {task_id}] Releasing slot...")
    # The semaphore is automatically released here

async def main():
    # Initialize the semaphore allowing a maximum of 3 concurrent tasks
    sem = asyncio.Semaphore(3)
    
    # Fire off 10 tasks concurrently
    tasks = [fetch_data(i, sem) for i in range(10)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
