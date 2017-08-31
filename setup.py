from setuptools import setup, find_packages

setup(name='swt-api',
      version='1.0',
      description='swt api',
      author='Luis Cunha',
      author_email='lfcunha@gmail.com',
      url='https://www.niaidceirs.org',
      packages=find_packages(),
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      zip_safe=False,  # don't use eggs,
     )