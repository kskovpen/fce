from setuptools import setup

setup(
    name='fce',
    version='0.0.2a',
    description='Future Collider Experiment',
    url='https://github.com/kskovpen/FCE',
    author='Kirill Skovpen',
    author_email='kirill.skovpen@ugent.be',
    license='LGPL-2.1',
    readme='README.md',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    packages=['fce'],
    scripts=['bin/fce'],
    entry_points={'console_scripts': ['fce-datasets=fce.fce_datasets:fce_datasets']},
    python_requires=">=3.8",
    install_requires=['PyQt6', 'boost_histogram', 'uproot', 'matplotlib', 'mplhep', 'pyhf', 'cabinetry'],
    package_data={'fce': ['config/samples.json', 'config/selection.dat', 'config/analysis.dat', 'config/skim.dat', 'data/fce.ico']},
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        "Operating System :: OS Independent",
        'Programming Language :: Python :: 3'
    ]
)