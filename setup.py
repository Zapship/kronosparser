from setuptools import find_packages, setup

setup(name='kronosparser',
      version='0.0.1',
      description='Python package for parsing dates',
      long_description=open('README.rst').read(),
      url='https://github.com/zapship/kronosparsing',
      author="Gaston L'Huillier",
      author_email='g@sudoai.com',
      license='MIT License',
      packages=find_packages(),
      package_data={'': ['README.rst', 'LICENSE']},
      zip_safe=False,
      install_requires=[x.strip() for x in open("requirements.txt").readlines()])
