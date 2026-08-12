import asyncio
import pytest
from async_scrapers import aggregate_all_reviews


@pytest.mark.asyncio
async def test_scrapers():
    print("Testing all scrapers for Dune (2021)...")
    res = await aggregate_all_reviews("tt1160419", "Dune", "2021", False, 200)
    for k, v in res.items():
        print(f"  {k}: {len(v)} reviews")
    print("Total:", sum(len(v) for v in res.values()))

if __name__ == "__main__":
    asyncio.run(test_scrapers())
