from setuptools import setup

from pathlib import Path


CURRENT_DIR = Path(__file__).parent


# Specific Python Test Runner (ptr) params for Unit Testing Enforcement
ptr_params = {
    "entry_point_module": "src/json2netns/main",
    "test_suite": "json2netns.tests.base",
    "test_suite_timeout": 120,
    "required_coverage": {
        "json2netns/config.py": 90,
        "json2netns/main.py": 70,
        "json2netns/netns.py": 70,
    },
    "run_black": True,
    "run_mypy": True,
    "run_flake8": True,
}


def get_long_description() -> str:
    return (CURRENT_DIR / "README.md").read_text(encoding="utf8")


setup(
    name="json2netns",
    version="2021.5.17",
    description="JSON parsing Linux Network Namespace (netns) topology builder.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    keywords="json linux netns network namespace",
    author="Cooper Ry Lees",
    author_email="me@cooperlees.com",
    url="https://github.com/cooperlees/json2netns",
    license="BSD",
    packages=["json2netns", "json2netns.tests"],
    package_dir={"": "src"},
    package_data={
        "json2netns": ["sample.json"],
    },
    python_requires=">=3.8.0",
    install_requires=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    entry_points={
        "console_scripts": [
            "json2netns=json2netns.main:main",
        ]
    },
)
