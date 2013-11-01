import sys
sys.path.insert(0, 'src/reversion')
from distutils.core import setup

# Load in babel support, if available.
try:
    from babel.messages import frontend as babel
    cmdclass = {"compile_catalog": babel.compile_catalog,
                "extract_messages": babel.extract_messages,
                "init_catalog": babel.init_catalog,
                "update_catalog": babel.update_catalog,}
except ImportError:
    cmdclass = {}

setup(name="django-reversion",
      version='1.7.1',
      license="BSD",
      description="An extension to the Django web framework that provides comprehensive version control facilities",
      long_description=open("README.rst").read(),
      author="Dave Hall",
      author_email="andrewshkovskii@gmail.com",
      url="http://github.com/andrewshkovskii/django-reversion",
      zip_safe=False,
      packages=["reversion", "reversion.management", "reversion.management.commands", "reversion.migrations", "reversion.serializer",],
      package_dir={"": "src"},
      package_data={"reversion": ["locale/*/LC_MESSAGES/django.*", "templates/reversion/*.html"]},
      cmdclass=cmdclass,
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.2',
                   'Programming Language :: Python :: 3.3',
                   "Framework :: Django",])
