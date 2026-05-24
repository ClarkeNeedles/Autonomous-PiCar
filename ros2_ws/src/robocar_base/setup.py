from setuptools import find_packages, setup
import os
from glob import glob

package_name = "robocar_base"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="robocar",
    maintainer_email="robocar@todo.todo",
    description="RoboCar base: cmd_vel to motor outputs",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            'auto_drive_motors = robocar_base.auto_drive_motors:main',
            'rpi_cam_stream_node = robocar_base.rpi_cam_stream_node:main',
            'video_recorder_node = robocar_base.video_recorder_node:main'
        ],
    },
)
