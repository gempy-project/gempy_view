﻿import copy

import numpy as np
from matplotlib import pyplot as plt
import scipy.spatial.distance as dd

from gempy.core.grid_modules.grid_types import RegularGrid, Sections
from gempy.core.grid_modules.topography import Topography
from .visualization_2d import Plot2D
from gempy import GeoModel
from gempy.core.grid import Grid


def plot_data(plot_2d: Plot2D, gempy_model: GeoModel, ax, section_name=None, cell_number=None, direction='y',
              legend=True, projection_distance=None):
    if projection_distance is None:
        # TODO: This has to be updated to the new location
        projection_distance = 0.2 * gempy_model.transform.isometric_scale

    # TODO: This are not here 
    points = gempy_model.surface_points.df.copy()
    orientations = gempy_model.orientations.df.copy()

    # TODO: This is a weird check to do this deep
    section_name, cell_number, direction = plot_2d._check_default_section(ax, section_name, cell_number, direction)

    if section_name is not None:
        Gx, Gy, cartesian_ori_dist, cartesian_point_dist, x, y = _projection_params_section(
            grid=gempy_model.grid,
            orientations=orientations,
            points=points,
            projection_distance=projection_distance,
            section_name=section_name
        )
    else:
        cartesian_ori_dist, cartesian_point_dist = _projection_params_regular_grid(
            regular_grid=gempy_model.grid.regular_grid,
            cell_number=cell_number,
            direction=direction,
            orientations=orientations,
            points=points
        )

        _, _, _, _, x, y, Gx, Gy = plot_2d.slice(
            regular_grid=gempy_model.grid.regular_grid,
            direction=direction
        )

    select_projected_p = cartesian_point_dist < projection_distance
    select_projected_o = cartesian_ori_dist < projection_distance

    # Hack to keep the right X label:
    temp_label = copy.copy(ax.xaxis.label)

    # region plot points
    points_df = points[select_projected_p]

    # ? The following code is the old one using pandas
    if False:  # TODO: Get rid of pandas completely
        points_df.plot.scatter(
            x=x, y=y, ax=ax,
            c=np.array(gempy_model.structural_frame.surface_points_colors)[select_projected_p],
            s=70,
            zorder=102,
            edgecolors='white',
            colorbar=False
        )
    else:
        x_values = points_df[x]
        y_values = points_df[y]
        colors = np.array(gempy_model.structural_frame.surface_points_colors)[select_projected_p]
        ax.scatter(
            x_values,
            y_values,
            c=colors,
            s=70,
            edgecolors='white',
            zorder=102
        )

    # endregion
    # region plot orientations

    sel_ori = orientations[select_projected_o]

    aspect = np.subtract(*ax.get_ylim()) / np.subtract(*ax.get_xlim())
    min_axis = 'width' if aspect < 1 else 'height'

    ax.quiver(
        sel_ori[x], sel_ori[y], sel_ori[Gx], sel_ori[Gy],
        pivot="tail",
        scale_units=min_axis,
        scale=30,
        color=np.array(gempy_model.structural_frame.orientations_colors)[select_projected_o],
        edgecolor='k',
        headwidth=8,
        linewidths=1,
        zorder=102
    )

    # endregion

    # region others

    if plot_2d.fig.is_legend is False and legend is True or legend == 'force':
        ax.legend(
            handles=[plt.Line2D([0, 0], [0, 0], color=color, marker='o', linestyle='') for color in gempy_model.structural_frame.elements_colors][::-1],
            labels=gempy_model.structural_frame.elements_names,
            numpoints=1
        )
        plot_2d.fig.is_legend = True

    ax.xaxis.label = temp_label

    try:
        ax.legend_.set_frame_on(True)
        ax.legend_.set_zorder(10000)
    except AttributeError:
        pass

    # endregion


def _projection_params_regular_grid(regular_grid: RegularGrid, cell_number, direction, orientations, points):
    if cell_number is None or cell_number == "mid":
        cell_number = int(regular_grid.resolution[0] / 2)

    if direction == 'x' or direction == 'X':
        arg_ = 0
        dx = regular_grid.dx
        dir = 'X'
    elif direction == 'y' or direction == 'Y':
        arg_ = 2
        dx = regular_grid.dy
        dir = 'Y'
    elif direction == 'z' or direction == 'Z':
        arg_ = 4
        dx = regular_grid.dz
        dir = 'Z'
    else:
        raise AttributeError('Direction must be x, y, z')

    _loc = regular_grid.extent[arg_] + dx * cell_number
    cartesian_point_dist = points[dir] - _loc
    cartesian_ori_dist = orientations[dir] - _loc

    return cartesian_ori_dist, cartesian_point_dist


def _projection_params_section(grid: Grid, orientations: 'pd.DataFrame', points: 'pd.DataFrame',
                               projection_distance: float, section_name: str):
    if section_name == 'topography':
        Gx, Gy, cartesian_ori_dist, cartesian_point_dist, x, y = _projection_params_topography(
            topography=grid.topography,
            orientations=orientations,
            points=points,
            projection_distance=projection_distance,
        )
    else:
        # Project points:
        sections: Sections = grid.sections
        shift = np.asarray(sections.df.loc[section_name, 'start'])
        end_point = np.atleast_2d(np.asarray(sections.df.loc[section_name, 'stop']) - shift)
        A_rotate = np.dot(end_point.T, end_point) / sections.df.loc[section_name, 'dist'] ** 2

        perpe_sqdist = ((np.dot(A_rotate, (points[['X', 'Y']]).T).T - points[['X', 'Y']]) ** 2).sum(axis=1)
        cartesian_point_dist = np.sqrt(perpe_sqdist)

        cartesian_ori_dist = np.sqrt(((np.dot(
            A_rotate, (orientations[['X', 'Y']]).T).T - orientations[['X', 'Y']]) ** 2).sum(axis=1))

        # These are the coordinates of the data projected on the section
        cartesian_point = np.dot(A_rotate, (points[['X', 'Y']] - shift).T).T
        cartesian_ori = np.dot(A_rotate, (orientations[['X', 'Y']] - shift).T).T

        # Since we plot only the section we want the norm of those coordinates
        points['X'] = np.linalg.norm(cartesian_point, axis=1)
        orientations['X'] = np.linalg.norm(cartesian_ori, axis=1)
        x, y, Gx, Gy = 'X', 'Z', 'G_x', 'G_z'
    return Gx, Gy, cartesian_ori_dist, cartesian_point_dist, x, y


def _projection_params_topography(topography: Topography, orientations, points, projection_distance, topography_compression: int = 5000):
    decimation_aux = int(topography.values.shape[0] / topography_compression)
    tpp = topography.values[::decimation_aux + 1, :]
    cdist_sp = dd.cdist(
        XA=tpp,
        XB=points[['X', 'Y', 'Z']])
    cartesian_point_dist = (cdist_sp < projection_distance).sum(axis=0).astype(bool)
    cdist_ori = dd.cdist(
        XA=tpp,
        XB=orientations[['X', 'Y', 'Z']]
    )
    cartesian_ori_dist = (cdist_ori < projection_distance).sum(axis=0).astype(bool)
    x, y, Gx, Gy = 'X', 'Y', 'G_x', 'G_y'
    return Gx, Gy, cartesian_ori_dist, cartesian_point_dist, x, y
