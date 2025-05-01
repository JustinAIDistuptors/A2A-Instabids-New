"""CLI runner for HomeownerAgent."""
import argparse
from pathlib import Path
import asyncio

from instabids.agents.factory import get_homeowner_agent


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run HomeownerAgent locally")
    parser.add_argument("--user", required=True, help="homeowner user_id")
    parser.add_argument("--image", nargs="*", help="path(s) to project image(s)")
    parser.add_argument("--text", help="initial description text")
    args = parser.parse_args()

    agent = get_homeowner_agent()
    result = await agent.process_input(
        user_id=args.user,
        description=args.text,
        image_paths=[Path(p) for p in args.image] if args.image else None,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
