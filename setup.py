from setuptools import setup, find_packages

setup(
    name="instabids-a2a",
    version="0.1.0",
    description="InstaBids A2A Implementation",
    author="JustinAIDistuptors",
    packages=find_packages(include=["instabids_google", "instabids_google.*"]),
    install_requires=[
        # Add your dependencies here
    ],
    python_requires=">=3.9",
)