import os

from setuptools import find_packages, setup

version_ns = {}
with open(os.path.join("funcx_websocket_service", "version.py")) as f:
    exec(f.read(), version_ns)
version = version_ns["VERSION"]


REQUIRES = [
    "aioredis>=2.0.0",
    "aiohttp",
    "websockets",
    "aio-pika",
    "python-json-logger",
    "funcx-common[redis,boto3]==0.0.10",
    "redis==3.5.3",
]

setup(
    name="funcx_websocket_service",
    version=version,
    packages=find_packages(),
    description="funcX WebSocket Service: "
    "High Performance Function Serving for Science",
    install_requires=REQUIRES,
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering",
    ],
    keywords=["funcX", "FaaS", "Function Serving"],
    entry_points={
        "console_scripts": [
            "websocket-service=funcx_websocket_service.application:cli",
        ]
    },
    author="funcX team",
    author_email="labs@globus.org",
    license="Apache License, Version 2.0",
    url="https://github.com/funcx-faas/funcx",
)
