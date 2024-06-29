from setuptools import setup

setup(
    name='fce',
    version='0.0.1',
    description='Future Collider Experiment',
    url='https://github.com/kskovpen/FCE',
    author='Kirill Skovpen',
    author_email='kirill.skovpen@ugent.be',
    license='LGPL-2.1',
    readme='README.md',
    packages=['fce'],
    scripts=['bin/fce'],
    install_requires=['PyQt6', 'boost_histogram', 'uproot', 'matplotlib', 'mplhep', 'pyhf', 'cabinetry'],
    package_data={'fce': ['config/samples.json', 'config/selection.dat', 'config/analysis.dat', 'data/fce.ico']},
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: LGPL License',
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3'
    ]
)