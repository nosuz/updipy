import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='updipy',
    version='0.0',
    description='AVR new 0 and 1 series flash writer',
    author="Norio Suzuki",
    author_email="nosuzuki@postcard.st",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nosuz/updipy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.6',
    install_requires=['pyserial'],
    entry_points={
        'console_scripts': [
            'updipy = updipy.updipy:main',
        ],
    },
)
