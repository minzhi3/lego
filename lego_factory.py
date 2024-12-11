import cadquery as cq
from cadquery import exporters
import ocp_vscode
import math


class LegoFactory:
    __sine_func = lambda x: -(math.cos(math.pi * x) - 1) / 2
    __line_func = lambda x: x
    __quad_func = lambda x: 2 * x * x if x < 0.5 else 1 - 2 * (1 - x) * (1 - x)
    __cubic_func = lambda x: (
        4 * x * x * x if x < 0.5 else 1 - math.pow(-2 * x + 2, 3) / 2
    )
    __func_map = {
        "line": __line_func,
        "sine": __sine_func,
        "quad": __quad_func,
        "cubic": __cubic_func,
    }

    @classmethod
    def slope_func(cls, slope: str):
        func = cls.__func_map.get(slope, cls.__line_func)
        return lambda x: cq.Vector(0, x, func(x))

    def __init__(self):
        self.wall = 1.2
        self.stud_radius = 9.5 / 2
        self.stud_spacing = 16
        self.stud_height = 4.0
        self.stud_thickness = self.wall
        self.base_shrink = 0.2
        self.inner_cylinder_radius = 6.65
        self.inner_cylinder_thickness = self.wall - 0.2
        self.unit_thickness = 9.5
        self.ledge_thickness = 1.0
        self.ledge_length = 3.2
        self.groove_radius = 25 / 2

    def ledge(
        self, base_height, base_width, base_thickness, height, width
    ) -> cq.Workplane:
        ledgeX: cq.Workplane = cq.Workplane().sketch()
        ledgeX = ledgeX.rarray(
            base_height - self.ledge_length, self.stud_spacing, 2, width
        )
        ledgeX = ledgeX.rect(self.ledge_length, self.ledge_thickness).finalize()
        ledgeX = (
            ledgeX.extrude(base_thickness, False)
            .tag("ledgeX")
            .edges("|Y and <Z and (not(<X or >X))")
            .chamfer(2, 0.2)
        )

        ledgeY: cq.Workplane = cq.Workplane().sketch()
        ledgeY = ledgeY.rarray(
            self.stud_spacing, base_width - self.ledge_length, height, 2
        )
        ledgeY = ledgeY.rect(self.ledge_thickness, self.ledge_length).finalize()
        ledgeY = (
            ledgeY.extrude(base_thickness, False)
            .tag("ledgeY")
            .edges("|X and <Z and (not(<Y or >Y))")
            .chamfer(2, 0.2)
        )

        obj = ledgeX.add(ledgeY).combine()
        return obj

    def stud(self, base_thickness, height, width) -> cq.Workplane:
        result = cq.Workplane("XY", (0, 0, base_thickness)).sketch()
        result = result.rarray(self.stud_spacing, self.stud_spacing, height, width)
        result = (
            result.circle(self.stud_radius)
            .circle(self.stud_radius - self.stud_thickness, "s")
            .finalize()
        )
        result = result.extrude(self.stud_height).tag("stud")
        return result

    def base_size(self, size_num: int) -> float:
        return self.stud_spacing * size_num - self.base_shrink * 2

    def base_thickness(self, size_num: int) -> float:
        return self.unit_thickness * size_num - 0.1

    def base(self, height, width, thickness) -> cq.Workplane:
        base_height = self.base_size(height)
        base_width = self.base_size(width)
        base_height_inner = base_height - self.wall * 2
        base_width_inner = base_width - self.wall * 2
        base_thickness = self.base_thickness(thickness)

        # base
        sketch: cq.Sketch = cq.Workplane().sketch().rect(base_height, base_width)
        sketch = sketch.rect(base_height_inner, base_width_inner, mode="s")
        # cylinder
        sketch = sketch.rarray(
            self.stud_spacing, self.stud_spacing, height - 1, width - 1
        )
        sketch = sketch.circle(self.inner_cylinder_radius)
        sketch = sketch.circle(
            self.inner_cylinder_radius - self.inner_cylinder_thickness, "s"
        )

        base: cq.Workplane = sketch.finalize()
        base = base.extrude(base_thickness).tag("base")
        base = base.faces(">Z").workplane(offset=-self.wall)
        base = base.box(base_height, base_width, self.wall, [True, True, False])

        if height > 1:
            cylinder_ledge: cq.Sketch = cq.Workplane(
                "XY", (0, 0, base_thickness)
            ).sketch()
            cylinder_ledge = cylinder_ledge.rarray(
                self.stud_spacing, self.stud_spacing, height - 1, width - 1
            )
            cylinder_ledge = cylinder_ledge.rect(
                (self.stud_spacing - self.wall - self.base_shrink) * 2,
                self.ledge_thickness,
            )
            cylinder_ledge = cylinder_ledge.rect(
                self.ledge_thickness,
                (self.stud_spacing - self.wall - self.base_shrink) * 2,
            )
            cylinder_ledge = cylinder_ledge.circle(
                self.inner_cylinder_radius, "s"
            ).finalize()
            cylinder_ledge = cylinder_ledge.extrude(
                -base_thickness + self.unit_thickness
            ).tag("cylinder_ledge")
            base = base.add(cylinder_ledge).combine()

        return base

    def make_rectangle(self, height: int, width: int, thickness: int) -> cq.Workplane:
        """
        Creates a rectangular normal brick with specified dimensions and adds features to it.

        Args:
            height (int): The height of the rectangle.
            width (int): The width of the rectangle.
            thickness (int): The thickness of the rectangle.

        Returns:
            cq.Workplane: The resulting 3D object with added features.
        """
        base = self.base(height, width, thickness)
        base_height = self.base_size(height)
        base_width = self.base_size(width)
        base_thickness = self.base_thickness(thickness)

        stun = self.stud(base_thickness, height, width)
        ledge = self.ledge(base_height, base_width, base_thickness, height, width)
        base = base.add(ledge).add(stun).combine()

        # Add fillets to the base edges
        base = base.faces(">X or <X or >Y or <Y").edges().fillet(0.6)
        base = base.faces(">Z").edges().fillet(0.4)
        return base

    def make_slope(
        self,
        height: int,
        width: int,
        thickness_begin: int,
        thickness_end: int,
        slope="line",
    ) -> cq.Workplane:
        if height < 2:
            raise ValueError("Height must be greater than 1")
        base = self.base(height, width, max(thickness_begin, thickness_end))
        base_width = self.base_size(width)
        base_height = self.base_size(height)
        base_thickness_begin = self.base_thickness(thickness_begin)
        base_thickness_end = self.base_thickness(thickness_end)
        base_thickness = max(base_thickness_begin, base_thickness_end)
        ledge = self.ledge(base_height, base_width, base_thickness, height, width)
        base = base.add(ledge).combine()
        # slope
        line = cq.Workplane("YZ").moveTo(-base_width / 2, base_thickness_begin)
        if slope == "line":
            line = line.lineTo(
                base_width / 2,
                base_thickness_end,
            ).tag("slope_axis")
        elif slope == "sine" or slope == "quad" or slope == "cubic":
            points = []
            N = 8
            for i in range(0, N + 1):
                x = i / N
                y = self.__func_map.get(slope, self.__line_func)(x)
                p = (
                    (x - 0.5) * base_width,
                    y * (base_thickness_end - base_thickness_begin)
                    + base_thickness_begin,
                )
                points.append(p)
            # line = line.spline(points).tag("slope_axis")
            line = line.polyline(points).tag("slope_axis")
        else:
            raise ValueError("Invalid slope function")
        path = cq.Workplane("YZ").polyline(points)
        groove = (
            cq.Workplane("XZ")
            .workplane(offset=base_width / 2)
            .center(0, base_thickness_begin)
            .circle(self.groove_radius)
            .sweep(path, normal=(0, 1, 0))
        )
        groove_outer = groove.shell(self.wall)

        line = line.lineTo(base_width / 2, 0).lineTo(-base_width / 2, 0).close()

        slope_base = line.extrude(base_height / 2, both=True).tag("slope_base")
        groove_outer = groove_outer.intersect(slope_base)
        slope_wall = slope_base.faces("<Z").shell(-self.wall)

        base = base.union(slope_wall)
        base = base.union(groove_outer)
        base = base.intersect(slope_base)
        base = base.cut(groove)

        return base
