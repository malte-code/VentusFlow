"""
This script processes input data from a JSON file for an OpenFOAM simulation, 
generates necessary configuration files, and prepares the simulation environment.
The script performs the following steps:
1. Loads the JSON file containing simulation data.
2. Extracts values required for OpenFOAM calculations.
3. Converts wind direction from radians to degrees.
4. Calculates the actual width and height of the simulation area.
5. Computes the scaling factor for the transformPoints utility.
6. Calculates the bounding box for topoSetDict.refine1 to refine3.
7. Generates the topoSetDict.windturbines file for wind turbine placement.
8. Creates the Allpre script to prepare the grid for the offshore wind park simulation.
9. Generates topoSetDict and refineMeshDict files for mesh refinement.

The script expects the JSON file path as a command-line argument and outputs the generated files in the same directory as the JSON file.

Generated files and their locations:
1. `topoSetDict.windturbines` - Located in the same directory as the JSON file.
2. `Allpre` - Located in the same directory as the JSON file.
3. `topoSetDict.refine1`, `topoSetDict.refine2`, `topoSetDict.refine3` - Located in the same directory as the JSON file.
4. `refineMeshDict.refine1`, `refineMeshDict.refine2`, `refineMeshDict.refine3` - Located in the same directory as the JSON file.
"""

# LIB
#------------------------------------------------
# Standard library
import json
import sys
import os
import math
#from dataclasses import dataclass
# Third-party libraries (currently not used)
#import numpy

# Neue globale Hilfsfunktionen für Polygonüberlappung und Gruppierung

def point_in_poly(x, y, poly, tol=1e-9):
    # Ray-casting algorithm with tolerance for testing if a point is inside a polygon.
    # If the point lies within tol of any edge or vertex, it is considered inside.
    if isinstance(poly, dict) and "coordinates" in poly:
        poly = poly["coordinates"]
    inside = False
    n = len(poly)
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        # Check if the point coincides with a vertex (within tolerance)
        if abs(x - p1x) < tol and abs(y - p1y) < tol:
            return True
        # Check if the horizontal ray crosses the edge
        if ((p1y > y) != (p2y > y)):
            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y + 1e-12) + p1x
            # If the point is nearly on the edge, consider it inside.
            if abs(x - xinters) < tol:
                return True
            if x < xinters - tol:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def polygons_overlap(poly1, poly2, tol=1e-9):
    """
    Returns True if poly1 and poly2 overlap significantly.
    This implementation uses bounding boxes. You can replace it with a more accurate method if needed.
    """
    def polygon_bbox(poly):
        xs = [pt[0] for pt in poly["coordinates"]]
        ys = [pt[1] for pt in poly["coordinates"]]
        return min(xs), min(ys), max(xs), max(ys)
    
    def bbox_intersection_area(b1, b2):
        x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
        y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
        return x_overlap * y_overlap

    b1 = polygon_bbox(poly1)
    b2 = polygon_bbox(poly2)
    inter_area = bbox_intersection_area(b1, b2)
    area1 = polygon_area(poly1)
    return inter_area > tol * area1

def polygon_area(poly):
    # Uses the shoelace formula.
    coords = poly["coordinates"]
    area = 0.0
    n = len(coords)
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0

def group_overlapping_polys(polys, tol=1e-9):
    """
    Groups polygons into clusters where polygons overlap.
    
    Parameters:
        polys (list): List of polygon dictionaries. Each dictionary should have a "coordinates" key.
        tol (float): Tolerance factor for determining overlap.
        
    Returns:
        list: A list of groups, where each group is a list of polygons that overlap.
    """
    n = len(polys)
    graph = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if polygons_overlap(polys[i], polys[j], tol):
                graph[i].append(j)
                graph[j].append(i)
    
    visited = [False] * n
    groups = []

    def dfs(idx, group):
        visited[idx] = True
        group.append(polys[idx])
        for neighbor in graph[idx]:
            if not visited[neighbor]:
                dfs(neighbor, group)

    for i in range(n):
        if not visited[i]:
            group = []
            dfs(i, group)
            groups.append(group)
    return groups

# Simulation Data
#------------------------------------------------
json_filename = 'simulation_parameters.json'    ###Make sure this is referenzed correctly

def get_simulation_data(json_file_path=None):
    """
    Load simulation data from a JSON file.
    If no path is provided, defaults to 'simulation_parameters.json' located in the same directory as this script.
    """

    if json_file_path is None:
        json_file_path = os.path.join(os.path.dirname(__file__), json_filename)

    if not os.path.exists(json_file_path):
        print(f"Fehler: Datei {json_file_path} nicht gefunden!")
        sys.exit(1)

    with open(json_file_path, 'r') as file:
        simulation_data = json.load(file)
    return simulation_data

# ROOT-Ordner
#------------------------------------------------
def get_case_folder():
    simulation_data = get_simulation_data()
    try:
        root_case_folder = os.path.join(os.path.dirname(__file__), '..', '..', simulation_data["rootFolder"])
    except KeyError:
        print("Fehler: 'rootFolder' fehlt in der JSON-Datei!")
        root_folder_new = os.path.join(os.path.dirname(__file__), '..', '..', "newCase")
        print(f"Setze 'rootFolder' auf: {root_folder_new}")
    return os.path.abspath(root_case_folder.strip("'\""))

# Simulation Area
#------------------------------------------------
class SimulationArea:
    rotation_angle_rad: float = 0.0
    rotation_angle_deg: float = 0.0
    sin_rotation: float = 0.0
    cos_rotation: float = 0.0
    center: tuple = (0.0, 0.0)
    corner_points: list = None
    width: float = 0.0
    depth: float = 0.0

    def __init__(self, sim_area_data):
        self.rotation_angle_rad = sim_area_data["rotationAngle"]
        self.rotation_angle_deg = math.degrees(self.rotation_angle_rad)
        self.sin_rotation = math.sin(self.rotation_angle_rad)
        self.cos_rotation = math.cos(self.rotation_angle_rad)

        self.center = tuple(map(float, sim_area_data["center"]))

        self.coordinates = [tuple(map(float, point)) for point in sim_area_data["coordinates"]]
        
        self.width = round(sim_area_data["dimensions"]["width"], 0)
        self.depth = round(sim_area_data["dimensions"]["depth"], 0)

    @staticmethod
    def getSimulationArea():
        simulation_data = get_simulation_data()
        # Expects a JSON structure with a "simulationArea" key.
        return SimulationArea(simulation_data["simulationArea"])

