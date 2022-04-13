import glob
import os
import shutil

import discretisedfield as df
import numpy as np
import pytest
from scipy.optimize import bisect

import mumaxc as mc


@pytest.mark.oommf
def test_stdprob3():
    name = "stdprob3"

    # Remove any previous simulation directories.
    if os.path.exists(name):
        shutil.rmtree(name)

    # Function for initiaising the flower state.
    def m_init_flower(pos):
        x, y, z = pos[0] / 1e-9, pos[1] / 1e-9, pos[2] / 1e-9
        mx = 0
        my = 2 * z - 1
        mz = -2 * y + 1
        norm_squared = mx**2 + my**2 + mz**2
        if norm_squared <= 0.05:
            return (1, 0, 0)
        else:
            return (mx, my, mz)

    # Function for initialising the vortex state.
    def m_init_vortex(pos):
        x, y, z = pos[0] / 1e-9, pos[1] / 1e-9, pos[2] / 1e-9
        mx = 0
        my = np.sin(np.pi / 2 * (x - 0.5))
        mz = np.cos(np.pi / 2 * (x - 0.5))

        return (mx, my, mz)

    def minimise_system_energy(L, m_init):
        N = 16  # discretisation in one dimension
        cubesize = 100e-9  # cube edge length (m)
        cellsize = cubesize / N  # discretisation in all three dimensions.
        lex = cubesize / L  # exchange length.

        Km = 1e6  # magnetostatic energy density (J/m**3)
        Ms = np.sqrt(2 * Km / mc.mu0)  # magnetisation saturation (A/m)
        A = 0.5 * mc.mu0 * Ms**2 * lex**2  # exchange energy constant
        K = 0.1 * Km  # Uniaxial anisotropy constant
        u = (0, 0, 1)  # Uniaxial anisotropy easy-axis

        p1 = (0, 0, 0)  # Minimum sample coordinate.
        p2 = (cubesize, cubesize, cubesize)  # Maximum sample coordinate.
        cell = (cellsize, cellsize, cellsize)  # Discretisation.
        mesh = mc.Mesh(
            p1=(0, 0, 0),
            p2=(cubesize, cubesize, cubesize),
            cell=(cellsize, cellsize, cellsize),
        )

        # Remove any previous simulation directories.
        if os.path.exists(name):
            shutil.rmtree(name)

        system = mc.System(name=name)
        system.hamiltonian = mc.Exchange(A) + mc.UniaxialAnisotropy(K, u) + mc.Demag()
        system.m = df.Field(mesh, value=m_init, norm=Ms)

        md = mc.RelaxDriver()
        md.drive(system)

        if os.path.exists(name):
            shutil.rmtree(name)

        return system

    def energy_difference(L):
        vortex = minimise_system_energy(L, m_init_vortex)
        flower = minimise_system_energy(L, m_init_flower)

        print(vortex.dt.columns)

        return vortex.total_energy() - flower.total_energy()

    cross_section = bisect(energy_difference, 8, 9, xtol=0.1)
    assert 8.4 < cross_section < 8.5

    if os.path.exists(name):
        shutil.rmtree(name)
