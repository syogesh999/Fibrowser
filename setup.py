#!/usr/bin/env python3
"""
Setup configuration for Fibrowser Pro v2.0
Advanced web browser built with PyQt5
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from main.py
main_file = Path(__file__).parent / "main.py"
version = "2.0.0"

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

if __name__ == '__main__':
    setup(
        name="fibrowser-pro",
        version=version,
        description="Advanced web browser built with PyQt5 - Modern, feature-rich, performant",
        long_description=long_description,
        long_description_content_type="text/markdown",
        author="Development Team",
        python_requires=">=3.8",
        install_requires=[
            "PyQt5>=5.15.9",
            "PyQtWebEngine>=5.15.7",
        ],
        extras_require={
            "dev": [
                "PyInstaller>=6.2.0",
                "python-dotenv>=1.0.0",
            ],
        },
        packages=find_packages(),
        entry_points={
            "console_scripts": [
                "fibrowser=fibrowser.main:main",
            ],
        },
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: End Users/Desktop",
            "Topic :: Internet :: WWW/HTTP :: Browsers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Operating System :: OS Independent",
        ],
        keywords="browser web pyqt5 desktop",
        project_urls={
            "Homepage": "https://github.com/syogesh999/Fibrowser",
            "Documentation": "https://github.com/syogesh999/Fibrowser#readme",
            "Repository": "https://github.com/syogesh999/Fibrowser.git",
            "Issues": "https://github.com/syogesh999/Fibrowser/issues",
        },
    )

