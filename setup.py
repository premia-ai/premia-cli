import json
from setuptools import find_packages, setup


def load_requirements():
    with open("Pipfile.lock") as file:
        lock_data = json.load(file)
        return [
            package_name + package_info["version"]
            for package_name, package_info in lock_data["default"].items()
        ]


setup(
    name="premia",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=load_requirements(),
    entry_points={"console_scripts": ["premia = premia.cli:cli"]},
)
