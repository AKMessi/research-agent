"""Setup script for the Ultimate Research Agent."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ultimate-research-agent",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Production-grade AI research agent with structured output",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_USERNAME/ultimate-research-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "research-agent=main:main",
        ],
    },
    keywords="research ai agent llm ollama web-search automation",
    project_urls={
        "Bug Reports": "https://github.com/YOUR_USERNAME/ultimate-research-agent/issues",
        "Source": "https://github.com/YOUR_USERNAME/ultimate-research-agent",
    },
)
