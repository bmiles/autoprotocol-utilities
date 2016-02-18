from setuptools import setup

setup(name='autoprotocol_utilities',
      version='0.1',
      description='Helper methods to construct protocols using autoprotocol-python.',
      url='git clone ssh://vcs@work.r23s.net/diffusion/APUTILS/autoprotocol-utilities.git',
      author='Conny Scheitz, Vanessa Biggers and all past and present Application Scientists',
      author_email='conny@transcriptic.com, vanessa@transcriptic.com',
      license='MIT',
      packages=['autoprotocol_utilities'],
      tests_require=['pytest'],
      install_requires=['autoprotocol>=2.6'],
      zip_safe=False)
