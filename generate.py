import json
import sys, os
from math import sqrt
import subprocess

# Ramer-Douglas-Peucker algorithm for polypath simplification
# https://stackoverflow.com/questions/37946754/python-ramer-douglas-peucker-rdp-algorithm-with-number-of-points-instead-of
class DPAlgorithm():
    def distance(a, b):
        return  sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def point_line_distance(point, start, end):
        if (start == end):
            return DPAlgorithm.distance(point, start)
        else:
            n = abs(
                (end[0] - start[0]) * (start[1] - point[1]) - (start[0] - point[0]) * (end[1] - start[1])
            )
            d = sqrt(
                (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2
            )
            return n / d

    def rdp(points, epsilon):
        """
        Reduces a series of points to a simplified version that loses detail, but
        maintains the general shape of the series.
        """
        dmax = 0.0
        index = 0
        i=1
        for i in range(1, len(points) - 1):
            d = DPAlgorithm.point_line_distance(points[i], points[0], points[-1])
            if d > dmax :
                index = i
                dmax = d

        if dmax >= epsilon :
            results = DPAlgorithm.rdp(points[:index+1], epsilon)[:-1] + DPAlgorithm.rdp(points[index:], epsilon)
        else:
            results = [points[0], points[-1]]
        return results



def parse_dd2vtt(infile):
    with open(infile, "r") as f:
        data = json.load(f)

    lines = []
    for line in data['line_of_sight']:
        line_pts = []
        for point in line:
            x = point['x']
            y = point['y']
            line_pts.append((x,y))
        lines.append(line_pts)

    return lines


def generate_scad(lines, outfile):
    # include polyline2d scad module
    out = "use <polyline2d.scad>;\n"

    # generate all points
    for i, line in enumerate(lines):
        simplified = DPAlgorithm.rdp(line, simplify_epsilon)
        pointstring = ",".join(f"[{x},{y}]" for x,y in simplified)
        out += f"points{i} = [{pointstring}];\n"

    # generate all walls and union() them
    out += "rotate([90,180,0])\n"
    out += f"linear_extrude({height})\n"
    out += f"scale([{scalex},{scaley},1])\n"
    out += "union(){\n"
    out += "\n".join(f"\tpolyline2d(points=points{i}, width={width},joinStyle=\"JOIN_MITER\");" for i in range(len(lines)))
    out += "\n};"

    with open(outfile, "w") as f:
        f.write(out)


if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} file.dd2vtt")
    exit()

infile = sys.argv[1]
infilename, ext = os.path.splitext(infile)
if "dd2vtt" not in ext:
    print("Please provide a dd2vtt file as input")
    exit()

scalex = 1.1 # multiplicative scale of the final object in x direction
scaley = 1.1 # multiplicative scale of the final object in x direction
height = 2   # height of the final object
width = 0.1  # width of the walls
simplify_epsilon = 0.1 # minimum distance between two wall points. Uses Ramer-Douglas-Peucker to decimate.

outfilescad = infilename + ".scad"
outfilestl =  infilename + ".stl"
outfileobj =  infilename + ".obj"

path, _ = os.path.split(os.path.abspath(__file__))
if os.name == 'nt':
    # windows paths
    # https://github.com/JustinSDK/dotSCAD/archive/v2.4.zip
    dotSCAD_path = path + "\dotSCAD-2.4\src"
    # https://files.openscad.org/OpenSCAD-2019.05-x86-64.zip
    openscad_path = path + "\openscad-2019.05\openscad.exe"
    # https://github.com/cnr-isti-vclab/meshlab/releases/download/Meshlab-2020.07/MeshLab2020.07-windows.exe
    meshlabserver_path = "C:\Program Files\VCG\MeshLab\meshlabserver.exe"
else:
    # linux paths
    dotSCAD_path=path+"/dotSCAD/src"
    openscad_path="openscad"
    # from https://github.com/cnr-isti-vclab/meshlab/releases/download/Meshlab-2020.09/MeshLabServer2020.09-linux.AppImage
    meshlabserver_path="./MeshLabServer2020.09-linux.AppImage"

print(f"Loading lines from input: {infile}")
lines = parse_dd2vtt(infile)

print(f"Generating scad file")
generate_scad(lines, outfilescad)

print(f"Converting scad file to stl")
# openscad -o out.stl generate.scad
subprocess.check_output([openscad_path, outfilescad, "-o", outfilestl], env={"OPENSCADPATH": dotSCAD_path})

print(f"Convertion stl to obj")
#./MeshLabServer2020.09-linux.AppImage -i path_extrude_walls.stl -o mesh.obj
subprocess.check_output([meshlabserver_path, "-i", outfilestl, "-o", outfileobj])

print("Removing tempfiles")
os.remove(outfilescad)
os.remove(outfilestl)