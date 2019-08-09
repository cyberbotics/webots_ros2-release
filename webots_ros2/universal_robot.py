# Copyright 1996-2019 Cyberbotics Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ROS2 Universal Robots controller."""

import rclpy
import os
import sys

from time import sleep

from webots_ros2.joint_state_publisher import JointStatePublisher
from webots_ros2.trajectory_follower import TrajectoryFollower

from rosgraph_msgs.msg import Clock

from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter

if 'WEBOTS_HOME' not in os.environ:
    sys.exit('"WEBOTS_HOME" not defined.')

try:
    sys.path.append(os.path.join(os.environ['WEBOTS_HOME'], 'lib', 'python%d%d' %
                    (sys.version_info[0], sys.version_info[1])))
    from controller import Robot
except Exception as e:
    sys.stderr.write('"WEBOTS_HOME" is not correctly set.')
    raise(e)


class ActionServerNode(Node):

    def __init__(self):
        super().__init__('ur_driver')
        sleep(15)  # TODO: wait to make sure that Webots is started
        self.robot = Robot()
        prefix = self.get_parameter_or('prefix',
                                       Parameter('prefix', Parameter.Type.STRING, '')).value
        self.jointStatePublisher = JointStatePublisher(self.robot, prefix, self)
        self.trajectoryFollower = TrajectoryFollower(self.robot, self, jointPrefix=prefix)
        self.trajectoryFollower.start()
        self.timestep = int(self.robot.getBasicTimeStep())
        self.clockPublisher = self.create_publisher(Clock, 'topic', 10)
        timer_period = 0.001 * self.timestep  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        if self.robot is None:
            return
        # Publish clock
        msg = Clock()
        time = self.robot.getTime()
        msg.clock.sec = int(time)
        # round prevents precision issues that can cause problems with ROS timers
        msg.clock.nanosec = int(round(1000 * (time - msg.clock.sec)) * 1.0e+6)
        self.clockPublisher.publish(msg)
        # update joint state and trajectory follower
        self.jointStatePublisher.publish()
        # Robot step
        if self.robot.step(self.timestep) < 0.0:
            del self.robot
            self.robot = None
            sys.exit(0)


def main(args=None):
    rclpy.init(args=args)

    actionServer = ActionServerNode()

    # Use a MultiThreadedExecutor to enable processing goals concurrently
    executor = MultiThreadedExecutor()

    rclpy.spin(actionServer, executor=executor)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    actionServer.destroy()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
