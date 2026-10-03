from setuptools import setup, find_packages

setup(
    name="becoming-a-bihari",
    version="0.1.0",
    description="Privacy-first, vibe-aware meme delivery system for Windows 11",
    author="Raushan",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "pywin32>=306",
        "pynput>=1.7.6",
        "pystray>=0.19.5",
        "Pillow>=10.0.0",
        "psutil>=5.9.0",
        "requests>=2.28.0",
        "winocr>=0.0.15",
        "tomli>=2.0.0; python_version < '3.11'",
    ],
    extras_require={
        "ai": ["laya>=0.3.0"],
    },
    entry_points={
        "console_scripts": [
            "bihari=bihari.__main__:main",
            "vihara=bihari.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment",
        "Topic :: Games/Entertainment",
    ],
)
