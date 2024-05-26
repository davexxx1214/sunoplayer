from setuptools import setup, find_packages

setup(
    name='suno_songs',
    version='0.5.2',
    packages=find_packages(),
    install_requires=[
        'curl_cffi',
        'fake-useragent',
        'requests',
        'rich',
        'python-dotenv',
    ],
)