# Wake Regions
# ------------------------------------------------
class WakeRegion:
    id: str
    coordinates: tuple
    center: tuple = None  

    def __init__(self, id, coordinates, center=None):
        self.id = id
        self.coordinates = [tuple(map(float, point)) for point in coordinates]
        self.center = center

    @staticmethod
    def getWakeRegions():
        simulation_data = get_simulation_data()
        # Return wakeRegions from JSON directly. Expect each region to have "id", "coordinates", and optionally "center"
        return simulation_data["wakeRegions"]

    # New static method replacing overlapping regions with subdivided ones.
    @staticmethod
    def getSubdividedWakeRegions():
        """
        Loads original wake regions, subdivides them via subdivide_rectangles,
        and adds unique wake ids to the subdivided regions.
        """
        subdivided = WakeRegion.subdivide_rectangles()
        return subdivided  # id assignment now happens in subdivide_rectangles

    @staticmethod
    def subdivide_rectangles(tol=1e-9):
       # option 2: disabled ()
        area_tolerance = 999


        ## Load the simulation data
            # Get the rotation angle (in radians) from the simulation area
        angle_rad = SimulationArea.getSimulationArea().rotation_angle_rad

        # Load the wake regions from the simulation data
        wakeRegions = WakeRegion.getWakeRegions()
        # Retrieve the turbine coordinates (for later ID assignment)
        turbines = WindTurbines.getTurbines()


        ## De-rotate the wake regions to align with the coordinate system
        def de_rotate_wake_regions(wakeRegions, angle_rad):
            theta = -angle_rad  # Use negative angle to de-rotate
            de_rotated_polygons = []

            for region in wakeRegions:
                new_coords = []
                for x, y in region["coordinates"]:
                    x_new = x * math.cos(theta) - y * math.sin(theta)
                    y_new = x * math.sin(theta) + y * math.cos(theta)
                    new_coords.append((x_new, y_new))

                de_rotated_polygons.append({
                    "id": region["id"],
                    "coordinates": new_coords,
                    "center": region["center"]
                })
                
            return de_rotated_polygons
        de_rotated_polygons = de_rotate_wake_regions(wakeRegions, angle_rad)

        ## Helper functions for polygon operations
        ##############################################################

        def polygon_bbox(poly):
            # returns (xmin, ymin, xmax, ymax) for a polygon defined as a list of (x,y) points or a dict with "coordinates"
            if isinstance(poly, dict) and "coordinates" in poly:
                poly = poly["coordinates"]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            return min(xs), min(ys), max(xs), max(ys)

        def bbox_intersection_area(b1, b2):
            # computes the overlap area of two axis-aligned bounding boxes b1 and b2
            x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
            return abs(x_overlap * y_overlap)

        def polygon_area(poly):
                #The shoelace formula, also known as Gauss's area formula and the surveyor's formula, is a mathematical algorithm to determine the area of a simple polygon whose vertices are described by their Cartesian coordinates in the plane. It is called the shoelace formula because of the constant cross-multiplying for the coordinates making up the polygon, like threading shoelaces. It has applications in surveying and forestry, among other areas.
            # If poly is a dictionary with coordinates, extract them
            if isinstance(poly, dict) and "coordinates" in poly:
                poly = poly["coordinates"]
            # area computed using the shoelace formula
            area = 0.0
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i+1) % n]
                area += x1 * y2 - x2 * y1
            return abs(area) / 2.0
        
        def point_in_poly(x, y, poly, tol=1e-9):
            # Ray-casting algorithm with tolerance for testing if a point is inside a polygon.
            # If the point lies within tol of any edge or vertex, it is considered inside.
            if isinstance(poly, dict) and "coordinates" in poly:
                poly = poly["coordinates"]
            inside = False
            n = len(poly)
            p1x, p1y = poly[0]
            for i in range(1, n + 1):
                p2x, p2y = poly[i % n]
                # Check if the point coincides with a vertex (within tolerance)
                if abs(x - p1x) < tol and abs(y - p1y) < tol:
                    return True
                # Check if the horizontal ray crosses the edge
                if ((p1y > y) != (p2y > y)):
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y + 1e-12) + p1x
                    # If the point is nearly on the edge, consider it inside.
                    if abs(x - xinters) < tol:
                        return True
                    if x < xinters - tol:
                        inside = not inside
                p1x, p1y = p2x, p2y
            return inside

        def polygon_center(poly):
            # Calculate the centroid of a polygon            
            poly = poly["coordinates"]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            x_center = sum(xs) / len(xs)
            y_center = sum(ys) / len(ys)
            return x_center, y_center
        
        def do_polys_overlap(poly1, poly2, tol=1e-9):
            """
            Check if any point in poly2 is inside poly1.
            """
            for x, y in poly2["coordinates"]:
                if point_in_poly(x, y, poly1, tol):
                    return True
            return False

        def polygons_overlap(poly1, poly2, tol=1e-9):
            """
            Returns True if poly1 and poly2 overlap beyond a tolerance based on bounding boxes.
            """

            b1 = polygon_bbox(poly1)
            b2 = polygon_bbox(poly2)
            inter_area = bbox_intersection_area(b1, b2)
            area1 = polygon_area(poly1)
            return inter_area > tol * area1
        
        ## ALGORITHM 1: Find clusters of overlapping polygons.
        ############################################################

        def find_clusters(polygons, tol=1e-9, area_tolerance=0.8):
            n = len(polygons)
            graph = {i: [] for i in range(n)}
            for i in range(n):
                for j in range(i + 1, n):
                    if polygons_overlap(polygons[i], polygons[j], tol):
                        graph[i].append(j)
                        graph[j].append(i)

            visited = [False] * n
            groups = []

            def dfs(idx, group):
                visited[idx] = True
                group.append(polygons[idx])
                for neighbor in graph[idx]:
                    if not visited[neighbor]:
                        dfs(neighbor, group)

            for i in range(n):
                if not visited[i]:
                    group = []
                    dfs(i, group)
                    groups.append(group)

            # Calculate a bounding box for each group and add id and center.
            groups_bbox = []
            region_count = 1
            for group in groups:
                xs = []
                ys = []
                zs = []
                # Sum areas of all polygons in the group.
                sum_area = 0
                for poly in group:
                    for pt in poly["coordinates"]:
                        xs.append(pt[0])
                        ys.append(pt[1])
                    sum_area += polygon_area(poly)
                    # Collect z from center if available.
                    if "center" in poly and len(poly["center"]) >= 3:
                        zs.append(poly["center"][2])
                bx_min = min(xs)
                bx_max = max(xs)
                by_min = min(ys)
                by_max = max(ys)
                bbox_area = (bx_max - bx_min) * (by_max - by_min)
                # Compute the center: average the x and y bounds and the average z if available.
                center_x = (bx_min + bx_max) / 2.0
                center_y = (by_min + by_max) / 2.0
                center_z = sum(zs) / len(zs) if zs else 0

                bbox_polygon = [(bx_min, by_min), (bx_max, by_min), (bx_max, by_max), (bx_min, by_max)]
                # If the bbox area is not more than (1+area_tolerance) times the sum of poly areas, return bbox;
                # otherwise, set the bbox for this group to False.
                if bbox_area <= (1 + area_tolerance) * sum_area:
                    groups_bbox.append({
                        'id': f'WakeRegion_{region_count}',
                        'coordinates': bbox_polygon,
                        'center': [center_x, center_y, center_z]
                    })
                else:
                    groups_bbox.append(False)
                region_count += 1

            return groups_bbox
        
        poly_clusters = find_clusters(de_rotated_polygons, tol, area_tolerance)
        
        if all(cluster != False for cluster in poly_clusters):
            wake_regions = de_rotate_wake_regions(poly_clusters, -angle_rad)
            
            return wake_regions
        
        else:

            ## ALGORITHM 2: Split polygons into overlapping and non-overlapping groups. subdivide rectangles. reunion of polygons (prioritieses Turbine_Regions)
            ## not yet implemented: check if Turbine_Regions are big enough for ALM Model, reunion of left WakeRegions, if TurbineRegion cant union with adjacent WakeRegions anymore
            #############################################################

            # split polygons into overlapping and non-overlapping groups.
            def split_polygons_by_overlap(polygons, tol=1e-9):
                """
                Splits a list of polygons into overlapping and non-overlapping groups.
                
                Parameters:
                    polygons (list): List of polygon dictionaries with a "coordinates" key.
                    tol (float): Tolerance for comparison of intersection area relative to polygon area.
                    
                Returns:
                    tuple: (overlapping_polys, non_overlapping_polys)
                """
                overlapping_polys = []
                non_overlapping_polys = []
                for i, poly in enumerate(polygons):
                    overlap_found = False
                    area_poly = polygon_area(poly)
                    bbox1 = polygon_bbox(poly)
                    for j, other in enumerate(polygons):
                        if i == j:
                            # Skip further processing for this condition
                            pass
                        bbox2 = polygon_bbox(other)
                        inter_area = bbox_intersection_area(bbox1, bbox2)
                        if inter_area > tol * area_poly:
                            overlap_found = True
                            break
                    if overlap_found:
                        overlapping_polys.append(poly)

                    else:
                        non_overlapping_polys.append(poly)
                return overlapping_polys, non_overlapping_polys

            # Call the function to define overlapping and non-overlapping polygons
            overlapping_polys, non_overlapping_polys = split_polygons_by_overlap(de_rotated_polygons, tol)

            def generate_candidate_cells(overlapping_polys, point_in_poly):
                """
                Generates candidate grid cells from overlapping polygons.
                A cell is not added if it overlaps with a previously added cell.
                """
                tol = 1e-3
                candidate_cells = []

                def cell_center(cell):
                    xs = [pt[0] for pt in cell]
                    ys = [pt[1] for pt in cell]
                    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0

                def cells_overlap(cell1, cell2):
                    # Calculate bounding boxes for cell1 and cell2
                    xs1 = [pt[0] for pt in cell1]
                    ys1 = [pt[1] for pt in cell1]
                    xs2 = [pt[0] for pt in cell2]
                    ys2 = [pt[1] for pt in cell2]
                    x1_min, x1_max = min(xs1), max(xs1)
                    y1_min, y1_max = min(ys1), max(ys1)
                    x2_min, x2_max = min(xs2), max(xs2)
                    y2_min, y2_max = min(ys2), max(ys2)
                    # Check for overlap based on bounding boxes
                    overlap_x = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
                    overlap_y = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
                    return (overlap_x > tol) and (overlap_y > tol)

                for i in range(len(overlapping_polys)):
                    polygon = overlapping_polys[i]

                    grid_x = set()
                    grid_y = set()

                    for x, y in polygon["coordinates"]:
                        grid_x.add(x)
                        grid_y.add(y)

                    for j in range(len(overlapping_polys)):
                        if i == j:
                            continue
                        other_polygon = overlapping_polys[j]
                        for x, y in other_polygon["coordinates"]:
                            if point_in_poly(x, y, polygon):
                                grid_x.add(x)
                                grid_y.add(y)

                    sorted_grid_x = sorted(grid_x)
                    sorted_grid_y = sorted(grid_y)
                    for k in range(len(sorted_grid_x) - 1):
                        for l in range(len(sorted_grid_y) - 1):
                            cell = [
                                (sorted_grid_x[k], sorted_grid_y[l]),
                                (sorted_grid_x[k+1], sorted_grid_y[l]),
                                (sorted_grid_x[k+1], sorted_grid_y[l+1]),
                                (sorted_grid_x[k], sorted_grid_y[l+1])
                            ]
                            center_x, center_y = cell_center(cell)
                            cell_dict = {
                                'id': polygon['id'],
                                'coordinates': cell,
                                'center': [center_x, center_y, 0]  # Assuming z-coordinate is 0 for 2D cells
                            }
                            if point_in_poly(center_x, center_y, polygon):
                                x_diff = abs(cell[1][0] - cell[0][0])
                                y_diff = abs(cell[2][1] - cell[0][1])
                                if x_diff > tol and y_diff > tol:
                                    # Check if new cell overlaps with any existing candidate cell
                                    overlap_found = False
                                    for existing in candidate_cells:
                                        if cells_overlap(existing['coordinates'], cell):
                                            overlap_found = True
                                            break
                                    if not overlap_found:
                                        candidate_cells.append(cell_dict)
                return candidate_cells
            
            # Call function to define candidate_cells for each polygon individually.
            candidate_cells = generate_candidate_cells(overlapping_polys, point_in_poly)

            candidate_cells = candidate_cells + non_overlapping_polys

            def augment_candidate_cells(candidate_cells, turbines, theta, point_in_poly):
                """
                Augments candidate cells by assigning an id based on turbine inclusion or wake region.
                
                Parameters:
                    candidate_cells (list): List of candidate cells (each cell is a list of (x,y) tuples).
                    turbines (list): List of tuples (turbine_id, (x,y)).
                    theta (float): De-rotation angle in radians.
                    de_rotated_polygons (list): List of de-rotated wake region polygons (each a dict with key "id" and "coordinates").
                    point_in_poly (function): Function to test if a point is inside a polygon.
                    
                Returns:
                    list: The augmented candidate cells with assigned id, original coordinates, and center.
                """
                for cell in candidate_cells:
                    # Check if any turbine lies inside the cell after de-rotation
                    for turbine in turbines:
                        turbine_id = turbine['id']
                        tx, ty = turbine['coordinates']
                        tx_rot = tx * math.cos(theta) - ty * math.sin(theta)
                        ty_rot = tx * math.sin(theta) + ty * math.cos(theta)
                        if point_in_poly(tx_rot, ty_rot, cell):
                            cell['id'] = turbine_id
                return candidate_cells

            # Update candidate_cells by calling the function
            candidate_cells = augment_candidate_cells(candidate_cells, turbines, -angle_rad, point_in_poly)
            

            def merge_rectangles(candidate_cells, merge_id1, merge_id2, direction="vertical"):
                candites_merge = []
                tol = 1e-9
                if direction not in ("vertical", "horizontal"):
                    raise ValueError("direction must be either 'vertical' or 'horizontal'")
                def get_bounds(cell):
                    xs = [pt[0] for pt in cell['coordinates']]
                    ys = [pt[1] for pt in cell['coordinates']]
                    return min(xs), max(xs), min(ys), max(ys)
                def try_merge(master, slave, dirn):
                    m_xmin, m_xmax, m_ymin, m_ymax = get_bounds(master)
                    s_xmin, s_xmax, s_ymin, s_ymax = get_bounds(slave)
                    vertical_possible = False
                    horizontal_possible = False
                    if abs(m_xmin - s_xmin) < tol and abs(m_xmax - s_xmax) < tol:
                        if abs(m_ymax - s_ymin) < tol or abs(m_ymin - s_ymax) < tol:
                            vertical_possible = True
                    if abs(m_ymin - s_ymin) < tol and abs(m_ymax - s_ymax) < tol:
                        if abs(m_xmax - s_xmin) < tol or abs(m_xmin - s_xmax) < tol:
                            horizontal_possible = True
                    if (vertical_possible and horizontal_possible) and step1:
                        new_ymin = min(m_ymin, s_ymin)
                        new_ymax = max(m_ymax, s_ymax)
                        return {
                            'id': master['id'],
                            'coordinates': [(m_xmin, new_ymin), (m_xmax, new_ymin),
                                            (m_xmax, new_ymax), (m_xmin, new_ymax)],
                            'center': [(m_xmin + m_xmax) / 2.0, (new_ymin + new_ymax) / 2.0]
                        }
                    elif vertical_possible and dirn == "vertical":
                        new_ymin = min(m_ymin, s_ymin)
                        new_ymax = max(m_ymax, s_ymax)
                        return {
                            'id': master['id'],
                            'coordinates': [(m_xmin, new_ymin), (m_xmax, new_ymin),
                                            (m_xmax, new_ymax), (m_xmin, new_ymax)],
                            'center': [(m_xmin + m_xmax) / 2.0, (new_ymin + new_ymax) / 2.0]
                        }
                    elif horizontal_possible and dirn == "horizontal":
                        new_xmin = min(m_xmin, s_xmin)
                        new_xmax = max(m_xmax, s_xmax)
                        return {
                            'id': master['id'],
                            'coordinates': [(new_xmin, m_ymin), (new_xmax, m_ymin),
                                            (new_xmax, m_ymax), (new_xmin, m_ymax)],
                            'center': [(new_xmin + new_xmax) / 2.0, (m_ymin + m_ymax) / 2.0]
                        }
                    return None
                if merge_id1 == merge_id2:
                    group = [cell.copy() for cell in candidate_cells if cell['id'].startswith(merge_id1)]
                    others = [cell.copy() for cell in candidate_cells if not cell['id'].startswith(merge_id1)]
                    changed = True
                    while changed:
                        changed = False
                        new_group = []
                        used = [False] * len(group)
                        for i in range(len(group)):
                            if used[i]:
                                continue
                            master = group[i]
                            for j in range(i + 1, len(group)):
                                if used[j]:
                                    continue
                                slave = group[j]
                                merged = try_merge(master, slave, direction)
                                if merged:
                                    master = merged
                                    used[j] = True
                                    changed = True
                            new_group.append(master)
                        group = new_group
                    return others + group
                else:
                    masters = [cell.copy() for cell in candidate_cells if cell['id'].startswith(merge_id1)]
                    slaves = [cell.copy() for cell in candidate_cells if cell['id'].startswith(merge_id2)]
                    others = [cell.copy() for cell in candidate_cells if not (cell['id'].startswith(merge_id1) or cell['id'].startswith(merge_id2))]
                    merged_occurred = True
                    step1 = False
                    while merged_occurred:
                        merged_occurred = False
                        masters = sorted(masters, key=lambda cell: polygon_area(cell['coordinates']))
                        slaves = sorted(slaves, key=lambda cell: polygon_area(cell['coordinates']))
                        for m_idx, master in enumerate(masters):
                            for s_idx, slave in enumerate(slaves):
                                step1 = True
                                candidate = try_merge(master, slave, direction)
                                if candidate:
                                    masters[m_idx] = candidate
                                    del slaves[s_idx]
                                    merged_occurred = True
                                    break
                            if merged_occurred:
                                break
                        if merged_occurred:
                            continue
                        opp_direction = "horizontal" if direction == "vertical" else "vertical"
                        adjacent_merge_occurred = False
                        step1 = False
                        for m_idx, master in enumerate(masters):
                            adjacent_slaves = []
                            for slave in slaves:
                                count = sum(1 for pt in slave['coordinates'] if point_in_poly(pt[0], pt[1], master))
                                if count >= 2:
                                    adjacent_slaves.append(slave)
                            if len(adjacent_slaves) >= 2:
                                adjacent_slaves = sorted(adjacent_slaves, key=lambda cell: polygon_area(cell['coordinates']))
                                merged_candidate = None
                                merged_slave_ids = []
                                for i in range(len(adjacent_slaves)):
                                    for j in range(i + 1, len(adjacent_slaves)):
                                        candites_merge.append(adjacent_slaves[i])
                                        candites_merge.append(adjacent_slaves[j])
                                        candidate_adj = try_merge(adjacent_slaves[i], adjacent_slaves[j], opp_direction)
                                        if candidate_adj:
                                            merged_candidate = candidate_adj
                                            merged_slave_ids = [adjacent_slaves[i]['id'], adjacent_slaves[j]['id']]
                                            break
                                    if merged_candidate:
                                        break
                                if merged_candidate:
                                    candidate_master = try_merge(master, merged_candidate, direction)
                                    if candidate_master:
                                        masters[m_idx] = candidate_master
                                        slaves = [slave for slave in slaves if slave['id'] not in merged_slave_ids]
                                        adjacent_merge_occurred = True
                                        break
                            if adjacent_merge_occurred:
                                break
                        if adjacent_merge_occurred:
                            continue
                        break
                    return others + masters + slaves
            
            subdivided_regions = merge_rectangles(candidate_cells, "Turbine", "Wake", direction="vertical")
            return subdivided_regions

