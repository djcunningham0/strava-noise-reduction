"""
TODO:
 - design a better Kalman filter (currently using a simple 2nd order filter, but
   need to allow for acceleration/changes of direction)
 - figure out how to convert (lat, long, altitude) to (x, y, z) in the matrix math
   (currently treating lat and long like x and y)
"""

from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise, Saver, kinematic_kf
from scipy.linalg import block_diag
import numpy as np

from typing import List


def create_kalman_filter(
        lat: List[float],
        long: List[float],
        uncertainty_pos: float,
        uncertainty_velo: float,
        state_uncertainty_pos: float,
        q_var: float,
        dt: float = 1.0,
) -> KalmanFilter:
    uncertainty_x = uncertainty_pos / 5280 / 69  # uncertainty latitude -- convert from feet: x / 5280 / 69
    uncertainty_vx = (uncertainty_velo / 3 / 5280 / 69) ** 2  # max speed = 25 ft/s (running) --> 3*sigma = 25 --> sigma^2 = (25/3 / 5280 / 69)^2
    uncertainty_y = uncertainty_pos / 5280 / 53  # uncertainty longitude -- convert from feet: x / 5280 / 53
    uncertainty_vy = (uncertainty_velo / 3 / 5280 / 69)

    kf = KalmanFilter(dim_x=4, dim_z=2)
    kf.x = np.array([lat[0], lat[1] - lat[0], long[1], long[1] - long[0]]).T  # initial state (location and velocity)
    kf.F = np.array([[1., dt, 0., 0.],
                     [0., 1., 0., 0.],
                     [0., 0., 1., dt],
                     [0., 0., 0., 1.]])  # state transition matrix
    kf.H = np.array([[1., 0., 0., 0.],
                     [0., 0., 1., 0.]])  # Measurement function
    kf.P = np.diag([uncertainty_x, uncertainty_vx, uncertainty_y, uncertainty_vy])  # covariance matrix
    kf.R = np.array([[state_uncertainty_pos / 5280 / 69, 0.],
                     [0., state_uncertainty_pos / 5280 / 53]])  # state uncertainty -- again convert from feet to latitude
    q = Q_discrete_white_noise(dim=2, dt=dt, var=q_var)
    kf.Q = block_diag(q, q)  # process uncertainty -- should probably be close to zero
    return kf
