from setuptools import setup, find_packages

setup(
    name="uvc",
    description="The Uber Version Controller. Early release of the version control facade used by Bespin.",
    author="Kevin Dangoor",
    author_email="dangoor+uvc@gmail.com",
    version="0.2.2",
    license="MPL/GPL/LGPL",
    url="http://bitbucket.org/dangoor/uvc/",
    packages=find_packages(),
    entry_points="""
        [console_scripts]
        uvc = uvc.main:run
    """
    
)