# Turbinen-Parameter
#------------------------------------------------
class WindTurbines:
    id: str
    turbineType: str
    coordinates: tuple
    hubHeight: float = 0.0
    rotorRadius: float = 0.0
    tipSpeedRatio: float = 0.0
    sphereRadius: float = 0.0

    def __init__(self, id, turbineType, coordinates, hubHeight=0.0, rotorRadius=0.0, tipSpeedRatio=0.0, sphereRadius=0.0):
        self.id = id
        self.turbineType = turbineType
        self.coordinates = tuple(map(float, coordinates))
        self.hubHeight = hubHeight
        self.rotorRadius = rotorRadius
        self.tipSpeedRatio = tipSpeedRatio
        self.sphereRadius = sphereRadius

    @staticmethod
    def getTurbines():
        turbines_data = get_simulation_data().get("turbines", {})
        turbines_list = turbines_data.get("turbine", [])
        # Global turbine parameters for the entire turbines block
        fvOptionsTurbines = {
            "stallType": turbines_data.get("stallType", ""),
            "stallModel": turbines_data.get("stallModel", ""),
            "endEffects": turbines_data.get("endEffects", ""),
            "hubCheckbox": turbines_data.get("hubCheckbox", False),
            "towerCheckbox": turbines_data.get("towerCheckbox", False),
        }
        turbines = [
            {
                "id": turbine["id"],
                "turbineType": turbine.get("turbineType", ""),
                "coordinates": tuple(map(float, turbine["coordinates"])),
                "hubHeight": turbine.get("hubHeight", 0.0),
                "rotorRadius": turbine.get("rotorRadius", 0.0),
                "tipSpeedRatio": turbine.get("tipSpeedRatio", 0.0),
                "sphereRadius": turbine.get("sphereRadius", 0.0),
            }
            for turbine in turbines_list
        ]
        return {"turbines": turbines, "fvOptions": fvOptionsTurbines}

# Umgebungs-Parameter
#------------------------------------------------
class Environment:
    windSpeed: float = 0.0
    windDirectionRad: float = 0.0
    turbIntensity_inlet: float = 0.0
    profileHeights_inlet: list = []
    cellDensity: float = 0.0

    def __init__(self, simulation_data):
        environment = simulation_data["environment"]["wind"]
        self.windSpeed = environment["speed"]
        self.windDirectionRad = (environment["direction"])
        self.turbIntensity_inlet = environment["turbulenceIntensity"]
        self.profileHeights_inlet = environment["profileHeights"]
        self.cellDensity = simulation_data["environment"]["cellDensity"]

    @staticmethod
    def getEnvironment():
        simulation_data = get_simulation_data()
        return Environment(simulation_data)

# Solver-Parameter
#------------------------------------------------
class SolverParameters:
    startTime: float = 0.0
    endTime: float = 0.0
    deltaT: float = 0.0
    writeInterval: float = 0.0
    computeCores: int = 0

    def __init__(self, solver_data):
        self.startTime = solver_data["startTime"]
        self.endTime = solver_data["endTime"]
        self.deltaT = solver_data["deltaT"]
        self.writeInterval = solver_data["writeInterval"]
        self.computeCores = solver_data["computeCores"]

    @staticmethod
    def getSolverParameters():
        simulation_data = get_simulation_data()
        solver_data = simulation_data["Solver"]
        return SolverParameters(solver_data)

# find ideal dimension, as close to input as possible, inital values before refinements
#------------------------------------------------
def compute_mesh_parameters():
    sim_area = SimulationArea.getSimulationArea()
    environment = Environment.getEnvironment()
    """
    Compute meshing parameters from a SimulationArea instance and cellDensity.

    Parameters:
        sim_area (SimulationArea): Instance containing simulation area dimensions.
        cell_density (float): Cell density value from the simulation.

    Returns:
        dict: A dictionary with keys:
            scale, cell_size, xElem, yElem, zElem,
            xMin, xMax, xDepth, yMin, yMax, yWidth,
            zMin, zMax, zWidth.
    """

    # set default scale
    scale = 1
    # calc cell size for number of refinements (refine1, refine2, refine3, refineWakeRegions)
    # refine doubles the number of cells in each dimension
    cell_size = (1 / environment.cellDensity) * (2*2*2*2)  # base cell size

    # Use sim_area.depth for x-dimension and sim_area.width for y-dimension fiiting cell size
    xElem = math.ceil(sim_area.depth / cell_size)
    yElem = math.ceil(sim_area.width / cell_size)
    zElem = math.ceil(1000 / cell_size)
    # total cells before refinement
    total_cells = xElem * yElem * zElem

    # calc Depth Parameters (x)
    xMin = - (xElem / 2) * cell_size
    xMax = (xElem / 2) * cell_size
    xDepth = xMax - xMin

    # calc Width Parameters (y)
    yMin = - (yElem / 2) * cell_size
    yMax = (yElem / 2) * cell_size
    yWidth = yMax - yMin

    # calc Height Parameters (z)
    zMin = 0
    zMax = zElem * cell_size
    zHeight = zMax - zMin

    return {
        "scale": scale,
        "cell_size": cell_size,
        "xElem": xElem,
        "yElem": yElem,
        "zElem": zElem,
        "xMin": xMin,
        "xMax": xMax,
        "xDepth": xDepth,
        "yMin": yMin,
        "yMax": yMax,
        "yWidth": yWidth,
        "zMin": zMin,
        "zMax": zMax,
        "zHeight": zHeight
    }

# Initialize Objects
#------------------------------------------------




################################################
#------------------------------------------------
# PREPROCESSING Settings
#------------------------------------------------
################################################

