from setuptools import setup, find_packages

setup(
    name="blueberry_tools_service",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,  
    package_data={
        "client.cli": ["tom.ans"], 
    },
     entry_points={
        "console_scripts": [
            "tom = client.cli.tom:main",  
        ],
    },
)