"""CLI driver for HomeownerAgent."""
import argparse
from instabids.agents.homeowner_agent import HomeownerAgent
from memory.persistent_memory import PersistentMemory

parser = argparse.ArgumentParser()
parser.add_argument("--description", required=True)
args = parser.parse_args()

agent = HomeownerAgent(memory=PersistentMemory())
print("Created project:", agent.start_project(args.description))