#------------------------------------------------
# Allclean
#------------------------------------------------
def create_allclean_script():
    allclean_path = os.path.join(get_case_folder(), "Allclean")

    with open(allclean_path, 'w') as file:
        file.write("#!/bin/sh\n\n")
        file.write("### Script for cleaning the folder of the offshore wind park simulation\n")
        file.write("### HLRS, 2024-2025\n\n")

        file.write("rm log.* slurm.* \n")
        file.write("\n")
        file.write("# Lösche Ordner\n")
        file.write("rm -rf VTK constant/polyMesh processor*\n")    
        file.write("\n")
        file.write("find . -maxdepth 1 -type d -regextype posix-extended -regex '\\./[0-9]{1,5}' -exec rm -rf {} +\n")
        file.write("\n")
    # print(f"Allclean successfully created at: \n{allclean_path}")

create_allclean_script()

#------------------------------------------------
# Allpre
#------------------------------------------------

def create_allpre_script():
    allpre_path = os.path.join(get_case_folder(), "Allpre")

    with open(allpre_path, 'w') as file:
        file.write("#!/bin/sh\n\n")

        file.write("### Script for preparing the grid for the offshore wind park simulation\n")
        file.write("### HLRS, 2024-2025\n\n")

        file.write(". $WM_PROJECT_DIR/bin/tools/RunFunctions\n")
        file.write("\n")

        # Replace turbine_names loop with wake_names loop.
        # Original code:
        # turbine_names = [turbine[0] for turbine in WindTurbines.getTurbines().turbine_coordinates]
        wake_names = [wake["id"] for wake in WakeRegion.getSubdividedWakeRegions()]
        file.write("loopRefineMesh () {\n")
        file.write("    for SET in " + " ".join(wake_names) + " ; do\n")
        file.write("        sed -i \"0,/set [a-zA-Z0-9_]*/s//set ${SET}/\" system/refineMeshDict.wakeregions \n")
        # Update runApplication command to use wake_${SET} instead of windturbine_${SET}
        file.write("        runApplication -s wake_${SET} refineMesh -overwrite -dict system/refineMeshDict.wakeregions\n")
        file.write("    done\n")
        file.write("}\n\n")

        file.write("runApplication blockMesh -dict system/blockMeshDict\n")
        file.write("\n")
        # ------------------------------------------------
        # approx refine1 500m refine2 250m refine3 1000m
        file.write("runApplication -s refine1 topoSet -dict system/topoSetDict.refine1\n")
        file.write("runApplication -s refine1 refineMesh -overwrite -dict system/refineMeshDict.refine1\n")
        file.write("runApplication -s refine2 topoSet -dict system/topoSetDict.refine2\n")
        file.write("runApplication -s refine2 refineMesh -overwrite -dict system/refineMeshDict.refine2\n")
        file.write("runApplication -s refine3 topoSet -dict system/topoSetDict.refine3\n")
        file.write("runApplication -s refine3 refineMesh -overwrite -dict system/refineMeshDict.refine3\n")
        #------------------------------------------------


        file.write("\n")
        file.write("runApplication -s wakeregions topoSet -dict system/topoSetDict.wakeregions\n")
        file.write("loopRefineMesh\n")
        file.write("\n")

        file.write("\n")
        # rotate (rotation center alsways 0 0 0, beware of relative simulationarea position, its influencing rotation)
        file.write(f"runApplication -s iter1 transformPoints -rollPitchYaw '(0 0 {SimulationArea.getSimulationArea().rotation_angle_deg})'\n")
        # -rollPitchYaw <vector>

        #translate to actual position
        # file.write(f"runApplication -s iter2 transformPoints -translate '( {center_x} {center_y} 0)'\n\n")
        # -translate <vector>
        # Translate by specified <vector> before rotations
        # file.write("\n")
        # overwriting initial conditions
        # file.write("python createInletBoundaryData.py\n")
        file.write("\n")
        # Postprocessing Mesh
        ################################################
        # Option1: parallel VTK generation (conflicts with Allrun)
        # parallel VTK generation
        # file.write("runApplication decomposePar\n")
        # file.write("runParallel renumberMesh -overwrite \n")
        # file.write(f"mpirun -np {computeCores} foamToVTK -parallel \n")

        #Option2: serial VTK generation
        file.write("runApplication checkMesh\n")
        file.write("runApplication foamToVTK\n")
        file.write("\n")
        # prepare for Solver
        file.write("restore0Dir \n")
        file.write("runApplication decomposePar \n")
        file.write("runParallel renumberMesh -overwrite \n")

        #Check log.files
        file.write("grep -i 'error' log.* || echo 'no errors!' \n")

    # print(f"Allpre successfully created at: \n{allpre_path}")

create_allpre_script()


