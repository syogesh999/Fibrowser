#!/usr/bin/env python3
"""
Fibrowser Pro - A feature-rich web browser built with PyQt5
Modern, sleek, and highly customizable desktop browser with theme support,
multi-tab browsing, download manager, and developer tools.

This file acts as a slim wrapper entry script to run the modularized package.
"""

import sys
from fibrowser.main import main

if __name__ == '__main__':
    sys.exit(main())