﻿import numpy as np
import pyvista as pv
from vtkmodules.util.numpy_support import numpy_to_vtk
import matplotlib.colors as mcolors

from gempy.core.data.grid_modules import Topography
from gempy_viewer.core.scalar_data_type import TopographyDataType
from gempy_engine.core.data.raw_arrays_solution import RawArraysSolution
from gempy_viewer.modules.plot_3d.vista import GemPyToVista


def plot_topography_3d(
        gempy_vista: GemPyToVista,
        topography: Topography,
        solution: RawArraysSolution,
        topography_scalar_type: TopographyDataType,
        elements_colors: list[str],
        contours=True,
        **kwargs
):
    rgb = False

    xx, yy = np.meshgrid(topography.x, topography.y)

    grid = pv.StructuredGrid(yy, xx, topography.values_2d[:, :, 2])
    polydata = grid.extract_surface()

    geological_map: np.array = solution.geological_map
    is_geological_map = ~(geological_map is None or geological_map.size == 0)
    
    match topography_scalar_type, is_geological_map:
        case TopographyDataType.GEOMAP, True:
            colors_hex = elements_colors
            colors_rgb_ = [list(mcolors.hex2color(val)) for val in colors_hex]  # Convert hex to RGB using list comprehension

            colors_rgb = np.array(colors_rgb_) * 255  # Multiply by 255 to get RGB values in [0, 255]
            sel = np.round(geological_map).astype(int) - 1
            selected_colors = colors_rgb[sel]  # Use numpy advanced indexing to get the corresponding RGB values
            scalars_val = numpy_to_vtk(selected_colors, array_type=3)  # Convert to vtk array

            cm = mcolors.ListedColormap(elements_colors)
            rgb = True

            show_scalar_bar = False
            scalars = 'id'

        case TopographyDataType.SCALARS, True:
            raise NotImplementedError('Not implemented yet')
        case _:  # * Plot topography 
            scalars_val = topography.values[:, 2]
            cm = 'terrain'

            show_scalar_bar = True
            scalars = 'height'

    polydata['id'] = scalars_val
    polydata['height'] = topography.values[:, 2]

    topography_actor = gempy_vista.p.add_mesh(
        polydata,
        scalars=scalars,
        cmap=cm,
        rgb=rgb,
        show_scalar_bar=False,
        **kwargs
    )

    if contours is True:
        contours = polydata.contour(scalars='height')
        contours_actor = gempy_vista.p.add_mesh(contours, color="white", line_width=3)

        gempy_vista.surface_poly['topography'] = polydata
        gempy_vista.surface_poly['topography_cont'] = contours
        gempy_vista.surface_actors["topography"] = topography_actor
        gempy_vista.surface_actors["topography_cont"] = contours_actor
    return topography_actor
