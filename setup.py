from setuptools import setup, find_packages

setup(
    name="instabids-a2a",
    version="0.1.0",
    description="InstaBids A2A Implementation",
    author="JustinAIDistuptors",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # Add your dependencies here
        "supabase>=2.3.1",
        "asyncpg>=0.27.0",
        "pgvector>=0.2.6",
    ],
    python_requires=">=3.9",
)