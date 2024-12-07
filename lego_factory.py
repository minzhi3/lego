import cadquery as cq
from cadquery import exporters


class LegoFactory:
    def __init__(self):
        self.wall = 1.2
        self.stud_radius = 9.5 / 2
        self.stud_spacing = 16
        self.stud_height = 3.75
        self.stud_thickness = self.wall
        self.base_shrink = 0.2
        self.inner_cylinder_radius = 6.65
        self.inner_cylinder_thickness = self.wall - 0.2
        self.unit_thickness = 9.5
        self.ledge_thickness = 1.0
        self.ledge_length = 3.2

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

    def make_rectangle(self, height, width, thickness) -> cq.Workplane:
        base_height = self.stud_spacing * height - self.base_shrink * 2
        base_width = self.stud_spacing * width - self.base_shrink * 2
        base_height_inner = base_height - self.wall * 2
        base_width_inner = base_width - self.wall * 2
        base_thickness = self.unit_thickness * thickness - 0.1

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

        stun = self.stud(base_thickness, height, width)
        ledge = self.ledge(base_height, base_width, base_thickness, height, width)

        base = base.add(ledge).add(stun).combine()

        # Add fillets to the base edges
        base = base.faces(">X or <X or >Y or <Y").edges().fillet(0.6)
        base = base.faces(">Z").edges().fillet(0.4)
        return base
