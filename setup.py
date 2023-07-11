from os.path import dirname, join

from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def read(fname):
    return open(join(dirname(__file__), fname)).read()


setup(
    name='infoblox-discovery',
    long_description=long_description,
    long_description_content_type='text/markdown',
    setuptools_git_versioning={
        "template": "{tag}",
        "dev_template": "{tag}.dev{ccount}",
        "dirty_template": "{tag}.post{ccount}+git.{sha}.dirty",
        "starting_version": "0.0.1",
        "version_callback": None,
        "version_file": None,
        "count_commits_from_version_file": False,
        "branch_formatter": None
    },
    setup_requires=['setuptools-git-versioning'],
    packages=find_packages(),
    author='thenodon',
    author_email='aha@ingby.com',
    url='https://github.com/thenodon/infoblox_discovery',
    license='GPLv3',
    include_package_data=True,
    zip_safe=False,
    description="A Prometheus file and http discovery for infoblox",
    install_requires=read('requirements.txt').split(),
    python_requires='>=3.8',
)