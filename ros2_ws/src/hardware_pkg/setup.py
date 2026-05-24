from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'hardware_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='robocar',
    maintainer_email='benmalvern@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cmd_vel_to_robocar = hardware_pkg.cmd_vel_to_robocar:main',
            'grayscale_calib = hardware_pkg.grayscale_calib:main',
            'grayscale = hardware_pkg.grayscale:main',
            'ultrasonic = hardware_pkg.ultrasonic:main',
        ],
    },
)