#------------------------------------------------
# blockMeshDict
#------------------------------------------------
def create_blockMeshDict():
    blockMeshDict_path = os.path.join(get_case_folder(), "system/blockMeshDict")
    meshParams = compute_mesh_parameters()
    with open(blockMeshDict_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n{\n")
        file.write("    version     2.0;\n")
        file.write("    format      ascii;\n")
        file.write("    class       dictionary;\n")
        file.write("    object      blockMeshDict;\n")
        file.write("}\n")
        file.write("// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n")

        file.write(f"scale {meshParams['scale']};\n\n")

        file.write(f"xMin {meshParams['xMin']};\n")
        file.write(f"xMax {meshParams['xMax']};\n")
        file.write(f"yMin {meshParams['yMin']};\n")
        file.write(f"yMax {meshParams['yMax']};\n")
        file.write(f"zMin {meshParams['zMin']};\n")
        file.write(f"zMax {meshParams['zMax']};\n\n")

        file.write(f"xElem {meshParams['xElem']};\n")
        file.write(f"yElem {meshParams['yElem']};\n")
        file.write(f"zElem {meshParams['zElem']};\n\n")
        file.write("vertices\n(\n")
        file.write("    ($xMin $yMin $zMin) // 0\n")
        file.write("    ($xMax $yMin $zMin) // 1\n")
        file.write("    ($xMax $yMax $zMin) // 2\n")
        file.write("    ($xMin $yMax $zMin) // 3\n")
        file.write("    ($xMin $yMin $zMax) // 4\n")
        file.write("    ($xMax $yMin $zMax) // 5\n")
        file.write("    ($xMax $yMax $zMax) // 6\n")
        file.write("    ($xMin $yMax $zMax) // 7\n")
        file.write(");\n\n")

        file.write("blocks\n(\n")
        file.write(f"    hex (0 1 2 3 4 5 6 7) ({meshParams['xElem']} {meshParams['yElem']} {meshParams['zElem']}) simpleGrading (1 1 1)\n")
        file.write(");\n\n")

        file.write("edges\n(\n);\n\n")

        file.write("boundary\n(\n")
        file.write("    outlet\n    {\n")
        file.write("        type patch;\n")
        file.write("        faces\n        (\n")
        file.write("            (0 3 4 7)\n")
        file.write("        );\n")
        file.write("    }\n\n")

        file.write("    inlet\n    {\n")
        file.write("        type patch;\n")
        file.write("        faces\n        (\n")
        file.write("            (1 2 5 6)\n")
        file.write("        );\n")
        file.write("    }\n\n")

        file.write("    bottom\n    {\n")
        file.write("        type wall;\n")
        file.write("        faces\n        (\n")
        file.write("            (0 1 2 3)\n")
        file.write("        );\n")
        file.write("    }\n\n")

        file.write("    top\n    {\n")
        file.write("        type patch;\n")
        file.write("        faces\n        (\n")
        file.write("            (4 5 6 7)\n")
        file.write("        );\n")
        file.write("    }\n\n")

        file.write("    side1\n    {\n")
        file.write("        type cyclic;\n")
        file.write("        neighbourPatch  side2;\n")
        file.write("        faces\n        (\n")
        file.write("            (0 1 4 5)\n")
        file.write("        );\n")
        file.write("    }\n\n")

        file.write("    side2\n    {\n")
        file.write("        type cyclic;\n")
        file.write("        neighbourPatch  side1;\n")
        file.write("        faces\n        (\n")
        file.write("            (2 3 6 7)\n")
        file.write("        );\n")
        file.write("    }\n")
        file.write(");\n\n")

        file.write("mergePatchPairs\n(\n);\n\n")

        file.write("// ************************************************************************* //\n")

    # print(f"blockMeshDict successfully created at: \n{blockMeshDict_path}")

create_blockMeshDict()

#------------------------------------------------
# 0.orig files
#------------------------------------------------
def create_nut_file():
    nut_path = os.path.join(get_case_folder(), "0.orig/nut")
    with open(nut_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n")
        file.write("{\n")
        file.write("    version     2.0;\n")
        file.write("    format      binary;\n")
        file.write("    arch        \"LSB;label=64;scalar=64\";\n")
        file.write("    class       volScalarField;\n")
        file.write("    location    \"0\";\n")
        file.write("    object      nut;\n")
        file.write("}\n")
        file.write("// ************************************************************************* //\n")
        file.write("\n")
        file.write("dimensions      [ 0 2 -1 0 0 0 0 ];\n")
        file.write("internalField   uniform 1e-08;\n")
        file.write("boundaryField\n")
        file.write("{\n")
        file.write("    inlet\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    outlet\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    bottom\n")
        file.write("    {\n")
        file.write("        type            atmNutkWallFunction;\n")
        file.write("        Cmu             0.09;\n")
        file.write("        kappa           0.41;\n")
        file.write("        E               9.8;\n")
        file.write("        z0              uniform 0.05;\n")
        file.write("        value           uniform 0;\n")
        file.write("    }\n")
        file.write("    top\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    side1\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("    side2\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("}\n")
        file.write("// ************************************************************************* //\n")

    # print(f"nut file successfully created at: \n{nut_path}")

def create_U_file():
    U_path = os.path.join(get_case_folder(), "0.orig/U")
    with open(U_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n")
        file.write("{\n")
        file.write("    version     2.0;\n")
        file.write("    format      binary;\n")
        file.write("    arch        \"LSB;label=64;scalar=64\";\n")
        file.write("    class       volVectorField;\n")
        file.write("    location    \"0\";\n")
        file.write("    object      U;\n")
        file.write("}\n")
        file.write("// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n")
        file.write("\n")
        file.write("dimensions      [ 0 1 -1 0 0 0 0 ];\n")
        file.write("#include \"$FOAM_CASE/system/initialConditions\"\n")
        file.write("internalField   uniform $UInitial;\n")
        file.write("boundaryField\n")
        file.write("{\n")
        file.write("    inlet\n")
        file.write("    {\n")
        file.write("        type            turbulentDigitalFilterInlet;\n")
        file.write("        value           uniform $UInitial;\n")
        file.write("        variant         digitalFilter;\n")
        file.write("        n               ( 10 100 );\n")
        file.write("        L               ( 100 20 20 20 20 20 60 20 20 );\n")
        file.write("        continuous      true;\n")
        file.write("        mean\n")
        file.write("        {\n")
        file.write("            type            mappedFile;\n")
        file.write("            mapMethod       nearest;\n")
        file.write("            fieldTable      UMean;\n")
        file.write("        }\n")
        file.write("        R\n")
        file.write("        {\n")
        file.write("            type            mappedFile;\n")
        file.write("            mapMethod       nearest;\n")
        file.write("            fieldTable      R;\n")
        file.write("        }\n")
        file.write("    }\n")
        file.write("    outlet\n")
        file.write("    {\n")
        file.write("        type            inletOutlet;\n")
        file.write("        inletValue      uniform ( 0 0 0 );\n")
        file.write("        value           uniform $UInitial;\n")
        file.write("    }\n")
        file.write("    bottom\n")
        file.write("    {\n")
        file.write("        type            noSlip;\n")
        file.write("    }\n")
        file.write("    top\n")
        file.write("    {\n")
        file.write("        type            slip;\n")
        file.write("    }\n")
        file.write("    side1\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("    side2\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("}\n")
        file.write("// ************************************************************************* //\n")

    # print(f"U file successfully created at: \n{U_path}")

def create_p_file():
    p_path = os.path.join(get_case_folder(), "0.orig/p")
    with open(p_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n")
        file.write("{\n")
        file.write("    version     2.0;\n")
        file.write("    format      binary;\n")
        file.write("    class       volScalarField;\n")
        file.write("    arch        \"LSB;label=32;scalar=64\";\n")
        file.write("    location    \"0\";\n")
        file.write("    object      p;\n")
        file.write("}\n")
        file.write("// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n")
        file.write("\n")
        file.write("dimensions      [0 2 -2 0 0 0 0];\n")
        file.write("internalField   uniform 0;\n")
        file.write("boundaryField\n")
        file.write("{\n")
        file.write("    inlet\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    outlet\n")
        file.write("    {\n")
        file.write("        type            fixedValue;\n")
        file.write("        value           uniform 0;\n")
        file.write("    }\n")
        file.write("    bottom\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    top\n")
        file.write("    {\n")
        file.write("        type            zeroGradient;\n")
        file.write("    }\n")
        file.write("    side1\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("    side2\n")
        file.write("    {\n")
        file.write("        type            cyclic;\n")
        file.write("    }\n")
        file.write("}\n")
        file.write("// ************************************************************************* //\n")

    # print(f"p file successfully created at: \n{p_path}")

# Call the functions
create_nut_file()
create_U_file()
create_p_file()

#------------------------------------------------
# initialConditions
#------------------------------------------------

def create_initial_conditions_file():
    environment = Environment.getEnvironment()
    simArea = SimulationArea.getSimulationArea()
    windTurbines = WindTurbines.getTurbines()
    # frontend cathesian coordiantes counterclockwise := rotationangle
    #             Norden (π/2)
    #               |
    #   Westen π ---+--- 0 Osten (0 rad)
    #               |
    #             Süden (3π/2)


    # openfoam meteo angle counterclockwise := meteoangle
    #             Norden (π/2)
    #               |
    #   Westen π ---+--- 0 Osten (0 rad)
    #               |
    #             Süden (3π/2)

    #transform coordiante system: shift pi; rotation clockwise -rotation
    meteoAngleRad =  simArea.rotation_angle_deg % (2 * math.pi)

    # Berechnung der ALM Turbinen-Referenzrichtung
    # ALM Turbinen-Referenzrichtung ist entgegengesetzt zur Windrichtung
    alm_x_axis = environment.windSpeed * math.cos(meteoAngleRad)
    alm_y_axis = environment.windSpeed * math.sin(meteoAngleRad)

    #wind zeigt in entgegengesetzte Richtung
    meteoAngleRad_wind = environment.windDirectionRad % (2 * math.pi)

    # Berechnung der Komponenten des Windvektors
    U_x_inital = environment.windSpeed * math.cos(meteoAngleRad_wind)
    U_y_inital = environment.windSpeed * math.sin(meteoAngleRad_wind)

    initialConditions_path = os.path.join(get_case_folder(), "system/initialConditions")
    with open(initialConditions_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n")
        file.write("\n")
        file.write("// Initial conditions of the offshore wind park simulation\n")
        file.write("// HLRS, 2022-2023\n")
        file.write("\n")
        file.write(f"WindSpeed       {environment.windSpeed};\n")
        file.write("\n")
        file.write(f"WindDirMeteoRad    {meteoAngleRad_wind};\n")
        file.write("\n")
        file.write(f"WindDirMeteoDeg    {math.degrees(environment.windDirectionRad)};\n")
        file.write("\n")
        file.write(f"// TurbineRefine Settings\n")
        file.write("\n")
        turbines_data = WindTurbines.getTurbines()
        file.write(f"sphereRadius    {turbines_data['turbines'][0]['sphereRadius']};\n")
        file.write("\n")
        file.write("\n")
        file.write("\n")
        file.write("\n")        
        file.write("// ************************************************************************* //\n")
        file.write("\n")
        file.write("// WindDirMeteo\n")
        file.write("UInitial\n")
        file.write("(\n")
        file.write(f"   {U_x_inital}\n")
        file.write(f"   {U_y_inital}\n")
        file.write("   0\n")
        file.write(");\n")
        file.write("\n")
        file.write("// TurbineAxis\n")
        file.write("axisInitial\n")
        file.write("(\n")
        file.write(f"   {alm_x_axis}\n")
        file.write(f"   {alm_y_axis}\n")
        file.write("   0\n")
        file.write(");\n")
        file.write("\n")
        file.write("// ************************************************************************* //\n")

    # print(f"initialConditions successfully created at: \n{initialConditions_path}")

create_initial_conditions_file()

#------------------------------------------------
# Inlet conditions
#------------------------------------------------

def create_inlet_conditions():
    environment = Environment.getEnvironment()
    turbines = WindTurbines.getTurbines()

    angle = environment.windDirectionRad
    # print(f"Inlet angle cos sin: {math.cos(angle)} {math.sin(angle)}")

    k_roughness_inlet = 0.41          # -
    z_zero_inlet = 0.05               # [m]
#TODO: ustar for multiple hubheights    
    # Berechnung von ustar
    ustar = environment.windSpeed * k_roughness_inlet / math.log((turbines['turbines'][0]['hubHeight'] + z_zero_inlet) / z_zero_inlet)                  # [m/s]
    # ustar = 0 * k_roughness_inlet / math.log((hubHeight + z_zero_inlet) / z_zero_inlet)                  # [m/s]

    Ux_inlet = []
    Uy_inlet = []
    
    Rxx_inlet = []
    Ryy_inlet = []
    Rzz_inlet = []

    pointsBuffer = "(\n"
    UBuffer = "(\n"
    RBuffer = "(\n"

    for point in environment.profileHeights_inlet:
        pointsBuffer += f"( 0 0 {point} )\n"
        U = ustar / k_roughness_inlet * math.log((point + z_zero_inlet) / z_zero_inlet)
        Ux_inlet = U * math.cos(angle)
        Uy_inlet = U * math.sin(angle)
        Uz_inlet = 0
        UBuffer += f"( {Ux_inlet} {Uy_inlet} {Uz_inlet} )\n"
        Rxx_inlet = (U * (environment.turbIntensity_inlet / 100)) ** 2
        Ryy_inlet = (U * (environment.turbIntensity_inlet / 100)) ** 2
        Rzz_inlet = (U * (environment.turbIntensity_inlet / 100)) ** 2
        RBuffer += f"( {Rxx_inlet} 0 0 {Ryy_inlet} 0 {Rzz_inlet} )\n"


    pointsBuffer += ")\n"
    UBuffer += ")\n"
    RBuffer += ")\n"

    outFiles = ("constant/boundaryData/inlet/points", "constant/boundaryData/inlet/0/UMean", "constant/boundaryData/inlet/0/R")

    inlet_path = os.path.join(get_case_folder(), 'constant/boundaryData/inlet')
    inlet_0_path = os.path.join(inlet_path, '0')

    if not os.path.exists(inlet_path):
        os.makedirs(inlet_path)
    if not os.path.exists(inlet_0_path):
        os.makedirs(inlet_0_path)

    for outFile in outFiles:
        outFile_path = os.path.join(get_case_folder(), outFile)
        with open(outFile_path, 'w') as f:
            if outFile == "constant/boundaryData/inlet/points":
                f.write(pointsBuffer)
            if outFile == "constant/boundaryData/inlet/0/UMean":
                f.write(UBuffer)
            if outFile == "constant/boundaryData/inlet/0/R":
                f.write(RBuffer)
            # print(f"{outFile_path} has been written")

create_inlet_conditions()

#------------------------------------------------
# topoSetDict.refine1 bis 3 und refineMeshDict.refine1 bis 3
#------------------------------------------------

def create_refine_files():
    turbines = WindTurbines.getTurbines()
    meshParams = compute_mesh_parameters()
    refineRegionsnames = ["refineRegion1", "refineRegion2", "refineH3"]
    refineRegionIndex = ["refine1", "refine2", "refine3"]
    refine1height = math.ceil(meshParams['zMax'])
    refine2height = math.ceil(meshParams['zMax'] / 2)
    refine3height = max(t['hubHeight'] for t in turbines['turbines']) + (max(t['sphereRadius'] for t in turbines['turbines']) * max(t['rotorRadius'] for t in turbines['turbines']))
    print("Refine heights:", refine1height, refine2height, refine3height)
    refineHeights = [refine1height, refine2height, refine3height]

    for i, region in enumerate(refineRegionsnames):
        # topoSetDict.refine
        topoSetDict_refine_path = os.path.join(get_case_folder(), f"system/topoSetDict.{refineRegionIndex[i]}")

        with open(topoSetDict_refine_path, 'w') as file:
            file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
            file.write("| =========                 |                                                 |\n")
            file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
            file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
            file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
            file.write("|    \\/     M anipulation  |                                                 |\n")
            file.write("\\*---------------------------------------------------------------------------*/\n")
            file.write("FoamFile\n{\n")
            file.write("    version     2.0;\n")
            file.write("    format      ascii;\n")
            file.write("    class       dictionary;\n")
            file.write("    object      topoSetDict;\n")
            file.write("}\n\n")
            
            file.write("// ************************************************************************* //\n")
            
            # Füge die berechneten Box-Koordinaten hier ein
            file.write("\n")
            file.write("actions\n")
            file.write("(\n")
            file.write("    {\n")
            file.write(f"        name        {region};\n")
            file.write("        type        cellSet;\n")
            file.write("        action      new;\n")
            file.write("        source      boxToCell;\n")
            file.write(f"        box ({meshParams['xMin']} {meshParams['yMin']} 0) ({meshParams['xMax']} {meshParams['yMax']} {refineHeights[i]});\n")
            file.write("    }\n")
            file.write(");\n")
            file.write("// ************************************************************************* //\n")

        # print(f"topoSetDict.{region} created at: \n{topoSetDict_refine_path}")

        # `refineMeshDict.refine1` generieren
        refineMeshDict_refine_path = os.path.join(get_case_folder(), f"system/refineMeshDict.{refineRegionIndex[i]}")

        with open(refineMeshDict_refine_path, 'w') as file:
            file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
            file.write("| =========                 |                                                 |\n")
            file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
            file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
            file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
            file.write("|    \\/     M anipulation  |                                                 |\n")
            file.write("\\*---------------------------------------------------------------------------*/\n")
            file.write("FoamFile\n{\n")
            file.write("    version     2.0;\n")
            file.write("    format      ascii;\n")
            file.write("    class       dictionary;\n")
            file.write("    object      refineMeshDict;\n")
            file.write("}\n\n")
            
            file.write("// ************************************************************************* //\n")
            file.write("\n")
            file.write(f"set             {region};\n")
            file.write("\n")
            file.write("coordinateSystem global;\n")
            file.write("\n")
            file.write("globalCoeffs\n{\n")
            # Füge die berechneten tan1 und tan2 Vektoren für die gedrehte Ausrichtung des KOS hier ein
            #calc is needed if roation is befor refine
            # file.write(f"    tan1            ( {cos_rotation_simArea} {sin_rotation_simArea} 0 );\n")
            # file.write(f"    tan2            ( {-sin_rotation_simArea} {cos_rotation_simArea} 0 );\n")

            file.write("    tan1            ( 1 0 0 );\n")
            file.write("    tan2            ( 0 1 0 );\n")

            file.write("}\n")
            file.write("\n")
            file.write("directions\n(\n")
            file.write("    tan1\n")
            file.write("    tan2\n")
            file.write("    normal\n")
            file.write(");\n")
            file.write("\n")
            file.write("useHexTopology  yes;\n")
            file.write("geometricCut    no;\n")
            file.write("writeMesh       no;\n")

            file.write("// ************************************************************************* //\n")

        # print(f" `refineMeshDict.{region}` created at: \n{refineMeshDict_refine_path}")

# Call the function
create_refine_files()

#------------------------------------------------
# topoSetDict.wakeregions
#------------------------------------------------

def create_topoSetDict_wakeregions():
    topoSetDictwakeregions_path = os.path.join(get_case_folder(), "system/topoSetDict.wakeregions")
    simulationArea = SimulationArea.getSimulationArea()
    turbine_data = WindTurbines.getTurbines()

    refine3height = max(t['hubHeight'] for t in turbine_data['turbines']) + (max(t['hubHeight'] for t in turbine_data['turbines']) * max(t['sphereRadius'] for t in turbine_data['turbines']))


    with open(topoSetDictwakeregions_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n{\n")
        file.write("    version     2.0;\n")
        file.write("    format      ascii;\n")
        file.write("    class       dictionary;\n")
        file.write("    location    \"system\";\n")
        file.write("    object      topoSetDict;\n")
        file.write("}\n\n")
        
        file.write("// ************************************************************************* //\n")
        file.write("#include \"$FOAM_CASE/system/initialConditions\"\n\n")
        file.write("actions\n(\n")
        
        # Original turbine refinement loop (kept for reference)
        file.write("    /*\n")
        file.write("    { // Original turbine refinement\n")
        file.write("        name        turbineName;\n")
        file.write("        type        cellSet;\n")
        file.write("        action      new;\n")
        file.write("        source      sphereToCell;\n")
        file.write("        origin      ( shiftedX shiftedY hubHeight );\n")
        file.write("        // radius      turbine_data.sphereRadius;\n")
        file.write("    }\n")
        file.write("    */\n\n")
        
        # New wake region refinement loop using wake.id from the wake region object:
        file.write("    // New wake region refinement using boxToCell based on wake.id\n")
        for wake in WakeRegion.getSubdividedWakeRegions():
            # Shift wake coordinates by simulationArea center
            shifted_points = [(pt[0] - simulationArea.center[0], pt[1] - simulationArea.center[1])
                              for pt in wake["coordinates"]]
            # Apply inverse rotation to align with mesh (angle = -rotation_angle)
            angle = simulationArea.rotation_angle_rad
            rotated_points = [(p[0]*math.cos(angle) + p[1]*math.sin(angle),
                               -p[0]*math.sin(angle) + p[1]*math.cos(angle))
                              for p in shifted_points]
            xs = [pt[0] for pt in rotated_points]
            ys = [pt[1] for pt in rotated_points]
            box_x_min = min(xs)
            box_y_min = min(ys)
            box_x_max = max(xs)
            box_y_max = max(ys)
            
            file.write("    {\n")
            file.write(f"        name        {wake['id']};\n")
            file.write("        type        cellSet;\n")
            file.write("        action      new;\n")
            file.write("        source      boxToCell;\n")
            file.write(f"        box ({box_x_min} {box_y_min} {0}) " +
                       f"({box_x_max} {box_y_max} {refine3height});\n")
            file.write("    }\n\n")
        
        file.write(");\n")
        file.write("// ************************************************************************* //\n")

# Call the function
create_topoSetDict_wakeregions()


#------------------------------------------------
# refineMeshDict.wakeregions
#------------------------------------------------
def create_refineMeshDict_wakeregions():
    refineMeshDict_wakeregions_path = os.path.join(get_case_folder(), "system/refineMeshDict.wakeregions")

    with open(refineMeshDict_wakeregions_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n{\n")
        file.write("    version     2.0;\n")
        file.write("    format      ascii;\n")
        file.write("    class       dictionary;\n")
        file.write("    location    \"system\";\n")
        file.write("    object      refineMeshDict;\n")
        file.write("}\n\n")
        
        file.write("// ************************************************************************* //\n")
        file.write("\n")
        file.write("set RefineObject;\n")

        file.write("\n")
        file.write("coordinateSystem global;\n")
        file.write("\n")

        file.write("// Rotation of refine coordinate system\n")
        file.write("globalCoeffs\n{\n")
        # no need for rotaion because main axis is rotated to the mesh (refers to Allpre)
        # file.write(f"    tan1            ( {SimulationArea.getSimulationArea().cos_rotation} {SimulationArea.getSimulationArea().sin_rotation} 0 );\n")
        # file.write(f"    tan2            ( {-SimulationArea.getSimulationArea().sin_rotation} {SimulationArea.getSimulationArea().cos_rotation} 0 );\n")
        # after rotation the refineMesh.windturbines the main axis is aligned with the mesh
        file.write("    tan1            ( 1 0 0 );\n")
        file.write("    tan2            ( 0 1 0 );\n")
        file.write("}\n")

        file.write("\n")
        file.write("directions\n(\n")
        file.write("    tan1\n")
        file.write("    tan2\n")
        file.write("    normal\n")
        file.write(");\n")

        file.write("\n")
        file.write("useHexTopology  yes;\n")
        file.write("geometricCut    no;\n")
        file.write("writeMesh       no;\n")
        file.write("\n")

        file.write("// ************************************************************************* //\n")

    # print(f" `refineMeshDict.wakeregions` created at: \n{refineMeshDict_wakeregions_path}")

# Call the function
create_refineMeshDict_wakeregions()


################################################
#------------------------------------------------
# SOLVER Settings
#------------------------------------------------
################################################

#------------------------------------------------
# Allrun
#------------------------------------------------
def create_allrun_script():
    computeCores = SolverParameters.getSolverParameters().computeCores
    allrun_path = os.path.join(get_case_folder(), "Allrun")
    with open(allrun_path, 'w') as file:
        file.write("#!/bin/sh\n\n")
        file.write("### Script for running the offshore wind park simulation in parallel\n")
        file.write("### HLRS, 2024-2025\n\n")

        file.write(". $WM_PROJECT_DIR/bin/tools/RunFunctions\n\n")

        file.write("rm log.foamToVTK log.pimpleFoam log.decomposePar log.reconstructPar log.renumberMesh  \n")
        file.write("rm -rf VTK processor* \n\n")

        file.write("restore0Dir\n\n")
        
        file.write(f"mpirun -np {computeCores} pimpleFoam -parallel\n")
        file.write("\n")
        file.write("runApplication reconstructPar\n")
        file.write("\n")
        file.write("runApplication foamToVTK\n")
        file.write("# -----------------------------------------------------------------------------\n")
    # print(f"Allrun successfully created at: \n{allrun_path}")

create_allrun_script()

#------------------------------------------------
# Allpost
#------------------------------------------------
def create_allpost_script():
    allpost_path = os.path.join(get_case_folder(), "Allpost")

    with open(allpost_path, 'w') as file:
        file.write("#!/bin/sh\n\n")
        file.write("### Script for post-processing the offshore wind park simulation\n")
        file.write("### HLRS, 2024-2025\n\n")

        file.write(". $WM_PROJECT_DIR/bin/tools/RunFunctions\n\n")

        file.write("rm log.foamToVTK log.reconstructPar\n\n")
        file.write(r"find . -maxdepth 1 -type d -regextype posix-extended -regex '\./[0-9]{1,5}' -exec rm -rf {} " + "+" + "\n\n")

        file.write("runApplication reconstructPar\n")
        file.write("runApplication foamToVTK\n")
    # print(f"Allpost successfully created at: \n{allpost_path}")

create_allpost_script()
#------------------------------------------------
# Allrun.slurm
#------------------------------------------------
def create_allrun_slurm_script():
    computeCores = SolverParameters.getSolverParameters().computeCores
    allrun_slurm_path = os.path.join(get_case_folder(), "Allrun.slurm")
    with open(allrun_slurm_path, 'w') as file:
        file.write("#!/bin/bash\n\n")
        file.write("### SLURM script for running the offshore wind park simulation in parallel\n")
        file.write("### HLRS, 2024-2025\n\n")
        file.write("#SBATCH --partition=compute                     ### Partition\n")
        file.write("#SBATCH --job-name=openfoamsimoffshore          ### Job Name\n")
        file.write("#SBATCH --time=512:00:00                        ### WallTime\n")
        file.write("#SBATCH --mem-per-cpu 2G\n")
        file.write(f"#SBATCH --ntasks {computeCores}\n")
        file.write("#SBATCH --ntasks-per-core 2\n")
        file.write("#SBATCH --ntasks-per-node 15\n")
        file.write("#SBATCH --cpus-per-task 1\n")
        file.write("#SBATCH --nodes 10\n")
        file.write("#SBATCH -o slurm.%j.out         # STDOUT\n")
        file.write("#SBATCH -e slurm.%j.err         # STDERR\n\n")
        file.write("source /home/hpcschud/.bashrc\n\n")
        file.write("cd $SLURM_SUBMIT_DIR\n\n")
        file.write(f"mpirun -np {computeCores} -- pimpleFoam -parallel > log.slurm_pimpleFoam 2>&1\n")

    # print(f"AllrunSlurm successfully created at: \n{allrun_slurm_path}")

create_allrun_slurm_script()

# ------------------------------------------------
# Allpost.slurm
# ------------------------------------------------
def create_allpost_slurm_script():
    allpost_slurm_path = os.path.join(get_case_folder(), "Allpost.slurm")

    with open(allpost_slurm_path, 'w') as file:
        file.write("#!/bin/bash\n\n")
        file.write("### SLURM script for post-processing the offshore wind park simulation\n")
        file.write("### HLRS, 2024-2025\n\n")
        file.write("#SBATCH --partition=compute                     ### Partition\n")
        file.write("#SBATCH --job-name=openfoamsimoffshore          ### Job Name\n")
        file.write("#SBATCH --time=512:00:00                        ### WallTime\n")
        file.write("#SBATCH --mem-per-cpu 2G\n")
        file.write("#SBATCH --ntasks 1\n")
        file.write("#SBATCH --cpus-per-task 1\n")
        file.write("#SBATCH -o slurm.%j.out         # STDOUT\n")
        file.write("#SBATCH -e slurm.%j.err         # STDERR\n\n")
        file.write("source /home/hpcschud/.bashrc\n\n")
        file.write("cd $SLURM_SUBMIT_DIR\n\n")
        file.write("runApplication reconstructPar\n")
        file.write("runApplication foamToVTK\n")
    # print(f"AllpostSlurm successfully created at: \n{allpost_slurm_path}")

# controlDict
#------------------------------------------------
def create_controlDict():
    solverParameters = SolverParameters.getSolverParameters()
    controlDict_path = os.path.join(get_case_folder(), "system/controlDict")
    with open(controlDict_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  2212                                  |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("\n")
        file.write("FoamFile\n")
        file.write("{\n")
        file.write("    version     2.0;                    // OpenFOAM-Version\n")
        file.write("    format      ascii;                   // Datei im ASCII-Format\n")
        file.write("    class       dictionary;              // OpenFOAM-Dictionary\n")
        file.write("    location    \"system\";                // Speicherort der Datei\n")
        file.write("    object      controlDict;             // Name des Objekts\n")
        file.write("}\n")
        file.write("\n")
        file.write("// ************************************************************************* //\n")
        file.write("\n")
        file.write("// Anwendung: Definiert den verwendeten OpenFOAM-Solver\n")
        file.write("application     pimpleFoam;              // PIMPLE-Solver für inkompressible, instationäre Strömung\n")
        file.write("\n")
        file.write("// Startoptionen der Simulation\n")
        file.write("startFrom       startTime;               // Simulation beginnt bei startTime\n")
        file.write(f"startTime       {solverParameters.startTime};                       // Startzeit der Simulation\n")
        file.write("\n")
        file.write("// Stoppkriterium für die Simulation\n")
        file.write("stopAt          endTime;                 // Simulation läuft bis `endTime`\n")
        file.write(f"endTime         {solverParameters.endTime};                     // Endzeitpunkt der Simulation (physikalische Zeit in Sekunden)\n")
        file.write("\n")
        file.write("// Zeitschrittgröße\n")
        file.write(f"deltaT          {solverParameters.deltaT};                    // Zeitschrittweite Δt = 0.5s (LES erfordert kleine Zeitschritte)\n")
        file.write("\n")
        file.write("// Steuerung der Datenausgabe\n")
        file.write("writeControl    adjustableRunTime;       // Ausgabe basierend auf dynamischer Simulationszeit\n")
        file.write(f"writeInterval   {solverParameters.writeInterval};                    // Ausgabeintervall für Ergebnisse (wenn, = endtime, dann keine speicherung der Ergebnisse des gesamten Gebietes)\n")
        file.write("\n")
        file.write("// Speicherverwaltung für Ausgabe\n")
        file.write("purgeWrite      0;                        // Keine alten Ausgabedateien löschen\n")
        file.write("writeFormat     binary;                   // Speicherung im binären Format (platzsparend)\n")
        file.write("writePrecision  6;                        // Genauigkeit der Ausgabedaten (6 Dezimalstellen)\n")
        file.write("writeCompression off;                     // Keine Komprimierung der Ergebnisse\n")
        file.write("\n")
        file.write("// Zeitformat für Ausgabe\n")
        file.write("timeFormat      general;                  // Ausgabe im allgemeinen Zeitformat\n")
        file.write("timePrecision   6;                        // Genauigkeit der Zeitausgabe (6 Dezimalstellen)\n")
        file.write("\n")
        file.write("// Laufzeitmodifikation\n")
        file.write("runTimeModifiable yes;                    // Simulationseinstellungen können während der Laufzeit geändert werden\n")
        file.write("\n")
        file.write("// Einbindung von dynamischen Bibliotheken für die Simulation\n")
        file.write("libs (\"libturbinesFoam.so\" \"libatmosphericModels.so\"); // Turbinen- und atmosphärische Modellbibliotheken\n")
        file.write("\n")
        file.write("// Funktionen für die Simulation\n")
        file.write("functions\n")
        file.write("{\n")
        file.write("   //#include \"fieldAverage\"               // Berechnet Mittelwerte von Strömungsgrößen\n")
        file.write("   //#include \"monitorPoints\"              // Definiert Messpunkte zur Überwachung der Strömung\n")
        file.write("   //#include \"writeRegisteredObject\"      // Speichert registrierte OpenFOAM-Objekte\n")
        file.write("   //#include \"writeForceAllTurbines\"      // Erfasst Kräfte auf alle Windturbinen\n")
        file.write("   #include \"sampleSliceDict\"       // (Deaktiviert) Mögliche Extraktion von Querschnitten\n")
        file.write("}\n")
        file.write("\n")
        file.write("// ************************************************************************* //\n")

    # print(f"controlDict successfully created at: \n{controlDict_path}")

# Call the function
create_controlDict()

#------------------------------------------------
# decomposeParDict
#------------------------------------------------
def create_decomposeParDict():
    solverParameters = SolverParameters.getSolverParameters()
    decomposeParDict_path = os.path.join(get_case_folder(), "system/decomposeParDict")

    with open(decomposeParDict_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n")
        file.write("{\n")
        file.write("    version     2.0;\n")
        file.write("    format      ascii;\n")
        file.write("    class       dictionary;\n")
        file.write("    object      decomposeParDict;\n")
        file.write("}\n")
        file.write("// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n")
        file.write("\n")
        file.write(f"numberOfSubdomains {solverParameters.computeCores};\n")
        file.write("\n")
        file.write("method          scotch;\n\n")

        file.write("//method          multiLevel;\n")
        file.write("\n")
        file.write("//multiLevelCoeffs\n")
        file.write("//{\n")
        file.write("//    method scotch;\n")
        file.write("//    domains (2 64);\n")
        file.write("//}\n")
        file.write("\n")
        file.write("// ************************************************************************* //\n")

    # print(f"decomposeParDict successfully created at: \n{decomposeParDict_path}")

# Call the function
create_decomposeParDict()

#------------------------------------------------
# fvOptions
#------------------------------------------------
def create_fvOptions():
    ## get data
    fvOptions_path = os.path.join(get_case_folder(), "constant/fvOptions")
    simulation_area = SimulationArea.getSimulationArea()
    center_x, center_y = simulation_area.center[0], simulation_area.center[1]
    
    wakeRegions = WakeRegion.getSubdividedWakeRegions()

    def shift_polygons_coordinates(polygons, cx, cy):
        """
        Shift all coordinates in a list of polygons by a given offset.
        """
        for polygon in polygons:
            polygon["coordinates"] = [(x - cx, y - cy) for (x, y) in polygon["coordinates"]]
            cx_old, cy_old, cz = polygon["center"]
            polygon["center"] = [cx_old - cx, cy_old - cy, cz]
        return polygons

    wakeRegions_shifted = shift_polygons_coordinates(wakeRegions, center_x, center_y)

    def shift_points_coordinates(points, cx, cy):
        """
        Shift the coordinates of point objects by a given x and y offset.
        """
        for pt in points['turbines']:
            x, y = pt['coordinates']
            pt['coordinates'] = (x - cx, y - cy)
        return points

    turbine_data = WindTurbines.getTurbines()
    turbine_data_shifted = shift_points_coordinates(turbine_data, center_x, center_y)

    # Base fvOptions template header
    fvOptions_content = (
        "/*--------------------------------*- C++ -*----------------------------------*\\\n"
        "| =========                 |\n"
        "| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox\n"
        "|  \\    /   O peration     | Version:  v2212\n"
        "|   \\  /    A nd           | Website:  www.openfoam.com\n"
        "|    \\/     M anipulation  |\n"
        "\\*---------------------------------------------------------------------------*/\n"
        "FoamFile\n"
        "{\n"
        "    version     2.0;\n"
        "    format      ascii;\n"
        "    class       dictionary;\n"
        "    location    \"system\";\n"
        "    object      fvOptions;\n"
        "}\n"
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n"
        "#include \"$FOAM_CASE/system/initialConditions\"\n\n"
    )
    
    # Turbine parameters
    inductionFactor = 0.25 #static
    dynamicStall = "off" #static
    endEffects_mode = "on" #static

    stallType = turbine_data['fvOptions']['stallType']
    dynamicStallModel = turbine_data['fvOptions']['stallModel']
    endEffectsModel = turbine_data['fvOptions']['endEffects']
    tower = turbine_data['fvOptions']['towerCheckbox']
    hub = turbine_data['fvOptions']['hubCheckbox']

    turbine_blocks = ""
    # Iterate over each turbine and assign wake region if the turbine lies within one.
    for turbine in turbine_data_shifted['turbines']:
        turbine_name = turbine['id']
        turbine_type = turbine['turbineType']
        x, y = turbine['coordinates']
        hub_height = turbine['hubHeight']
        rotorRadius = turbine['rotorRadius']
        tipSpeedRatio = turbine['tipSpeedRatio']
        elements = turbine_type.split('_')[-1]
        type = turbine_type.split('_')[0]

        # Determine the cellSet for this turbine's fvOptions by checking each shifted wake region.
        cellset = 'None'
        for wakeR in wakeRegions_shifted:
            if point_in_poly(x, y, wakeR):
                cellset = wakeR['id']
                break

        turbine_block = f"""{turbine_name}
{{
    type            axialFlowTurbineALSource;
    active          on;

    axialFlowTurbineALSourceCoeffs
    {{
        fieldNames          (U);
        selectionMode       cellSet;
        cellSet             {cellset};
        origin              ({x} {y} {hub_height});
        axis                $axisInitial;
        verticalDirection   (0 0 1);
        freeStreamVelocity  $UInitial;
        tipSpeedRatio       {tipSpeedRatio};
        inductionFactor     {inductionFactor};
        rotorRadius         {rotorRadius};

        {stallType}
        {{
            active          {dynamicStall};
            dynamicStallModel {dynamicStallModel};
        }}

        endEffects
        {{
            active          {endEffects_mode};
            endEffectsModel {endEffectsModel};
            GlauertCoeffs
            {{
                tipEffects  on;
                rootEffects on;
            }}
            ShenCoeffs
            {{
                tipEffects  on;
                rootEffects on;
                c1          0.125;
                c2          21;
            }}
        }}

        blades
        {{
            blade1
            {{
                writePerf           true;
                writeElementPerf    true;
                nElements           17;
                elementProfiles
                (
                    #include "{type}_Blade/{type}_{elements}_elementProfiles"
                );
                elementData
                (
                    #include "{type}_Blade/{type}_{elements}_elementData"
                );
                collectivePitch     0.0;
            }}
            blade2
            {{
                $blade1;
                writePerf           false;
                writeElementPerf    false;
                azimuthalOffset     120.0;
            }}
            blade3
            {{
                $blade2;
                azimuthalOffset     240.0;
            }}
        }}
    """
        if tower:
            turbine_block += f"""
        tower
        {{
            includeInTotalDrag  false;
            nElements           2;
            elementProfiles     (cylinder);
            elementData
            (// axial distance (turbine axis), height, diameter
                (10.0 {-hub_height} 4.50)
                (10.0   0.0 3.50)
            );
        }}"""
        if hub:
            turbine_block += f"""
        hub
        {{
            nElements           2;
            elementProfiles     (cylinder);
            elementData
            (
            #include "{type}_Blade/{type}_hub_elementData"
            );
        }}"""
        turbine_block += f"""
        profileData
        {{
            DU99W405LM
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/DU40_A{elements}"
                );
            }}
            DU99W350LM
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/DU35_A{elements}"
                );
            }}
            DU97W300LM
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/DU30_A{elements}"
                );
            }}
            DU91W2250LM
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/DU25_A{elements}"
                );
            }}
            DU93W210LM
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/DU21_A{elements}"
                );
            }}
            NACA64618
            {{
                tableType   singleRe;
                data
                (
                #include "{type}_Blade/{type}_foil/NACA64_A{elements}"
                );
            }}
            circular050
            {{
                data ((-180 0 0.50)(180 0 0.50));
            }}
            circular035
            {{
                data ((-180 0 0.35)(180 0 0.35));
            }}
            cylinder
            {{
                data ((-180 0 0.0)(180 0 0.0));
            }}
        }}
    }}
}}
"""
        turbine_blocks += turbine_block
    
    fvOptions_content += turbine_blocks

    with open(fvOptions_path, "w") as file:
        file.write(fvOptions_content)

create_fvOptions()

# def create_monitorPoints():
#     monitorPointsStatus = "false"
#     monitorPoints_path = os.path.join(get_case_folder(), "system/monitorPoints")
#     with open(monitorPoints_path, 'w') as file:
#         file.write("monitorPoints\n")
#         file.write("{\n")
#         file.write("    type probes;\n")
#         file.write(f"    enabled         {monitorPointsStatus};\n")  # Aktivierung der Messpunkte
#         file.write("    writeControl   timeStep;\n")
#         file.write("    writeInterval   10;\n")
#         file.write("    libs            (\"libsampling.so\");\n")
#         file.write("\n")
#         file.write("    probeLocations\n")
#         file.write("    (\n")

#         # Turbinenkoordinaten als Messpunkte einfügen
#         for turbine in simulation_data["turbines"]["turbines"]:
#             x, y = turbine["coordinates"]
#             file.write(f"        ({x} {y} {hubHeight}) // Monitoring for {turbine['id']}\n")

#         file.write("    );\n")
#         file.write("\n")
#         file.write("    fields\n")
#         file.write("    (\n")
#         file.write("        p\n")         # Druck
#         file.write("        U\n")         # Geschwindigkeit (Ux, Uy, Uz)
#         file.write("        UMean\n")     # Gemittelte Geschwindigkeit (falls `fieldAverage` aktiv ist)
#         file.write("    );\n")
#         file.write("}\n")

#     # print(f"monitorPoints successfully created at: \n{monitorPoints_path}")

# # Call the function
# create_monitorPoints()

#------------------------------------------------
# writeForceAllTurbines
#------------------------------------------------
def create_writeForceAllTurbines():
    turbine_data = WindTurbines.getTurbines()
    writeForceAllTurbines_path = os.path.join(get_case_folder(), "system/writeForceAllTurbines")

    with open(writeForceAllTurbines_path, 'w') as file:
        file.write("writeForceAllTurbines\n")
        file.write("{\n")
        file.write("// Script to sum up the fields from all wind turbines `force.turbineXXX` into a single field `forceAllTurbines.write`\n")
        file.write("// for visualization\n")
        file.write("// HLRS, 2024-2025\n\n")

        file.write("    libs            (utilityFunctionObjects);\n")
        file.write("    type            coded;\n")
        file.write("    name            writeForceAllTurbines;\n")
        file.write("    writeControl    adjustableRunTime;\n")
        file.write("    writeInterval   10.0;\n\n")

        file.write("    codeWrite\n")
        file.write("    #{\n\n")

        # Initialisierung des Kraftfelds
        file.write("        volScalarField forceAllTurbines\n")
        file.write("        (\n")
        file.write("            IOobject\n")
        file.write("            (\n")
        file.write("                \"forceAllTurbines\",\n")
        file.write("                mesh().time().timeName(),\n")
        file.write("                mesh(),\n")
        file.write("                IOobject::NO_READ,\n")
        file.write("                IOobject::AUTO_WRITE\n")
        file.write("            ),\n")
        file.write("            mesh(),\n")
        file.write("            dimensionedScalar(\"zero\", dimensionSet(0,1,-2,0,0,0,0), 0.0)\n")
        file.write("        );\n\n")

        # Dynamische Erzeugung der Turbinen-Kraftfelder
        file.write("        Foam::word fields[] = {\n")

        # Turbinen iterativ hinzufügen
        for turbine in turbine_data['turbines']:
            turbine_name = turbine['id']
            file.write(f"            \"force.{turbine_name}\",\n")

        file.write("        };\n\n")

        # Berechnung der Gesamtkraft
        file.write("        Info << \"Reading forces \";\n")
        file.write("        for (Foam::word i : fields) {\n")
        file.write("           Info << \"i \" << i;\n")
        file.write("           const volVectorField& forceTemp = mesh().lookupObject<volVectorField>(i);\n")
        file.write("           forceAllTurbines = forceAllTurbines + mag(forceTemp);\n")
        file.write("        }\n\n")

        file.write("        forceAllTurbines.write();\n")
        file.write("        Info << endl <<\"forceAllTurbines volScalarField written\" << endl;\n")
        file.write("    #};\n")
        file.write("}\n")

    # print(f"`writeForceAllTurbines` successfully created at: {writeForceAllTurbines_path}")

# Call the function
create_writeForceAllTurbines()


#------------------------------------------------
# sampleSlice
#------------------------------------------------
#TODO: make it work for openFOAM (needs to be aktivated in controlDict)
def create_sampleSlice():
    turbines = WindTurbines.getTurbines()
    hubHeight = turbines['turbines'][0]['hubHeight']
    sampleSlice_path = os.path.join(get_case_folder(), "system/sampleSliceDict")

    with open(sampleSlice_path, 'w') as file:
        file.write("/*--------------------------------*- C++ -*----------------------------------*\\\n")
        file.write("| =========                 |                                                 |\n")
        file.write("| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |\n")
        file.write("|  \\    /   O peration     | Version:  v2212                                 |\n")
        file.write("|   \\  /    A nd           | Website:  www.openfoam.com                      |\n")
        file.write("|    \\/     M anipulation  |                                                 |\n")
        file.write("\\*---------------------------------------------------------------------------*/\n")
        file.write("FoamFile\n{\n")
        file.write("    version     2.0;\n")
        file.write("    format      ascii;\n")
        file.write("    class       dictionary;\n")
        file.write("    location    \"system\";\n")
        file.write("    object      sampleSlice;\n")
        file.write("}\n\n")
        
        file.write("// ************************************************************************* //\n")
        file.write("\n")
        file.write("interpolationScheme cellPoint;\n")
        file.write("\n")
        file.write("setFormat vtk;\n")
        file.write("\n")
        file.write("sets\n")
        file.write("(\n")
        file.write("    hubSlice\n")
        file.write("    {\n")
        file.write("        type        cuttingPlane;\n")
        file.write("        planeType   pointAndNormal;\n")
        file.write("        pointAndNormalDict\n")
        file.write("        {\n")
        file.write(f"            basePoint   (0 0 {hubHeight});\n")
        file.write("            normalVector (0 0 1);\n")
        file.write("        }\n")
        file.write("        interpolate true;\n")
        file.write("        fields      (U p);\n")
        file.write("    }\n")
        file.write(");\n")
        file.write("\n")
        file.write("// ************************************************************************* //\n")

    # print(f"sampleSlice successfully created at: \n{sampleSlice_path}")

# Call the function
create_sampleSlice()


#------------------------------------------------
#------------------------------------------------
# Summary
#------------------------------------------------
#------------------------------------------------
def print_simulation_summary():
    meshParameters = compute_mesh_parameters()
    """Prints the simulation summary based on mesh parameters."""
    print("\nSimulation Summary:")
    print(f"cellsize: {meshParameters['cell_size']} meters")
    print(f"cellsizeRefine1: {meshParameters['cell_size']/2}")
    print(f"cellsizeRefine2: {meshParameters['cell_size']/4}")
    print(f"cellsizeRefine3: {meshParameters['cell_size']/8}")
    print(f"cellsizeRefineTurb: {meshParameters['cell_size']/16}")
    print(f"Width: {meshParameters['yMax'] - meshParameters['yMin']} meters")
    print(f"Length: {meshParameters['xMax'] - meshParameters['xMin']} meters")
    print(f"Height: {meshParameters['zMax'] - meshParameters['zMin']} meters")

print_simulation_summary()

# subdivided_regions = WakeRegion.getSubdividedWakeRegions()
# print("Subdivided wake regions:")
# for region in subdivided_regions:
#     print(region)