"""Setup script for course outline to iCalendar converter."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="course-outline-converter",
    version="0.1.0",
    author="Course Outline Converter",
    description="Convert Western University course outline PDFs to iCalendar files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pdfplumber>=0.10.0",
        "dateparser>=1.2.0",
        "icalendar>=5.0.0",
        "pytz>=2023.3",
    ],
    entry_points={
        "console_scripts": [
            "course-outline-convert=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Topic :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)


